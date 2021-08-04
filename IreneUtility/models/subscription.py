from typing import Union, Optional
from . import base_util
from ..util import u_logger as log

import discord


class Subscription:
    def __init__(self, sub_id, followed_channels=None):
        """
        :param sub_id: The ID of the subscription.
        :param followed_channels: The channels subscribed/followed.
        """
        self.id = sub_id.lower()  # channel code
        self._followed_channels = followed_channels or []
        self._mention_roles = {}  # channel_id: role_id

    def __iadd__(self, channel: Union[discord.TextChannel, int]):
        """Have a text channel follow this vlive channel.

        DO NOT PASS IN A VLIVE CHANNEL
        """
        self.add_text_channel(channel)
        return self

    def __isub__(self, channel: Union[discord.TextChannel, int]):
        """Have a text channel unfollow this vlive channel.

        DO NOT PASS IN A VLIVE CHANNEL
        """
        self.remove_text_channel(channel)
        return self

    def __len__(self):
        """Get the amount of text channels following."""
        return len(self._followed_channels)

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

    def check_channel_followed(self, channel) -> Union[discord.TextChannel, int]:
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

    async def _fetch_channel(self, channel_id: int) -> Optional[discord.TextChannel, int]:
        """
        Get/Fetch a discord text channel.

        :param channel_id: The Text Channel ID.
        :returns: (int) If it could not be found or there was no permission, the text channel ID would be returned.
        :returns: (NoneType) If there was a general Exception
        :returns: (discord.TextChannel) If the retrieval went well.
        """
        try:
            channel = base_util.ex.client.get_channel(channel_id) or \
                      await base_util.ex.client.fetch_channel(channel_id)
        except discord.Forbidden:
            log.console(f"No Permission to fetch Channel ID: {channel_id}. (discord.Forbidden)",
                        method=self._fetch_channel)
            return channel_id
        except discord.NotFound:
            log.console(f"Failed to fetch Invalid Channel ID: {channel_id}. (discord.NotFound)",
                        method=self._fetch_channel)
            # invalid channel id.
            return channel_id
        except Exception as e:
            log.console(f"{e} (Exception)", method=self._fetch_channel)
            return  # Skip this channel.
        return channel
