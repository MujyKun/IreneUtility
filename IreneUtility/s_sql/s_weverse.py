from . import self


async def fetch_weverse():
    """Fetch all weverse subscriptions."""
    return await self.conn.fetch("SELECT channelid, communityname, roleid, commentsdisabled, mediadisabled"
                                 " FROM weverse.channels")
