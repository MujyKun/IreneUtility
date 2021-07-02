from . import self


async def follow(channel_id: int, vlive_id: str, role_id: int = None):
    """
    Follow a vlive channel.

    :param channel_id: Text Channel ID
    :param vlive_id: Vlive channel code the channel is following.
    :param role_id: Role ID to mention.
    """
    await unfollow(channel_id, vlive_id)  # we want to make sure this for certain the below row doesn't already exist.
    await self.conn.execute("INSERT INTO vlive.followers(channelid, roleid, vliveid) VALUES ($1, $2, $3)",
                            channel_id, role_id, vlive_id.lower())


async def unfollow(channel_id: int, vlive_id: str):
    """
    Unfollow a vlive channel.

    """
    await self.conn.execute("DELETE FROM vlive.followers WHERE channelid = $1 AND vliveid = $2",
                            channel_id, vlive_id.lower())
