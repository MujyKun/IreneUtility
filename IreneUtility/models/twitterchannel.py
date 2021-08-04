from typing import Optional, List

import discord
import tweepy

from . import Subscription
from . import base_util
from ..util import u_logger as log

BASE_URL = "https://twitter.com"


class TwitterChannel(Subscription):
    def __init__(self, twitter_id, followed_channels=None):
        """
        Represents a Twitter Channel.


        :param twitter_id: ID of the Twitter Channel (The channel username)
        :param followed_channels: List of channel ids or text channels that are following the Twitter channel.
        """
        super().__init__(twitter_id, followed_channels)

        # If the latest content is None, we will just override it and not consider it as "new"
        self.latest_tweet = None

    async def _fetch_new_tweet(self) -> Optional[str]:
        """Attempt to fetch a new tweet.

        Will not work if no discord text channels are following.
        Will return the link to a tweet if found.
        """
        if not len(self):
            return

        try:
            user = base_util.ex.api.user_timeline(self.id, count=1)
            if not user:
                return
        except Exception as e:
            log.console(f"{e}", method=self._fetch_new_tweet)
            return

        latest_tweet_id = user[0].id_str
        if not latest_tweet_id:
            return

        if not self.latest_tweet:
            # this tweet will not be considered new.
            self.latest_tweet = latest_tweet_id
            return

        if self.latest_tweet == latest_tweet_id:
            # not new
            return

        self.latest_tweet = latest_tweet_id
        tweet_link = f"{BASE_URL}/{self.id}/status/{latest_tweet_id}"
        return tweet_link

    async def send_update_to_followers(self, tweet_link: str) -> List[int]:
        """Send tweet update to following channels.

        :param tweet_link: (str) The link to the tweet.
        :returns: List of channel ids that should be removed. (Failed to send)
        """
        channel_ids_to_remove = []
        for channel in self._followed_channels:
            try:
                if isinstance(channel, int):
                    channel = self._fetch_channel(channel)
                    if not channel:
                        continue
                    if isinstance(channel, int):
                        channel_ids_to_remove.append(channel)
                        continue

                role_id = self._mention_roles.get(channel.id)
                msg_body = tweet_link if not role_id else f"<@&{role_id}>\n{tweet_link}"

                try:
                    log.console(f"Attempting to send Twitter ({self.id}) notification to {channel.id}.",
                                method=self.send_update_to_followers)
                    await channel.send(msg_body)
                except discord.Forbidden:
                    channel_ids_to_remove.append(channel.id)
                    log.console(f"No perms to send twitter noti to {channel.id} (discord.Forbidden)",
                                method=self.send_update_to_followers)
                except Exception as e:
                    log.console(f"{e} (Exception2)", method=self.send_update_to_followers)
            except Exception as e:
                log.console(f"{e} (Exception3)", method=self.send_update_to_followers)

        return channel_ids_to_remove

    async def check_channel_id(self) -> bool:
        """Checks if the Twitter ID (Channel Username) is correct.

        :returns: True if it works.
        """
        try:
            base_util.ex.api.user_timeline(self.id, count=1)
            return True
        except tweepy.TweepError:
            ...
        return False
