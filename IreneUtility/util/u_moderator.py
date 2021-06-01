from ..Base import Base


class Moderator(Base):
    def __init__(self, *args):
        super().__init__(*args)
        
    async def add_welcome_message_server(self, channel_id, guild_id, message, enabled):
        """Adds a new welcome message server."""
        await self.ex.conn.execute(
            "INSERT INTO general.welcome(channelid, serverid, message, enabled) VALUES($1, $2, $3, $4)", channel_id,
            guild_id, message, enabled)
        self.ex.cache.welcome_messages[guild_id] = {"channel_id": channel_id, "message": message, "enabled": enabled}

    async def check_welcome_message_enabled(self, server_id):
        """Check if a welcome message server is enabled."""
        return self.ex.cache.welcome_messages[server_id]['enabled'] == 1

    async def update_welcome_message_enabled(self, server_id, enabled):
        """Update a welcome message server's enabled status"""
        await self.ex.conn.execute("UPDATE general.welcome SET enabled = $1 WHERE serverid = $2", int(enabled), server_id)
        self.ex.cache.welcome_messages[server_id]['enabled'] = int(enabled)

    async def update_welcome_message_channel(self, server_id, channel_id):
        """Update the welcome message channel."""
        await self.ex.conn.execute("UPDATE general.welcome SET channelid = $1 WHERE serverid = $2", channel_id, server_id)
        self.ex.cache.welcome_messages[server_id]['channel_id'] = channel_id

    async def update_welcome_message(self, server_id, message):
        await self.ex.conn.execute("UPDATE general.welcome SET message = $1 WHERE serverid = $2", message, server_id)
        self.ex.cache.welcome_messages[server_id]['message'] = message

    async def toggle_games(self, channel_id: int) -> bool:
        """Toggles game usage in a text channel.

        Will return True if channel has games enabled.
        """
        if channel_id in self.ex.cache.channels_with_disabled_games:
            await self.ex.sql.s_moderator.enable_game_in_channel(channel_id)
            return True
        else:
            await self.ex.sql.s_moderator.disable_game_in_channel(channel_id)
            return False



# self.ex.u_moderator = Moderator()
