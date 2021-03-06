from ..Base import Base
from . import u_logger as log
import discord


class SelfAssignRoles(Base):
    def __init__(self, *args):
        super().__init__(*args)

    #########################
    # ## SelfAssignRoles ## #
    #########################
    async def add_self_role(self, role_id, role_name, server_id):
        """Adds a self-assignable role to a server."""
        role_info = [role_id, role_name]
        await self.ex.conn.execute("INSERT INTO selfassignroles.roles(roleid, rolename, serverid) VALUES ($1, $2, $3)",
                              role_id, role_name, server_id)
        roles = await self.get_assignable_server_roles(server_id)
        if roles:
            roles.append(role_info)
        else:
            cache_info = self.ex.cache.assignable_roles.get(server_id)
            if not cache_info:
                self.ex.cache.assignable_roles[server_id] = {}
                cache_info = self.ex.cache.assignable_roles.get(server_id)
            cache_info['roles'] = [role_info]

    async def get_self_role(self, message_content, server_id):
        """Returns a discord.Object that can be used for adding or removing a role to a member."""
        roles = await self.get_assignable_server_roles(server_id)
        if roles:
            for role in roles:
                role_id = role[0]
                role_name = role[1]
                if role_name.lower() == message_content.lower():
                    return discord.Object(role_id), role_name
        return None, None

    async def check_self_role_exists(self, role_id, role_name, server_id):
        """Check if a role exists as a self-assignable role in a server."""
        cache_info = self.ex.cache.assignable_roles.get(server_id)
        if cache_info:
            roles = cache_info.get('roles')
            if roles:
                for role in roles:
                    c_role_id = role[0]
                    c_role_name = role[1]
                    if c_role_id == role_id or c_role_name == role_name:
                        return True
        return False

    async def remove_self_role(self, role_name, server_id):
        """Remove a self-assignable role from a server."""
        await self.ex.conn.execute("DELETE FROM selfassignroles.roles WHERE rolename = $1 AND serverid = $2", role_name,
                              server_id)
        cache_info = self.ex.cache.assignable_roles.get(server_id)
        if cache_info:
            roles = cache_info.get('roles')
            if roles:
                for role in roles:
                    if role[1].lower() == role_name.lower():
                        roles.remove(role)

    async def modify_channel_role(self, channel_id, server_id):
        """Add or Change a server's self-assignable role channel."""

        def update_cache():
            cache_info = self.ex.cache.assignable_roles.get(server_id)
            if not cache_info:
                self.ex.cache.assignable_roles[server_id] = {'channel_id': channel_id}
            else:
                cache_info['channel_id'] = channel_id

        amount_of_results = self.ex.first_result(
            await self.ex.conn.fetchrow("SELECT COUNT(*) FROM selfassignroles.channels WHERE serverid = $1", server_id))
        if amount_of_results:
            update_cache()
            return await self.ex.conn.execute("UPDATE selfassignroles.channels SET channelid = $1 WHERE serverid = $2",
                                         channel_id, server_id)
        await self.ex.conn.execute("INSERT INTO selfassignroles.channels(channelid, serverid) VALUES($1, $2)", channel_id,
                              server_id)
        update_cache()

    async def remove_current_channel_role(self, channel_id, server_id):
        """Remove the self-assignable role channel if the current channel was previously assigned."""

        cache_info = self.ex.cache.assignable_roles.get(server_id)

        if not cache_info or cache_info['channel_id'] != channel_id:
            raise KeyError

        cache_info['channel_id'] = None
        return await self.ex.conn.execute("DELETE FROM selfassignroles.channels WHERE serverid = $1", server_id)

    async def get_assignable_server_roles(self, server_id):
        """Get all the self-assignable roles from a server."""
        results = self.ex.cache.assignable_roles.get(server_id)
        if results:
            return results.get('roles')

    async def check_for_self_assignable_role(self, message):
        """Main process for processing self-assignable roles."""
        try:
            author = message.author
            server_id = await self.ex.get_server_id(message)
            if await self.check_self_assignable_channel(server_id, message.channel):
                if message.content:
                    prefix = message.content[0]
                    if len(message.content) > 1:
                        msg = message.content[1:len(message.content)]
                    else:
                        return
                    role, role_name = await self.get_self_role(msg, server_id)
                    await self.process_member_roles(message, role, role_name, prefix, author)
        except Exception as e:
            log.console(f"{e} (Exception)", method=self.check_for_self_assignable_role)

    async def check_self_assignable_channel(self, server_id, channel):
        """Check if a channel is a self assignable role channel."""
        if server_id:
            cache_info = self.ex.cache.assignable_roles.get(server_id)
            if cache_info:
                channel_id = cache_info.get('channel_id')
                if channel_id:
                    if channel_id == channel.id:
                        return True

    @staticmethod
    async def check_member_has_role(member_roles, role_id):
        """Check if a member has a role"""
        for role in member_roles:
            if role.id == role_id:
                return True

    async def process_member_roles(self, message, role, role_name, prefix, author):
        """Adds or removes a (Self-Assignable) role from a member"""
        if role:
            if prefix == '-':
                if await self.check_member_has_role(author.roles, role.id):
                    await author.remove_roles(role, reason="Self-Assignable Role", atomic=True)
                    await message.channel.send(
                        f"> {author.display_name}, You no longer have the {role_name} role.", delete_after=10)
                else:
                    await message.channel.send(f"> {author.display_name}, You do not have the {role_name} role.",
                                               delete_after=10)
            elif prefix == '+':
                if await self.check_member_has_role(author.roles, role.id):
                    return await message.channel.send(
                        f"> {author.display_name}, You already have the {role_name} role.", delete_after=10)
                await author.add_roles(role, reason="Self-Assignable Role", atomic=True)
                await message.channel.send(f"> {author.display_name}, You have been given the {role_name} role.",
                                           delete_after=10)
        if not author.bot:
            await message.delete()  # remove the message if it exists in a self-assignable role channel


# self.ex.u_self_assign_roles = SelfAssignRoles()
