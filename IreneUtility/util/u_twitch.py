from ..Base import Base
from . import u_logger as log
import json


# noinspection PyBroadException,PyPep8
class Twitch(Base):
    def __init__(self, *args):
        super().__init__(*args)

    async def check_guild_limit(self, guild_id):
        """check if a guild is allowed to follow more channels"""
        channels_followed = 0
        for guilds in self.ex.cache.twitch_channels.values():
            if guild_id in guilds:
                channels_followed += 1
        return channels_followed < self.ex.twitch_guild_follow_limit

    async def check_channel_followed(self, twitch_username, guild_id):
        """Check if a guild is being followed."""
        twitch_username = twitch_username.lower()
        guilds = self.ex.cache.twitch_channels.get(twitch_username)
        if guilds:
            return guild_id in guilds

    async def get_discord_channel(self, guild_id):
        """Get the channel that follow announcements are sent to."""
        return self.ex.cache.twitch_guild_to_channels.get(guild_id)

    async def get_discord_role(self, guild_id):
        return self.ex.cache.twitch_guild_to_roles.get(guild_id)

    async def add_channel(self, twitch_username, guild_id):
        """Follows a twitch channel."""
        twitch_username = twitch_username.lower()
        guilds = self.ex.cache.twitch_channels.get(twitch_username)
        if guilds:
            guilds.append(guild_id)
        else:
            self.ex.cache.twitch_channels[twitch_username] = [guild_id]
        await self.ex.conn.execute("INSERT INTO twitch.channels(username, guildid) VALUES($1, $2)", twitch_username,
                              guild_id)

    async def set_discord_channel(self, guild_id, channel_id):
        """Set the channel for a guild that receives live updates."""
        if await self.get_discord_channel(guild_id) or await self.get_discord_role(guild_id):
            await self.ex.conn.execute("UPDATE twitch.guilds SET channelid = $1 WHERE guildid = $2", channel_id, guild_id)
        else:
            await self.ex.conn.execute("INSERT INTO twitch.guilds(guildid, channelid) VALUES ($1, $2)", guild_id, channel_id)

        self.ex.cache.twitch_guild_to_channels[guild_id] = channel_id

    async def remove_channel(self, twitch_username, guild_id):
        """Stop following a twitch channel."""
        twitch_username = twitch_username.lower()
        guilds = self.ex.cache.twitch_channels.get(twitch_username) or []
        if guild_id in guilds:
            guilds.remove(guild_id)
        await self.ex.conn.execute("DELETE FROM twitch.channels WHERE username = $1 AND guildid = $2", twitch_username,
                              guild_id)

    async def change_twitch_role(self, guild_id, role_id):
        """Adds/Changes a twitch role that gets mentioned on twitch updates."""
        if await self.get_discord_role(guild_id) or await self.get_discord_channel(guild_id):
            await self.ex.conn.execute("UPDATE twitch.guilds SET roleid = $1 WHERE guildid = $2", role_id, guild_id)
        else:
            await self.ex.conn.execute("INSERT INTO twitch.guilds(guildid, roleid) VALUES ($1, $2)", guild_id, role_id)
        self.ex.cache.twitch_guild_to_roles[guild_id] = role_id

    async def delete_twitch_role(self, guild_id):
        """Delete a twitch role mentioned on updates."""
        self.ex.cache.twitch_guild_to_roles[guild_id] = None
        await self.ex.conn.execute("UPDATE twitch.guilds SET roleid = NULL WHERE guildid = $1", guild_id)

    async def get_channels_followed(self, guild_id):
        """Get the twitch channels a discord server follows."""
        channels_followed = []
        for twitch_username, guilds in self.ex.cache.twitch_channels.items():
            if guild_id in guilds:
                channels_followed.append(twitch_username)
        return channels_followed

    async def reset_twitch_token(self):
        """Get/and reset twitch access token to use on the twitch api."""
        end_point = f"https://id.twitch.tv/oauth2/token?client_id={self.ex.keys.twitch_client_id}&client_secret=" \
            f"{self.ex.keys.twitch_client_secret}&grant_type=client_credentials"
        async with self.ex.session.post(end_point) as r:
            if r.status == 200:
                body = await r.text()
                self.ex.twitch_token = (json.loads(body)).get('access_token')
                return self.ex.twitch_token
        self.ex.twitch_token = None

    async def send_twitch_announcement(self, twitch_username):
        guilds = self.ex.cache.twitch_channels.get(twitch_username)
        for guild_id in guilds:
            try:
                if not guild_id:
                    continue

                channel_id = self.ex.cache.twitch_guild_to_channels.get(guild_id)
                if not channel_id:
                    continue

                # confirm the channel has not already received a post for this streamer.
                if await self.ex.sql.s_twitch.check_twitch_already_posted(twitch_username, channel_id):
                    continue

                # set the channel id as already posted.
                await self.ex.sql.s_twitch.set_twitch_posted(twitch_username, channel_id)

                role_id = self.ex.cache.twitch_guild_to_roles.get(guild_id)

                end_message = f", {twitch_username} is now live on https://www.twitch.tv/" \
                    f"{twitch_username} ! Make sure to go check it out!"
                if role_id:
                    message = f"Hey <@&{role_id}>{end_message}"
                else:
                    message = f"Hey @everyone{end_message}"

                channel = self.ex.client.get_channel(channel_id)
                if not channel:
                    channel = await self.ex.client.fetch_channel(channel_id)

                if not channel:
                    raise Exception

                await channel.send(message)
            except Exception as e:
                log.console(f"{e} (Exception) - Failed to send twitch announcement to Guild ID: {guild_id}",
                            method=self.send_twitch_announcement)
