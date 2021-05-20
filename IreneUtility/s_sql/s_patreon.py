from IreneUtility.s_sql import self


async def fetch_cached_patrons():
    """Fetch the cached patrons."""
    # it is possible for the super to sometimes not be fetched (probably when super is 0).
    cached_patrons = await self.conn.fetch("SELECT userid, super FROM patreon.cache")
    proper_cached = []
    for cached_patron in cached_patrons:
        user_id = cached_patron[0]
        try:
            super_patron = cached_patron[1]
        except TypeError:
            super_patron = 0
        proper_cached.append([user_id, super_patron])
    return proper_cached


async def delete_patron(user_id):
    """Delete a patron.

    :param user_id: Discord User ID
    """
    await self.conn.execute("DELETE FROM patreon.cache WHERE userid = $1", user_id)


async def update_patron(user_id, super_patron: int):
    """Updates a patron's status

    :param user_id: Discord User ID
    :param super_patron: 1 for the user becoming a super patron, or 0 if they are a normal patron.
    """
    await self.conn.execute("UPDATE patreon.cache SET super = $1 WHERE userid = $2", super_patron, user_id)


async def add_patron(user_id, super_patron: int):
    """Add a patron

    :param user_id: Discord User ID
    :param super_patron: 1 for the user becoming a super patron, or 0 if they are a normal patron.
    """
    await self.conn.execute("INSERT INTO patreon.cache(userid, super) VALUES($1, $2)", user_id, super_patron)