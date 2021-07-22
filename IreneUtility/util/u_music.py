from typing import Union, Optional, List

import asyncio

import aiohttp.client_exceptions
import wavelink
import discord
import re
import traceback
from discord.ext import commands
from wavelink.ext import spotify
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
        self.skipped = False  # Whether the song has been skipped.
        self.ignore_next = False  # decides whether the next play event is ignored.
        self.next = asyncio.Event()  # will be triggered when the next song should be played.
        self.ex.client.loop.create_task(self.controller_loop())

    async def controller_loop(self):
        """Manages when to play the next song."""
        player = await self.ex.u_music.get_guild_player(self.guild_id)
        await player.set_volume(self.volume)

        while True:
            self.next.clear()

            # avoids several event calls for a skip and when the track ends.
            if self.ignore_next:
                self.skipped = False
                self.ignore_next = False
                await self.next.wait()
                continue

            if self.skipped:
                self.ignore_next = True

            played = await self.ex.u_music.play_next(player)  # play the next song.

            if not played:  # no songs are queued.
                await player.disconnect(force=True)
                await player.cleanup()
                break

            await self.next.wait()

        await self.ex.u_music.destroy_player(player)


class Music(Base):
    def __init__(self, *args):
        super().__init__(*args)
        self.controllers = {}  # guild_id: controller
        self.node_pool = wavelink.NodePool()
        self.removing_partial_tracks = False
        self.URL_REGEX = re.compile(r'https?://(?:www\.)?.+')

    async def start_nodes(self):
        """Initiate the wavelink nodes."""
        for voice_region in self.ex.cache.voice_regions:
            try:
                log.console(f"Attempting to Start Wavelink node for {voice_region}.", method=self.start_nodes)
                await self.node_pool.create_node(bot=self.ex.client, bot_id=self.ex.keys.bot_id, region=voice_region,
                                                 identifier=voice_region, spotify_client=self.ex.spotify_client,
                                                 **self.ex.keys.wavelink_options)
            except aiohttp.client_exceptions.ClientConnectionError:
                log.console(f"Failed to initiate a node for {voice_region}.")
            except Exception as e:
                log.console(e, method=self.start_nodes)

    async def get_guild_player(self, guild: Union[discord.Guild, int]):
        """Get a player for a guild if it exists."""
        if isinstance(guild, int):
            guild = self.ex.client.get_guild(guild)

        if not guild:
            return

        for node in self.node_pool.nodes.values():
            player = node.get_player(guild)
            if player:
                return player

    def __destroy_controller(self, controller: LoopController):
        """Removes a controller from the collection of controllers if it existed."""
        try:
            self.controllers.pop(controller.guild_id)
        except KeyError:
            pass

    async def destroy_player(self, player: wavelink.Player):
        """Destroys a player and the controller associated with it."""
        controller = self.get_controller(player, create_new=False)
        if controller:
            self.__destroy_controller(controller)
        await player.disconnect(force=True)
        await player.destroy(force=True)

    def get_controller(self, value: Union[commands.Context, wavelink.Player], create_new=True):
        """Get the controller of a guild.

        Will make a controller if one does not exist.

        :param value: Context or a Player.
        :param create_new: Whether to create a new instance if one is not found.
        """
        guild_id = value.guild.id
        controller = self.controllers.get(guild_id)
        if not controller and create_new:
            controller = LoopController(guild_id, self.ex)
            self.controllers[guild_id] = controller

        return controller

    async def start_player_loop(self, player: wavelink.Player):
        """Will start the player's loop if it isn't already started.

        :param player: wavelink Player
        """
        self.get_controller(player)

    async def play_next(self, player: wavelink.Player):
        """Play the next song in the player.

        :param player: The wavelink Player for the guild.
        """
        # Create the controller if it doesn't exist. This will start the controller loop and start playing songs.
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
                    ["title", player.source.info.get("title")],
                    ["artist", player.source.info.get("author")]
                ])
                await ctx.send(msg)
            return True

    async def toggle_pause(self, ctx, pause=True) -> wavelink.Player:
        """Toggle the pause of a player.

        :param ctx: Context
        :param pause: Whether to pause.
        :returns: Wavelink Player
        """
        player = await self.get_guild_player(ctx.guild)

        if not player.is_connected:
            await ctx.invoke(self.connect_to_vc(ctx))

        if pause:
            result = "already paused" if player.is_paused else "now paused"
        else:
            result = "now resumed" if player.is_paused else "not paused"

        msg = await self.ex.get_msg(ctx, "music", "player_status", ["result", result])

        await player.set_pause(pause)
        return await ctx.send(msg)

    async def connect_to_vc(self, ctx: discord.ext.commands.Context) -> Optional[wavelink.Player]:
        """Connect to a voice channel.

        :param ctx: (discord.ext.commands.Context)
        :returns: Optional[wavelink.Player]

        :raises: (discord.NotFound) Author is not in a voice channel or a general exception occurred.
        """

        async def connect(current_channel=None):
            if current_channel:
                await current_channel.disconnect()

            voice_channel = ctx.author.voice.channel
            player: wavelink.Player = await voice_channel.connect(cls=wavelink.Player)
            await ctx.send(await self.ex.get_msg(ctx, "music", "connecting", ["voice_channel",
                                                                              voice_channel.name]))
            return player

        try:
            if not ctx.voice_client:
                return await connect()
            else:
                if ctx.author.voice.channel != ctx.voice_client.channel:
                    return await connect(current_channel=ctx.voice_client)
                vc: wavelink.Player = ctx.voice_client
        except AttributeError:
            await ctx.send(await self.ex.get_msg(ctx, "music", "no_channel"))
            raise discord.NotFound  # we do not want the command to progress further than this message
        except Exception as e:
            await ctx.send(f"{e}")
            raise discord.NotFound  # we do not want the command to progress further than this message
        return vc

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
            # get the track currently playing
            current_track: wavelink.Track = player.source
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

    async def get_track_info(self, track: Union[wavelink.Track, wavelink.PartialTrack]):
        """
        Puts Track into a displayable form for displaying a queue.

        :param track: Wavelink Track.
        :returns: (str) Message containing the title, artist, duration, and mention of user that requested the song.
        """
        extra_info = ""
        if isinstance(track, wavelink.Track):
            extra_info = f" by **{track.author}** " \
                         f"(**{await self.ex.u_miscellaneous.get_cooldown_time(track.length)}**)"
        song_info = f"**{track.title}**{extra_info}"
        ctx = track.info.get("ctx")
        if ctx:
            song_info += f" - Requested by <@{ctx.author.id}>"
        song_info += "\n"
        return song_info

    async def search_query(self, search_query: str):
        """Search Tracks for youtube/spotify/soundcloud playlists/tracks based on a search query.

        :param search_query: Query to search tracks for.
        """

        # currently disabled soundcloud due to possibly
        # searching spotify instead of soundcloud in wavelink beta version.
        # soundcloud_tracks = await self.__search_soundcloud(search_query)

        tracks = await self.__search_spotify(search_query, playlist=True) or await self.__search_spotify(
            search_query, album=True) or await self.__search_spotify(
            search_query) or await self.__search_youtube(search_query)

        return tracks

    async def __search_youtube(self, search_query: str) \
            -> Optional[Union[List[wavelink.PartialTrack], List[wavelink.Track]]]:
        """Search Partial/Tracks for youtube based on a search query.

        :param search_query: Query to search tracks for.
        :returns: Optional[Union[List[wavelink.PartialTrack], List[wavelink.Track]]]
        """
        search_query = search_query.strip('<>')
        get_first_result = self.URL_REGEX.match(search_query)

        if get_first_result:
            # search Youtube Music
            tracks = await wavelink.YouTubeMusicTrack.search(query=search_query, return_first=get_first_result)
            if tracks:
                return tracks

        # search regular youtube.
        tracks = await wavelink.YouTubeTrack.search(query=search_query, return_first=get_first_result)
        if tracks:
            return tracks

    async def __search_soundcloud(self, search_query: str) \
            -> Optional[Union[List[wavelink.PartialTrack], List[wavelink.Track]]]:
        """Search Partial/Tracks for soundcloud based on a search query.

        :param search_query: Query to search tracks for.
        :returns: Optional[Union[List[wavelink.PartialTrack], List[wavelink.Track]]]
        """
        # only get first result
        tracks = await wavelink.SoundCloudTrack.search(query=search_query)
        if tracks:
            return [tracks]

    async def __search_spotify(self, search_query: str, playlist=False, album=False) \
            -> Optional[Union[List[wavelink.PartialTrack], List[spotify.SpotifyTrack]]]:
        """Search PartialTracks for spotify playlists based on a search query.

        :param search_query: Query to search tracks for.
        :param playlist: (bool) To search for playlists.
        :param album: (bool) To search for albums.
        :returns: Optional[List[wavelink.PartialTrack]]
        """
        tracks = []

        try:
            if playlist:
                type = spotify.SpotifySearchType.playlist
            elif album:
                type = spotify.SpotifySearchType.album
            else:
                type = spotify.SpotifySearchType.track
                track = await spotify.SpotifyTrack.search(query=search_query, return_first=True)
                if track:
                    return [track]

            iterator = spotify.SpotifyTrack.iterator(query=search_query, type=type, partial_tracks=True)
            async for track in iterator:
                if not hasattr(track, "info"):
                    track.info = {}
                tracks.append(track)
        except TypeError:
            pass
        except spotify.SpotifyRequestError:
            pass
        except:
            traceback.print_exc()

        return tracks

    async def remove_partial_tracks(self, player):
        """Remove partial tracks and convert them to regular tracks."""
        if self.removing_partial_tracks:
            return

        self.removing_partial_tracks = True
        if not hasattr(player, "playlist"):
            return

        # do not want to enumerate since we need to confirm index at the moment the track is being set.
        for track in player.playlist:
            if isinstance(track, spotify.PartialTrack):
                try:
                    player.playlist[player.playlist.index(track)] = await track._search()
                except ValueError:  # not in list
                    pass
                except IndexError:  # incorrect index
                    pass
        self.removing_partial_tracks = False
