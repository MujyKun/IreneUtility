from . import self


async def fetch_user_wins(user_id: int):
    """Fetch a user's bias game scores with the idol id to the score."""
    return await self.conn.fetch("SELECT idolid, wins FROM biasgame.winners WHERE userid = $1 ORDER BY WINS DESC",
                                 user_id)
