import wavelink
import discord
from ..Base import Base
from . import u_logger as log


class Music(Base):
    def __init__(self, *args):
        super().__init__(*args)

    async def start_nodes(self):
        """Initiate the wavelink nodes."""
        for voice_region in self.ex.cache.voice_regions:
            log.console(f"Started Wavelink node for {voice_region}.", method=self.start_nodes)
            await self.ex.wavelink.initiate_node(identifier=voice_region, region=voice_region,
                                                 **self.ex.keys.wavelink_options)

    async def play_next(self, player: wavelink.Player):
        """Play the next song in the player.

        :param player: The wavelink Player for the guild.
        """
        if hasattr(player, "playlist"):
            if not len(player.playlist):
                return

            track: wavelink.Track = player.playlist.pop[0]
            await player.play(track)

            player.now_playing = track

            if hasattr(player, "loop"):
                if player.loop:
                    player.playlist.append(track)  # add the track to the end of the queue if we are looping.

            if hasattr(track, "ctx"):
                msg = await self.ex.get_msg(track.ctx, "music", "now_playing", [
                    ["title", track.title],
                    ["author", track.author]
                ])
                await track.ctx.send(msg)

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
