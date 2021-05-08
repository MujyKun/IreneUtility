from IreneUtility.s_sql import self


async def fetch_weverse():
    """Fetch all weverse subscriptions."""
    return await self.conn.fetch("SELECT channelid, communityname, roleid, commentsdisabled FROM weverse.channels")
