import discord

from ..Base import Base
from ..models import VliveChannel


class Vlive(Base):
    def __init__(self, *args):
        super().__init__(*args)

    async def follow_vlive(self, channel, vlive_id, role_id=None):
        """
        Follows a vlive channel.

        :param channel: Can be a TextChannel or a channel ID. Will attempt to make it a channel.
        :param vlive_id: Channel Code for vlive channel.
        :param role_id: Role ID that should be mentioned.
        """
        vlive_id, vlive_obj, channel, channel_id = self.get_necessities(channel, vlive_id)

        if not vlive_obj.check_channel_followed(channel):
            await self.ex.sql.s_vlive.follow(channel_id, vlive_id, role_id)
            vlive_obj += channel if channel else channel_id
            return True

    async def unfollow_vlive(self, channel, vlive_id):
        """
        Unfollows a vlive channel.

        :param channel: Can be a TextChannel or a channel ID. Will attempt to make it a channel.
        :param vlive_id: Channel Code for vlive channel.
        """
        vlive_id, vlive_obj, channel, channel_id = self.get_necessities(channel, vlive_id)

        if vlive_obj.check_channel_followed(channel):
            vlive_obj -= channel if channel else channel_id
            await self.ex.sql.s_vlive.unfollow(channel_id, vlive_id)
            return True

    def get_necessities(self, channel, vlive_id):
        """Used to reduce duplicated code and bring objects in their correct formats.

        :returns The vlive id, vlive object, TextChannel, and TextChannel id in their proper formats.
        """
        vlive_id = vlive_id.lower()
        vlive_obj: VliveChannel = self.ex.cache.vlive_channels.get(vlive_id)

        if isinstance(channel, discord.TextChannel):
            channel_id = channel.id
        else:  # should be int // will account for string
            channel_id = int(channel)
            channel = self.ex.client.get_channel(channel_id)

        return vlive_id, vlive_obj, channel, channel_id
