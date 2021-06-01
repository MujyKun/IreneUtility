from . import self


async def add_guild(guild):
    """
    Adds a guild to the guild table.

    :param guild: D.py Guild
    """
    guild_info = ((guild.id, guild.name, len(guild.emojis), f"{guild.region}", guild.afk_timeout, guild.icon,
                   guild.owner_id, guild.banner, guild.description, guild.mfa_level, guild.splash,
                   guild.premium_tier, guild.premium_subscription_count, len(guild.text_channels),
                   len(guild.voice_channels), len(guild.categories), guild.emoji_limit, guild.member_count,
                   len(guild.roles), guild.shard_id, guild.created_at))
    input_param = ",".join([f"${i+1}" for i in range(len(guild_info))])
    await self.conn.execute(f"INSERT INTO stats.guilds VALUES ({input_param})", *guild_info)


async def remove_guild(guild):
    """
    Removes a guild from the guild table.

    :param guild: D.py Guild
    """
    await self.conn.execute("DELETE FROM stats.guilds WHERE guildid = $1", guild.id)
