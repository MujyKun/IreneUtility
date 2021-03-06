from ..Base import Base


# noinspection PyBroadException,PyPep8
class Patreon(Base):
    def __init__(self, *args):
        super().__init__(*args)
    
    async def get_patreon_users(self):
        """Get the permanent patron users"""
        return await self.ex.conn.fetch("SELECT userid from patreon.users")

    async def get_patreon_role_members(self, super_patron=False):
        """Get the members in the patreon roles.

        NOTE: Translator, Proofreader, and DataMod roles are considered patron roles.
        """
        support_guild = self.ex.client.get_guild(int(self.ex.keys.bot_support_server_id))
        patrons = []
        # API call will not show role.members
        if not super_patron:
            patreon_role = support_guild.get_role(int(self.ex.keys.patreon_role_id))
            translator_role = support_guild.get_role(int(self.ex.keys.translator_role_id))
            proofreader_role = support_guild.get_role(int(self.ex.keys.proofreader_role_id))
            datamod_role = support_guild.get_role(int(self.ex.keys.datamod_role_id))
            if translator_role:
                patrons += translator_role.members
                for member in translator_role.members:
                    user = await self.ex.get_user(member.id)
                    user.is_translator = True
            if proofreader_role:
                patrons += proofreader_role.members
                for member in proofreader_role.members:
                    user = await self.ex.get_user(member.id)
                    user.is_proofreader = True
            if datamod_role:
                patrons += datamod_role.members
                for member in datamod_role.members:
                    user = await self.ex.get_user(member.id)
                    if not user.is_data_mod:
                        # we should have had the data mod cache load them already.
                        try:
                            await self.ex.sql.s_groupmembers.insert_data_mod(user.id)
                        except:
                            ...  # possible duplicate error.
                        user.is_data_mod = True
                current_data_mod_ids = [member.id for member in datamod_role.members]
                current_cached_data_mods = [user_id for user_id in await self.ex.sql.s_groupmembers.fetch_data_mods()]
                for data_mod_id in current_cached_data_mods:
                    if data_mod_id not in current_data_mod_ids:
                        await self.ex.sql.s_groupmembers.delete_data_mod(data_mod_id)

        else:
            patreon_role = support_guild.get_role(int(self.ex.keys.patreon_super_role_id))
        if patreon_role:
            patrons += patreon_role.members
        return patrons

    async def check_if_patreon(self, user_id, super_patron=False):
        """Check if the user is a patreon.
        There are two ways to check if a user ia a patreon.
        The first way is getting the members in the Patreon/Super Patreon Role.
        The second way is a table to check for permanent patreon users that are directly added by the bot owner.
        -- After modifying -> We take it straight from cache now.
        """
        user = await self.ex.get_user(user_id)
        if super_patron:
            return user.super_patron
        return user.patron

    async def add_to_patreon(self, user_id):
        """Add user as a permanent patron."""
        try:
            user_id = int(user_id)
            await self.ex.conn.execute("INSERT INTO patreon.users(userid) VALUES($1)", user_id)
            user = await self.ex.get_user(user_id)
            user.patron = True
            user.super_patron = True
        except:
            pass

    async def remove_from_patreon(self, user_id):
        """Remove user from being a permanent patron."""
        try:
            user_id = int(user_id)
            await self.ex.conn.execute("DELETE FROM patreon.users WHERE userid = $1", user_id)
            user = await self.ex.get_user(user_id)
            user.patron = False
            user.super_patron = False
        except:
            pass

    async def reset_patreon_cooldown(self, ctx):
        """Checks if the user is a patreon and resets their cooldown."""
        # Super Patrons also have the normal Patron role.
        if await self.check_if_patreon(ctx.author.id):
            ctx.command.reset_cooldown(ctx)
