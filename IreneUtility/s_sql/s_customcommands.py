from IreneUtility.s_sql import self


async def fetch_custom_commands():
    """Fetches all custom commands."""
    return await self.conn.fetch("SELECT serverid, commandname, message FROM general.customcommands")

