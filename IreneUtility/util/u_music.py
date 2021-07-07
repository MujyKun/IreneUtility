import wavelink
import discord
from ..Base import Base


class Music(Base):
    def __init__(self, *args):
        super().__init__(*args)

    async def toggle_pause(self, ctx, pause=True) -> wavelink.Player:
        """Toggle the pause of a player.

        :param ctx: Context
        :param pause: Whether to pause.
        :returns: Wavelink Player
        """
        if not ctx.guild:
            return await ctx.send(await self.ex.get_msg(ctx, "general", "no_dm"))

        player = self.ex.wavelink.get_player(ctx.guild.id)

        if not player.is_connected:
            await ctx.invoke(self.connect_to_vc(ctx))

        if pause:
            result = "already paused" if player.is_paused else "now paused"
        else:
            result = "now resumed" if player.is_paused else "not paused"

        msg = await self.ex.get_msg(ctx, "music", "player_status", ["result", result])

        await player.set_pause(pause)
        return await ctx.send(msg)

    async def connect_to_vc(self, ctx, channel: discord.VoiceChannel = None):
        """Connect to a voice channel.

        :param ctx: Context
        :param channel: Voice Channel
        """
        if not ctx.guild:
            return await ctx.send(await self.ex.get_msg(ctx, "general", "no_dm"))

        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send(await self.ex.get_msg(ctx, "music", "no_channel"))

        player = self.ex.wavelink.get_player(ctx.guild.id)
        await ctx.send(await self.ex.get_msg(ctx, "music", "connecting", ["voice_channel", channel.name]))
        await player.connect(channel.id)
