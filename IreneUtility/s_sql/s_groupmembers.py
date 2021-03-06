from typing import List

from . import self

IMAGE_COLUMNS = ["thumbnail", "banner"]
DATE_COLUMNS = ["birthdate", "debutdate", "disbanddate"]


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
    await self.conn.execute(f"INSERT INTO groupmembers.member({', '.join(IDOL_COLUMNS)}) VALUES "
                            f"({', '.join([f'${value}' for value in range(1, len(IDOL_COLUMNS) + 1)])})", *args)


async def fetch_latest_idol(full_name, stage_name):
    """
    Fetch the latest idol with a specific full name and stage name.

    :param full_name: Full name of the idol.
    :param stage_name: Stage name of the idol.
    :returns: Latest Idol Information
    """
    return await self.conn.fetchrow(f"SELECT id, {', '.join(IDOL_COLUMNS)} FROM groupmembers.member WHERE "
                                    f"fullname = $1 AND stagename = $2 ORDER BY id DESC", full_name, stage_name)


async def fetch_latest_group(group_name):
    """
    Fetch the latest group with a specific group name.

    :param group_name: Name of the group.
    :returns: Latest Group Information
    """
    return await self.conn.fetchrow(f"SELECT groupid, {', '.join(GROUP_COLUMNS)} FROM groupmembers.groups WHERE "
                                    f"groupname=$1 ORDER BY groupid DESC", group_name)


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


async def update_info(obj_id: int, column: str, content, group=False):
    """
    Update the information of an idol/group.

    WARNING: Do not accept user-input for the column section unless filtered beforehand.

    :param obj_id: (int) Idol/Group ID
    :param column: (str) Column name
    :param content: Content to update with.
    :param group: (bool) If the object is a group.
    """
    table_name = "member" if not group else "groups"
    id_name = "id" if not group else "groupid"
    await self.conn.execute(f"UPDATE groupmembers.{table_name} SET {column} = $1 WHERE {id_name} = $2",
                            content, obj_id)


async def insert_data_mod(user_id: int):
    """Insert a data mod.

    :param user_id: User ID of the data mod to remove.
    """
    await self.conn.execute("INSERT INTO groupmembers.datamods(userid) VALUES($1)", user_id)


async def delete_data_mod(user_id: int):
    """Delete a data mod.

    :param user_id: User ID of the data mod to remove.
    """
    await self.conn.execute("DELETE FROM groupmembers.datamods WHERE userid = $1", user_id)


async def fetch_data_mods() -> List[int]:
    """Fetch data mods

    :returns: (List[int]) A list of user ids.
    """
    user_ids = await self.conn.fetch("SELECT userid FROM groupmembers.datamods")
    if not user_ids:
        return []
    else:
        return [record[0] for record in user_ids]


async def set_global_alias(object_id, alias, is_group):
    """
    Set a global alias

    :param object_id: The idol/group ID
    :param alias: The alias to add
    :param is_group: Whether we have a group as the object.
    """
    await self.conn.execute("INSERT INTO groupmembers.aliases(objectid, alias, isgroup) VALUES($1, $2, $3)",
                               object_id, alias.lower(), is_group)


async def set_local_alias(object_id, alias, is_group, server_id):
    """
    Set a global alias

    :param object_id: The idol/group ID
    :param alias: The alias to add
    :param is_group: Whether we have a group as the object.
    :param server_id: The server ID for the local alias.
    """
    await self.conn.execute(
        "INSERT INTO groupmembers.aliases(objectid, alias, isgroup, serverid) VALUES($1, $2, $3, $4)", object_id,
        alias.lower(), is_group, server_id)


async def remove_global_alias(object_id, alias, is_group):
    """
    Remove a global idol/group alias.

    :param object_id: The idol/group ID
    :param alias: The alias to add
    :param is_group: Whether we have a group as the object.

    """
    await self.conn.execute(
        "DELETE FROM groupmembers.aliases WHERE alias = $1 AND isgroup = $2 AND objectid = $3 AND serverid IS NULL",
        alias, is_group, object_id)


async def remove_local_alias(object_id, alias, is_group, server_id):
    """
    Remove a server idol/group alias.

    :param object_id: The idol/group ID
    :param alias: The alias to add
    :param is_group: Whether we have a group as the object.
    :param server_id: The server ID for the local alias.
    """
    await self.conn.execute(
        "DELETE FROM groupmembers.aliases WHERE alias = $1 AND isgroup = $2 AND serverid = $3 AND objectid = $4",
        alias, is_group, server_id, object_id)


async def add_idol_to_group(idol_id, group_id):
    """
    Add an Idol to a group.

    :param idol_id: Idol ID to add to Group
    :param group_id: Group ID to add Idol to.
    """
    await self.conn.execute("INSERT INTO groupmembers.idoltogroup(idolid, groupid) VALUES($1, $2)", idol_id, group_id)


async def remove_idol_from_group(idol_id, group_id):
    """
    Remove an Idol from a group.

    :param idol_id: Idol ID to remove from a Group
    :param group_id: Group ID to remove an Idol from.
    """
    await self.conn.execute("DELETE FROM groupmembers.idoltogroup WHERE idolid = $1 AND groupid = $2",
                            idol_id, group_id)


async def fetch_db_groups_from_member(idol_id):
    """Fetch all the group ids that belong to a member.

    :param idol_id: Idol ID
    """
    return await self.conn.fetch("SELECT groupid FROM groupmembers.idoltogroup WHERE idolid = $1", idol_id)


