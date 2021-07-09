from typing import Union

import asyncio
import wavelink
import discord
from discord.ext import commands

from ..Base import Base
from . import u_logger as log


class LoopController(Base):
    def __init__(self, guild_id, *args):
        """Controls the loop for music.

        Our queue is present in the players.
        """
        super().__init__(*args)
        self.guild_id = guild_id
        self.volume = 50
        self.next = asyncio.Event()  # will be triggered when the next song should be played.
        self.ex.client.loop.create_task(self.controller_loop())

    async def controller_loop(self):
        """Manages when to play the next song."""
        player = self.ex.wavelink.get_player(self.guild_id)
        await player.set_volume(self.volume)

        while True:
            played = await self.ex.u_music.play_next(player)  # play the next song.

            if not played:  # no songs are queued.
                await player.disconnect(force=True)
                await player.destroy(force=True)
                break

            await self.next.wait()


class Music(Base):
    def __init__(self, *args):
        """
        Music Utility.

        We want controller logic to be hidden to client.
        """
        super().__init__(*args)
        self.controllers = {}  # guild_id: controller

    async def start_nodes(self):
        """Initiate the wavelink nodes."""
        for voice_region in self.ex.cache.voice_regions:
            try:
                log.console(f"Started Wavelink node for {voice_region}.", method=self.start_nodes)
                node = await self.ex.wavelink.initiate_node(identifier=voice_region, region=voice_region,
                                                            **self.ex.keys.wavelink_options)
                node.set_hook(self.on_event_hook)
            except Exception as e:
                log.console(e, method=self.start_nodes)

    async def on_event_hook(self, event):
        """Node hook callback."""
        if isinstance(event, (wavelink.TrackEnd, wavelink.TrackException)):
            controller = self.get_controller(event.player)
            controller.next.set()

    def get_controller(self, value: Union[commands.Context, wavelink.Player]):
        """Get the controller of a guild.

        Will make a controller if one does not exist.

        :param value: Context or a Player.
        """
        if isinstance(value, commands.Context):
            guild_id = value.guild.id
        else:
            guild_id = value.guild_id
        controller = self.controllers.get(guild_id)
        if not controller:
            controller = LoopController(guild_id)
            self.controllers[guild_id] = controller

        return controller

    async def play_next(self, player: wavelink.Player):
        """Play the next song in the player.

        :param player: The wavelink Player for the guild.
        """
        # Create the controller. This will start the controller loop and start playing songs.
        self.get_controller(player)

        if hasattr(player, "playlist"):
            if not len(player.playlist):
                return

            track: wavelink.Track = player.playlist.pop(0)
            await player.play(track)

            if hasattr(player, "loop"):
                if player.loop:
                    player.playlist.append(track)  # add the track to the end of the queue if we are looping.

            ctx = track.info.get("ctx")
            if ctx:
                msg = await self.ex.get_msg(ctx, "music", "now_playing", [
                    ["title", track.title],
                    ["artist", track.author]
                ])
                await ctx.send(msg)
            return True

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
            await ctx.send(await self.ex.get_msg(ctx, "general", "no_dm"))
            raise Exception  # we do not want the command to progress further than this message

        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                await ctx.send(await self.ex.get_msg(ctx, "music", "no_channel"))
                raise Exception  # we do not want the command to progress further than this message

        player = self.ex.wavelink.get_player(ctx.guild.id)
        await ctx.send(await self.ex.get_msg(ctx, "music", "connecting", ["voice_channel", channel.name]))
        await player.connect(channel.id)

    async def create_queue_embed(self, player: wavelink.Player):
        """
        Create and Return a list of embeds from a queue.

        :param player: The wavelink Player.
        :returns List[discord.Embed]

        """
        embed_list = []
        queue_desc = ""
        page_number = 1
        if hasattr(player, "playlist"):
            if not player.playlist:  # empty playlist.
                return embed_list

            # get the track currently playing
            current_track: wavelink.Track = player.current
            if current_track:
                queue_desc += f"NOW PLAYING: {await self.get_track_info(current_track)}\n"
                # Currently playing song does not count as a queue index.

            # add the rest of the track descriptions.
            for queue_index, track in enumerate(player.playlist, 1):
                queue_desc += f"{queue_index}) {await self.get_track_info(track)}\n"

                if len(queue_desc) >= 1000:
                    embed = await self.ex.create_embed(title=f"Current Server Queue (Page {page_number})",
                                                       title_desc=queue_desc)
                    queue_desc = ""
                    page_number += 1
                    embed_list.append(embed)

        if queue_desc:
            embed_list.append(await self.ex.create_embed(title=f"Current Server Queue (Page {page_number})",
                                                         title_desc=queue_desc))

        return embed_list

    async def get_track_info(self, track: wavelink.Track):
        """
        Puts Track into a displayable form for displaying a queue.

        :param track: Wavelink Track.
        :returns: (str) Message containing the title, artist, duration, and mention of user that requested the song.
        """
        song_info = f"**{track.title}** by **{track.author}** (" \
                    f"**{await self.ex.u_miscellaneous.get_cooldown_time(track.length//1000)}**)"
        ctx = track.info.get("ctx")
        if ctx:
            song_info += f" - Requested by <@{ctx.author.id}>"
        song_info += "\n"
        return song_info



