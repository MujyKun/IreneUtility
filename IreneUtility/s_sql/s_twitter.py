from typing import Union, Optional

from . import self


async def insert_photo_uploaded(image_id, media_id):
    """Insert an image so that we can keep track of twitter media uploads.

    :param image_id: Unique Image ID
    :param media_id: Twitter Media ID
    """
    return await self.conn.execute("INSERT INTO twitter.mediauploaded(imageid, mediaid) VALUES ($1, $2)", image_id,
                                   media_id)


async def check_photo_uploaded(image_id):
    """Checks if a photo was already uploaded.

    :param image_id: The unique image id.
    :returns: Count of the image id in the table (should be 0 or 1)
    """
    return (await self.conn.fetchrow("SELECT COUNT(*) FROM twitter.mediauploaded WHERE imageid = $1", image_id))[0]


async def follow(channel_id: int, twitter_id: str, role_id: int = None):
    """
    Follow a twitter channel.

    :param channel_id: Text Channel ID
    :param twitter_id: Twitter channel code the channel is following.
    :param role_id: Role ID to mention.
    """
    await unfollow(channel_id, twitter_id)  # we want to make sure this for certain the below row doesn't already exist.
    await self.conn.execute("INSERT INTO twitter.followers(channelid, roleid, twitterid) VALUES ($1, $2, $3)",
                            channel_id, role_id, twitter_id.lower())


async def unfollow(channel_id: int, twitter_id: str):
    """
    Unfollow a twitter channel.

    """
    await self.conn.execute("DELETE FROM twitter.followers WHERE channelid = $1 AND twitterid = $2",
                            channel_id, twitter_id.lower())


async def fetch_followed_channels(channel_id: Optional[int] = None):
    """
    Fetch all followed twitter channels.

    Can also be used to fetch a channel's twitter channels.
    :param channel_id: (Optional[int])
    """
    query = "SELECT channelid, roleid, twitterid FROM twitter.followers"
    args = {}
    if channel_id:
        query += " WHERE channelid = $1"
        args = {channel_id}

    return await self.conn.fetch(query, *args)


async def fetch_active_channel_count(channel_ids: Union[list, tuple]) -> int:
    """Fetch the amount of channels that are active from a list.

    This is especially useful for checking the channel IDs of a guild.

    WARNING: Do NOT pass user input into this method.

    :param channel_ids: A list of channel IDS.
    """
    if isinstance(channel_ids, list):
        channel_ids = tuple(channel_ids)

    return (await self.conn.fetchrow(f"SELECT COUNT(*) FROM twitter.followers WHERE channelid IN {channel_ids}"))[0]
