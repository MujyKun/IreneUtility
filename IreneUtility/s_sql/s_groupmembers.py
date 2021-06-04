from . import self


async def fetch_restricted_channels():
    """Fetch all restricted idol photo channels."""
    return await self.conn.fetch("SELECT channelid, serverid, sendhere FROM groupmembers.restricted")


async def fetch_dead_links():
    """Fetch all dead links."""
    return await self.conn.fetch("SELECT deadlink, userid, messageid, idolid, guessinggame FROM "
                                 "groupmembers.deadlinkfromuser")


async def fetch_all_images():
    """Fetch all images."""
    return await self.conn.fetch("SELECT id, memberid, link, groupphoto, facecount, filetype FROM "
                                 "groupmembers.imagelinks")


async def fetch_all_idols():
    """Fetch all idols."""
    return await self.conn.fetch("""SELECT id, fullname, stagename, formerfullname, formerstagename, birthdate,
            birthcountry, birthcity, gender, description, height, twitter, youtube, melon, instagram, vlive, spotify,
            fancafe, facebook, tiktok, zodiac, thumbnail, banner, bloodtype, tags, difficulty
            FROM groupmembers.Member ORDER BY id""")


async def fetch_all_groups():
    """Fetch all groups."""
    return await self.conn.fetch("""SELECT groupid, groupname, debutdate, disbanddate, description, twitter, 
            youtube, melon, instagram, vlive, spotify, fancafe, facebook, tiktok, fandom, company,
            website, thumbnail, banner, gender, tags FROM groupmembers.groups 
            ORDER BY groupname""")


async def fetch_aliases(object_id, group=False):
    """Fetch all global and server aliases of an idol or group.

    :param object_id: An Idol or Group id
    :param group: Whether the object is a group.
    """
    return await self.conn.fetch("SELECT alias, serverid FROM groupmembers.aliases "
                                 "WHERE objectid = $1 AND isgroup = $2", object_id, int(group))


async def fetch_members_in_group(group_id):
    """Fetches the idol ids in a group.

    :param group_id: The group's id
    """
    return await self.conn.fetch("SELECT idolid FROM groupmembers.idoltogroup WHERE groupid = $1", group_id)


async def fetch_send_idol_photos():
    """Fetches the text channels and idols that should be sent to the channel after t time."""
    return await self.conn.fetch("SELECT channelid, idolids FROM groupmembers.sendidolphotos")


async def delete_send_idol_photo_channel(text_channel_id: int):
    """Deletes a text channel from receiving photos after t time.

    :param text_channel_id: ID of the text channel that should no longer receive idol photos.
    """
    await self.conn.execute("DELETE FROM groupmembers.sendidolphotos WHERE channelid = $1", text_channel_id)


async def insert_send_idol_photo(text_channel_id: int, idol_id: int):
    """Inserts a text channel to receive photos from certain idols.

    :param text_channel_id: ID of the text channel that will receive idol photos from the idol.
    :param idol_id: The idol id that will have their photos be sent to the text channel.
    """
    await self.conn.execute("INSERT INTO groupmembers.sendidolphotos(channelid, idolids) VALUES ($1, $2)",
                            text_channel_id, {idol_id})


async def update_send_idol_photo(text_channel_id: int, idol_ids: list):
    """
    Update a text channel's idol list

    :param text_channel_id: ID of the text channel that will receive idol photos from the idol.
    :param idol_ids: ALL idol ids that should be associated with the text channel
    """
    await self.conn.execute("UPDATE groupmembers.sendidolphotos SET idolids = $1 WHERE channelid = $2", idol_ids,
                            text_channel_id)
