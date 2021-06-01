from . import self


async def fetch_us_stats():
    """Fetch the user's id, easy, medium, and hard unscramble game stats"""
    return await self.conn.fetch("SELECT userid, easy, medium, hard FROM stats.unscramblegame")
