from . import self


async def fetch_games_disabled():
    """Fetch the servers being logged."""
    return await self.conn.fetch("SELECT channelid FROM general.gamesdisabled")


async def disable_game_in_channel(channel_id: int):
    """Disable games in a text channel."""
    return await self.conn.execute("INSERT INTO general.gamesdisabled(channelid) VALUES($1)", channel_id)


async def enable_game_in_channel(channel_id: int):
    """Enable games in a text channel."""
    return await self.conn.execute("DELETE FROM general.gamesdisabled WHERE channelid = $1", channel_id)
