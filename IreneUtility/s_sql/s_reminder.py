from IreneUtility.s_sql import self


async def fetch_reminders():
    """Fetch all reminders. (id, user id, reason, timestamp)"""
    return await self.conn.fetch("SELECT id, userid, reason, timestamp FROM reminders.reminders")
