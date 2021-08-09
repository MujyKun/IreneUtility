from . import self


IDOL_COLUMNS = ["fullname", "stagename", "formerfullname", "formerstagename", "birthdate", "birthcountry",
                "birthcity", "gender", "description", "height", "twitter", "youtube", "melon", "instagram",
                "vlive", "spotify", "fancafe", "facebook", "tiktok", "zodiac", "thumbnail", "banner",
                "bloodtype", "tags", "difficulty"]

GROUP_COLUMNS = ["groupname", "debutdate", "disbanddate", "description", "twitter", "youtube", "melon", "instagram",
                 "vlive", "spotify", "fancafe", "facebook", "tiktok", "fandom", "company", "website", "thumbnail",
                 "banner", "gender", "tags"]


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
    return await self.conn.fetch(f"SELECT id, {', '.join(IDOL_COLUMNS)} FROM groupmembers.member ORDER BY id")


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


async def get_idol_id_by_image_id(image_id: int):
    """
    Get an idol id from a unique image id.

    :returns: Idol ID or NoneType (if the image id does not exist)
    """
    member = await self.conn.fetchrow("SELECT memberid FROM groupmembers.imagelinks WHERE id = $1", image_id)
    return None if not member else member[0]


async def insert_new_idol(*args):
    """
    Insert a new idol.
    """
    await self.conn.execute(f"INSERT INTO groupmembers.member({IDOL_COLUMNS}) VALUES "
                            f"({', '.join([f'${value}' for value in range(1, len(IDOL_COLUMNS) + 1)])})", *args)


async def fetch_latest_idol(full_name, stage_name):
    """
    Fetch the latest idol with a specific full name and stage name.

    :param full_name: Full name of the idol.
    :param stage_name: Stage name of the idol.
    :returns: Latest Idol Information
    """
    return await self.conn.fetchrow(f"SELECT id, {', '.join(IDOL_COLUMNS)} FROM groupmembers.member WHERE "
                                    f"fullname = $1, stagename = $ 2 ORDER BY id DESC", full_name, stage_name)


async def fetch_latest_group(group_name):
    """
    Fetch the latest group with a specific group name.

    :param group_name: Name of the group.
    :returns: Latest Group Information
    """
    return await self.conn.fetchrow(f"SELECT id, {', '.join(GROUP_COLUMNS)} FROM groupmembers.groups WHERE "
                                    f"groupname=$1 ORDER BY id DESC", group_name)


async def insert_new_group(*args):
    """
    Insert a new group.
    """
    await self.conn.execute(f"INSERT INTO groupmembers.groups({', '.join(GROUP_COLUMNS)}) VALUES "
                            f"({', '.join([f'${value}' for value in range(1, len(GROUP_COLUMNS) + 1)])})", *args)


async def set_member_banner(idol_id, image_url):
    """
    Set the banner of an idol.

    :param idol_id: Idol ID to set the banner for.
    :param image_url: Image url to set the banner to.
    """
    await self.conn.execute("UPDATE groupmembers.member SET banner = $1 WHERE id = $2", image_url, idol_id)


async def set_member_thumbnail(idol_id, image_url):
    """
    Set the thumbnail of an idol.

    :param idol_id: Idol ID to set the thumbnail for.
    :param image_url: Image url to set the thumbnail to.
    """
    await self.conn.execute("UPDATE groupmembers.member SET thumbnail = $1 WHERE id = $2", image_url, idol_id)


async def set_group_banner(group_id, image_url):
    """
    Set the banner of a group.

    :param group_id: Group ID to set the banner for.
    :param image_url: Image url to set the banner to.
    """
    await self.conn.execute("UPDATE groupmembers.groups SET banner = $1 WHERE groupid = $2", image_url, group_id)


async def set_group_thumbnail(group_id, image_url):
    """
    Set the thumbnail of a group.

    :param group_id: Group ID to set the thumbnail for.
    :param image_url: Image url to set the thumbnail to.
    """
    await self.conn.execute("UPDATE groupmembers.groups SET thumbnail = $1 WHERE groupid = $2", image_url, group_id)
