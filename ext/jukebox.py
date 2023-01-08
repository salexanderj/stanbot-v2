import disnake
import utils
from disnake.ext import commands
from bot import StanBot

import voice.helpers


class Radio(commands.Cog):
    def __init__(self, bot: StanBot):
        self.bot = bot

    @commands.slash_command(
        description="Command Stan to play audio from a url.",
        dm_permission=False
    )
    async def play(self,
                   inter: disnake.ApplicationCommandInteraction,
                   url: str = commands.Param(description="The url to play.")
                   ) -> None:

        channel = voice.helpers.try_get_voice_channel(inter.author)
        if channel is None:
            await inter.send("Where, retard?", delete_after=10)
            return

        vc = await voice.helpers.ensure_in_channel(self.bot, channel)

        try:
            await vc.enqueue([url], inter)
        except Exception as e:
            await inter.send("I farded.", delete_after=10)
            await utils.relay_error(self.bot, e, await inter.original_message())

    @commands.message_command(
        name="Play File(s)",
        description="Command Stan to play audio from embeds or files in the selected message.",
        dm_permission=False
    )
    async def play_selected(self,
                            inter: disnake.ApplicationCommandInteraction
                            ) -> None:

        if not inter.target:
            await inter.send("I can't play that, retard.", ephemeral=True)
            return

        channel = voice.helpers.try_get_voice_channel(inter.author)
        if channel is None:
            await inter.send("Where, retard?", ephemeral=True)
            return

        message: disnake.Message = inter.target

        urls = []

        for attachment in message.attachments:
            if "video" in attachment.content_type or "audio" in attachment.content_type:
                urls.append(attachment.url)
        for embed in message.embeds:
            if embed.video is not None:
                urls.append(embed.video.url)

        if len(urls) < 1:
            await inter.send("I can't play that, retard.", ephemeral=True)
            return

        channel = voice.helpers.try_get_voice_channel(inter.author)
        if channel is None:
            await inter.send("Where, retard?", ephemeral=True)
            return

        vc = await voice.helpers.ensure_in_channel(self.bot, channel)

        try:
            await vc.enqueue(urls, inter)
        except Exception as e:
            await inter.send("I farded.", ephemeral=True)
            await utils.relay_error(self.bot, e, await inter.original_message())

    @commands.slash_command(
        description="Command Stan to skip the current item in queue.",
        dm_permission=False
    )
    async def skip(self,
                   inter: disnake.ApplicationCommandInteraction,
                   no_loop: bool = commands.Param(
                       description="If true, this will prevent the skipped song from being looped.",
                       default=False)
                   ):

        channel = voice.helpers.try_get_voice_channel(inter.guild.me)
        if channel is None:
            await inter.send("Retard", delete_after=10)
            return

        vc = voice.helpers.try_get_voice_client(self.bot, channel)
        if vc:
            await vc.skip(inter, no_loop)
        else:
            await inter.send("Retard.", delete_after=10)

    @commands.slash_command(
        description="Forces Stan to disconnect from the voice channel in this guild.",
        dm_permission=False
    )
    async def disconnect(self,
                         inter: disnake.ApplicationCommandInteraction
                         ) -> None:

        channel = voice.helpers.try_get_voice_channel(inter.author)
        if channel is None:
            await inter.send("Retard.", delete_after=10)
            return

        vc = voice.helpers.try_get_voice_client(self.bot, channel)

        if vc is not None:
            await vc.clear()
            await vc.disconnect()
            await inter.send(f"Banished from {channel.name}.", delete_after=10)
        else:
            await inter.send("Retard.", delete_after=10)

    @commands.slash_command(
        description="Command Stan to toggle looping queue mode.",
        dm_permission=False
    )
    async def loop(self,
                   inter: disnake.ApplicationCommandInteraction
                   ):

        channel = voice.helpers.try_get_voice_channel(inter.guild.me)
        if channel is None:
            await inter.send("Retard", delete_after=10)
            return

        vc = voice.helpers.try_get_voice_client(self.bot, channel)
        if vc:
            await vc.toggle_looping(inter)
        else:
            await inter.send("Retard.", delete_after=10)


def setup(bot: StanBot) -> None:
    bot.add_cog(Radio(bot))
