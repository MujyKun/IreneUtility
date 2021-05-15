from IreneUtility.s_sql import self


async def fetch_bot_statuses():
    """Fetch all bot statuses."""
    return await self.conn.fetch("SELECT status FROM general.botstatus")


async def fetch_n_word(ordered_by_greatest=False):
    """Fetch all users N Word count."""
    additional_query = "ORDER BY nword DESC" if ordered_by_greatest else ""
    return await self.conn.fetch(f"SELECT userid, nword FROM general.nword {additional_query}")


async def fetch_temp_channels():
    """Fetch all temporary channels"""
    return await self.conn.fetch("SELECT chanid, delay FROM general.tempchannels")


async def fetch_welcome_messages():
    """Fetch all welcome messages"""
    return await self.conn.fetch("SELECT channelid, serverid, message, enabled FROM general.welcome")


async def fetch_server_prefixes():
    """Fetch the server prefixes."""
    return await self.conn.fetch("SELECT serverid, prefix FROM general.serverprefix")


async def fetch_bot_bans():
    """Fetch all bot bans."""
    return await self.conn.fetch("SELECT userid FROM general.blacklisted")


async def fetch_mod_mail():
    """Fetch mod mail users and channels."""
    return await self.conn.fetch("SELECT userid, channelid FROM general.modmail")


async def fetch_welcome_roles():
    """Fetch all welcome roles."""
    return await self.conn.fetch("SELECT guildid, roleid FROM general.welcomeroles")


async def insert_welcome_role(guild_id: int, role_id: int):
    """Insert or Update a welcome role."""
    await self.conn.execute("INSERT INTO general.welcomeroles(guildid, roleid) VALUES ($1, $2)", guild_id, role_id)


async def update_welcome_role(guild_id: int, role_id: int):
    """Update a guild's welcome role."""
    await self.conn.execute("UPDATE general.welcomeroles SET roleid = $1 WHERE guildid = $2", role_id, guild_id)


async def delete_welcome_role(guild_id: int):
    """Delete a guild's welcome role."""
    await self.conn.execute("DELETE FROM general.welcomeroles WHERE guildid = $1", guild_id)
