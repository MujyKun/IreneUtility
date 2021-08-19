from typing import List

import discord
from . import base_util
from . import Subscription
from ..util import u_logger as log


class VliveChannel(Subscription):
    def __init__(self, vlive_id, followed_channels=None):
        """
        Represents a VLIVE Channel.


        :param vlive_id: ID of the Vlive Channel (The channel code)
        :param followed_channels: List of channel ids or text channels that are following the Vlive channel.
        """
        super().__init__(vlive_id, followed_channels)

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

    async def check_live(self):
        """Check if the Vlive channel is live."""
        if not await self._fetch_data():
            log.console(f"Failed to update data for VLIVE Channel {self.id}", method=self.check_live)
            return False  # we were not able to successfully update our data.
        return self._is_live

    async def send_live_to_followers(self) -> List[int]:
        """Send live message to following channels

        :returns: List of channel ids that should be removed. (Failed to send)
        """
        self.already_posted = True
        channel_ids_to_remove = []
        embed = await self.create_embed()
        for channel in self._followed_channels:
            try:
                if isinstance(channel, int):
                    channel = await self._fetch_channel(channel)
                    if not channel:
                        continue
                    if isinstance(channel, int):
                        channel_ids_to_remove.append(channel)
                        continue

                role_id = self._mention_roles.get(channel.id)
                msg_body = None if not role_id else f"<@&{role_id}>"

                try:
                    log.console(f"Attempting to send Vlive ({self.id}) notification to {channel.id}.",
                                method=self.send_live_to_followers)
                    await channel.send(msg_body, embed=embed)
                except discord.Forbidden:
                    channel_ids_to_remove.append(channel.id)
                    log.console(f"No perms to send vlive noti to {channel.id} (discord.Forbidden)",
                                method=self.send_live_to_followers)
                except Exception as e:
                    log.console(f"{e} (Exception2)", method=self.send_live_to_followers)
            except Exception as e:
                log.console(f"{e} (Exception3)", method=self.send_live_to_followers)

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
