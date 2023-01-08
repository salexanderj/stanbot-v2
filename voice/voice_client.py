import disnake
import asyncio
from datetime import datetime
from queue import Queue
from typing import Optional

from voice.song import Song
from voice.ytdl import extract_media_info, get_ffmpeg_options
from voice.media_info import MediaInfo, MediaType


class StanVoiceClient(disnake.VoiceClient):

    def __init__(self, client: disnake.Client, channel: disnake.abc.Connectable):

        super().__init__(client, channel)
        self._queue: Queue[Song] = Queue()
        self._current_song: Optional[Song] = None
        self._looping: bool = False
        self._embed_message: Optional[disnake.Message] = None
        self._announce_channel: Optional[disnake.TextChannel] = None
        self._last_member: Optional[disnake.Member] = None

    async def enqueue(self, urls: list[str], inter: disnake.ApplicationCommandInteraction) -> None:

        self._announce_channel = inter.channel
        self._last_member = inter.author

        await inter.response.defer()

        infos: list[MediaInfo] = []

        for url in urls:
            new_infos = await extract_media_info(url, MediaType.Audio)
            infos.extend(new_infos)

        for info in infos:
            new_song = Song(info, inter.author)
            self._queue.put(new_song)

        if not self.is_playing():
            await self.play_next()
        else:
            await self.update_embed()

        await inter.delete_original_message()

    async def play_next(self) -> None:

        self.stop()

        next_song = self._queue.get(block=False)
        self._current_song = next_song

        source = disnake.FFmpegPCMAudio(next_song.media_info.media_url, **get_ffmpeg_options())
        self.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.on_end(), self.client.loop))

        await self.send_or_update_embed()

    async def on_end(self) -> None:

        if self._queue.empty():
            if self._looping and self._current_song:
                self._queue.put(self._current_song)
                await self.play_next()
            else:
                await self.clear()
                await self.disconnect()
        else:
            if self._looping and self._current_song:
                self._queue.put(self._current_song)
            await self.play_next()

    async def skip(self, inter: Optional[disnake.ApplicationCommandInteraction] = None, no_loop: bool = False) -> None:

        await inter.send(f"Skipping {self._current_song.name}{' and ignoring looping' if no_loop else ''}...",
                         delete_after=10)
        if no_loop:
            self._current_song = None
        self.stop()
        await self.update_embed()

    async def toggle_looping(self, inter: Optional[disnake.ApplicationCommandInteraction] = None) -> None:

        self._looping = not self._looping
        await self.update_embed()
        text = "enabled" if self._looping else "disabled"
        await inter.send(f"Looping {text}...", delete_after=10)

    async def generate_embed(self) -> disnake.Embed:

        embed = disnake.Embed(
            title="Echoes of the Void",
            color=0x8c041f,
            timestamp=datetime.now()
        )

        if self._last_member is not None:
            embed.set_author(name=self._last_member.nick or self._last_member.name,
                             icon_url=self._last_member.avatar.url)

        current = self._current_song

        if current is not None and current.media_info.thumbnail is not None:
            embed.set_thumbnail(current.media_info.thumbnail)

        songs_field = f":arrow_forward: {current.name[:30] + '...' if len(current.name) > 30 else current.name}\n" \
            if current else ""
        requesters_field = f"{current.owner.nick or current.owner.name}\n" \
            if current else ""
        links_field = f"[{current.media_info.extractor}]({current.media_info.page_url})\n" \
            if current else ""

        l: list[Song] = list(self._queue.queue)
        count = 0
        if len(l) > 0:
            for idx, i in enumerate(l):
                if count == 25:
                    break
                songs_field += f"{idx + 1}. {i.name[:30] + '...' if len(i.name) > 30 else i.name}\n"
                requesters_field += f"{i.owner.nick or i.owner.name}\n"
                links_field += f"[{i.media_info.extractor}]({i.media_info.page_url})\n"

                count += 1

        embed.add_field("Queue", songs_field)
        embed.add_field("Requester", requesters_field)
        embed.add_field("Source", links_field)

        embed.set_footer(text=f"Currently looping:  {self._looping}")

        return embed

    async def send_or_update_embed(self) -> None:

        if self._embed_message is None:
            await self.send_embed()
            return

        if self._embed_message.channel is not self._announce_channel:
            await self._embed_message.delete()
            await self.send_embed()
            return

        await self.update_embed()

    async def update_embed(self) -> None:

        if self._embed_message is None:
            return

        new_embed = await self.generate_embed()
        await self._embed_message.edit(embeds=[new_embed])

    async def send_embed(self) -> None:

        if self._announce_channel is None:
            return

        embed = await self.generate_embed()
        self._embed_message = await self._announce_channel.send(embeds=[embed])

    async def clear(self) -> None:

        await self._embed_message.delete()
