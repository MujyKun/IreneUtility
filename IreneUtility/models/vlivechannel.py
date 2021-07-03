import discord
from . import base_util
from ..util import u_logger as log


class VliveChannel:
    def __init__(self, vlive_id, followed_channels=None):
        """
        Represents a VLIVE Channel.


        :param vlive_id: ID of the Vlive Channel (The channel code)
        :param followed_channels: List of channel ids or text channels that are following the Vlive channel.
        """
        self.id = vlive_id.lower()  # channel code
        self._followed_channels = followed_channels or []
        self._mention_roles = {}  # channel_id: role_id

        # Whether we already posted to followed channels about the current live
        self.already_posted = False

        self._payload = {
            "app_id": base_util.ex.keys.vlive_app_id,
            "channelCode": self.id,
            "maxNumOfRows": 100,
            "pageNo": 1
        }
        self._channel_info = None  # General VLive channel Info

        self.channel_name = None  # Name of the Channel (Includes Korean)
        self.profile_image = None  # URL to the profile of the channel.
        self.cover_image = None  # URL to the cover image of the channel.
        self.fan_count = None  # Number of fans.
        self.slogan = None  # Slogan of the channel.
        self.total_video_count = None  # Total amount of videos in the channel.

        self._video_list = None  # A LIST of dics (videos).

        # as these are not always updated, we will have them private
        self._is_live = False  # Whether the channel is currently live.
        self._most_recent_video = None  # Video Dic of the most recent video.

    def __iadd__(self, channel):
        """Have a text channel follow this vlive channel.

        DO NOT PASS IN A VLIVE CHANNEL
        """
        if isinstance(channel, discord.TextChannel) or isinstance(channel, int):
            self.add_text_channel(channel)

    def __isub__(self, channel):
        """Have a text channel unfollow this vlive channel.

        DO NOT PASS IN A VLIVE CHANNEL
        """
        if isinstance(channel, discord.TextChannel) or isinstance(channel, int):
            self.remove_text_channel(channel)

    def __len__(self):
        """Get the amount of text channels following."""
        return len(self._followed_channels)

    async def check_live(self):
        """Check if the Vlive channel is live."""
        if not await self._fetch_data():
            return False  # we were not able to successfully update our data.

    async def send_live_to_followers(self):
        """Send live message to following channels

        :returns: List of channel ids that should be removed. (Failed to send)
        """
        self.already_posted = True
        channel_ids_to_remove = []
        embed = await self.create_embed()
        for channel in self._followed_channels:
            if isinstance(channel, int):
                try:
                    channel = base_util.ex.client.get_channel(channel) or \
                              await base_util.ex.client.fetch_channel(channel)
                except discord.Forbidden:
                    channel_ids_to_remove.append(channel)
                    log.console(f"No Permission to fetch Channel ID: {channel}. (discord.Forbidden)",
                                method=self.send_live_to_followers)
                except discord.NotFound:
                    channel_ids_to_remove.append(channel)
                    log.console(f"Failed to fetch Invalid Channel ID: {channel}. (discord.NotFound)",
                                method=self.send_live_to_followers)
                    # invalid channel id.
                except Exception as e:
                    log.console(f"{e} (Exception)", method=self.send_live_to_followers)

            role_id = self._mention_roles.get(channel.id)
            msg_body = None
            if role_id:
                msg_body = f"<@&{role_id}>"

            try:
                await channel.send(msg_body, embed=embed)
            except discord.Forbidden:
                channel_ids_to_remove.append(channel.id)
                log.console(f"No perms to send vlive noti to {channel.id} (discord.Forbidden)",
                            method=self.send_live_to_followers)
            except Exception as e:
                log.console(f"{e} (Exception2)", method=self.send_live_to_followers)

        return channel_ids_to_remove

    async def create_embed(self):
        """Created an embed for being live."""
        title = f"{self.channel_name} IS NOW LIVE ON VLIVE!"
        video_id = self._most_recent_video.get("videoSeq")
        video_title = self._most_recent_video.get("title")
        thumbnail_link = self._most_recent_video.get("thumbnail")
        video_link = f"https://www.vlive.tv/video/{video_id}"
        desc = f"**Video Title:** {video_title}"

        embed = await base_util.ex.create_embed(title=title, title_desc=desc, title_url=video_link)
        embed.set_thumbnail(url=self.profile_image)
        embed.set_image(url=thumbnail_link)

        return embed

    async def _fetch_data(self):
        """Fetches and updates data."""
        async with base_util.ex.session.get(f"{base_util.ex.keys.vlive_base_url}/getChannelVideoList",
                                         params=self._payload) as response:
            if response.status != 200:
                return

            data = await response.json(content_type=None)

        if not data:
            return

        # we will only store the important things under the object itself.
        result = data.get("result")
        channel_info = result.get("channelInfo")

        self.channel_name = channel_info.get("channelName")
        self.profile_image = channel_info.get("channelProfileImage")
        self.cover_image = channel_info.get("channelCoverImage")
        self.fan_count = channel_info.get("fanCount")
        self.slogan = channel_info.get("comment")
        self.total_video_count = result.get("totalVideoCount")

        # entire video list
        self._video_list = result.get("videoList")

        self._most_recent_video = self._video_list[0]
        self._is_live = self._most_recent_video.get("videoType") == "LIVE"
        if not self._is_live:
            self.already_posted = False

        return True

    async def check_channel_code(self):
        """Checks if the Vlive ID (Channel Code) is correct.

        :returns: True if it works.
        """
        async with base_util.ex.session.get(f"{base_util.ex.keys.vlive_base_url}/getChannelVideoList",
                                            params=self._payload) as response:
            if response.status == 500:
                # We will not specifically check the code (usually 3002) that is processed back.
                # The reason for this is because if you send a long enough vlive id, you will get an invalid param
                # error instead (usually 3000) from vlive.
                return False
        return True

    def add_text_channel(self, channel):
        """
        Let a text channel follow the vlive channel.

        :param channel: Channel ID or a TextChannel
        """
        object_followed = self.check_channel_followed(channel)
        if not object_followed:
            self._followed_channels.append(channel)

    def remove_text_channel(self, channel):
        """
        Makes a text channel unfollow this vlive channel.

        :param channel: Channel ID or a TextChannel
        """
        object_followed = self.check_channel_followed(channel)
        if object_followed:
            self._followed_channels.remove(channel)

    def check_channel_followed(self, channel):
        """Checks if a channel is followed and returns the object that is followed.

        :param channel: Channel ID or a TextChannel
        :returns: (discord.TextChannel or int) The object that is following the vlive channel.
        """
        if isinstance(channel, discord.TextChannel):
            channel_id = channel.id
        else:  # should be an int // taking consideration for string too.
            channel_id = int(channel)
            channel = base_util.ex.client.get_channel(channel_id)

        if channel:
            if channel in self._followed_channels:
                return channel
        if channel_id in self._followed_channels:
            return channel_id

    def set_mention_role(self, channel, role):
        """Will mention a role whenever posting in a certain channel.

        :param channel: Channel ID or a Text Channel.
        :param role: Role ID or Role.
        """
        if isinstance(channel, discord.TextChannel):
            channel_id = channel.id
        else:
            channel_id = int(channel)

        if isinstance(role, discord.Role):
            role_id = role.id
        else:
            role_id = int(role)

        self._mention_roles[channel_id] = role_id
