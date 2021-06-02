from ..Base import Base
from .. import models
from . import u_logger as log
import datetime
import discord
import asyncio
import json
from os.path import getsize
import random
import time


# noinspection PyBroadException,PyPep8
class GroupMembers(Base):
    def __init__(self, *args):
        super().__init__(*args)
        self.api_headers = {'Authorization': self.ex.keys.translate_private_key}
        self.api_endpoint = "https://api.irenebot.com/photos/"
        self.local_api_endpoint = f"http://127.0.0.1:{self.ex.keys.api_port}/photos/"

    async def get_if_user_voted(self, user_id):
        time_stamp = self.ex.first_result(
            await self.ex.conn.fetchrow("SELECT votetimestamp FROM general.lastvoted WHERE userid = $1", user_id))
        if time_stamp:
            tz_info = time_stamp.tzinfo
            current_time = datetime.datetime.now(tz_info)
            check = current_time - time_stamp
            log.console(f"It has been {check.seconds} seconds since {user_id} voted.")
            return check.seconds <= 86400
        log.console(f"{user_id} has not voted in the past 24 hours.")

    def check_idol_object(self, obj):
        return isinstance(obj, self.ex.u_objects.Idol)

    async def send_vote_message(self, message):
        """Send the vote message to a user."""
        server_prefix = await self.ex.get_server_prefix(message)
        vote_message = f"> **To call more idol photos for the next 24 hours," \
                       f" please support Irene by voting or becoming a patron through the links at " \
                       f"`{server_prefix}vote` or `{server_prefix}patreon`!**"
        return await message.channel.send(vote_message)

    async def set_global_alias(self, obj, alias):
        """Set an idol/group alias for the bot."""
        obj.aliases.append(alias)
        is_group = int(not self.check_idol_object(obj))
        await self.ex.conn.execute("INSERT INTO groupmembers.aliases(objectid, alias, isgroup) VALUES($1, $2, $3)", obj.id,
                              alias, is_group)

    async def set_local_alias(self, obj, alias, server_id):
        """Set an idol/group alias for a server"""
        local_aliases = obj.local_aliases.get(server_id)
        if local_aliases:
            local_aliases.append(alias)
        else:
            obj.local_aliases[server_id] = [alias]
        is_group = int(not self.check_idol_object(obj))
        await self.ex.conn.execute(
            "INSERT INTO groupmembers.aliases(objectid, alias, isgroup, serverid) VALUES($1, $2, $3, $4)", obj.id,
            alias, is_group, server_id)

    async def remove_global_alias(self, obj, alias):
        """Remove a global idol/group alias """
        obj.aliases.remove(alias)
        is_group = int(not self.check_idol_object(obj))
        await self.ex.conn.execute(
            "DELETE FROM groupmembers.aliases WHERE alias = $1 AND isgroup = $2 AND objectid = $3 AND serverid IS NULL",
            alias, is_group, obj.id)

    async def remove_local_alias(self, obj, alias, server_id):
        """Remove a server idol/group alias"""
        is_group = int(not self.check_idol_object(obj))
        local_aliases = obj.local_aliases.get(server_id)
        if local_aliases:
            local_aliases.remove(alias)
        await self.ex.conn.execute(
            "DELETE FROM groupmembers.aliases WHERE alias = $1 AND isgroup = $2 AND serverid = $3 AND objectid = $4",
            alias, is_group, server_id, obj.id)

    async def get_member(self, idol_id) -> models.Idol:
        """Get a member by the idol id."""
        try:
            idol_id = int(idol_id)
        except:
            # purposefully create an error if an idol id was not passed in. This is useful to not check for it
            # in other commands.
            return
        for idol in self.ex.cache.idols:
            if idol.id == idol_id:
                return idol

    async def get_group(self, group_id) -> models.Group:
        """Get a group by the group id."""
        try:
            group_id = int(group_id)
        except:
            # purposefully create an error if a group id was not passed in. This is useful to not check for it
            # in other commands.
            return
        for group in self.ex.cache.groups:
            if group.id == group_id:
                return group

    @staticmethod
    async def format_card_fields(obj, card_formats):
        """Formats all relevant card fields to be displayed"""
        final_string = ""
        for attr_name, display_format in card_formats.items():
            if not getattr(obj, attr_name):
                continue
            if isinstance(display_format, str):
                final_string += f"{display_format}{getattr(obj, attr_name)}\n"
            elif isinstance(display_format, list) and len(display_format) == 2:
                final_string += f"{display_format[0]}{getattr(obj, attr_name)}{display_format[1]}\n"
            else:
                raise TypeError
        return final_string

    async def set_embed_card_info(self, obj, group=False, server_id=None):
        """Sets General Information about a Group or Idol."""

        if group:
            title = f"{obj.name} [{obj.id}]\n"
            card_description = await self.format_card_fields(obj, self.ex.cache.group_description)
        else:
            title = f"{obj.full_name} ({obj.stage_name}) [{obj.id}]\n"
            card_description = await self.format_card_fields(obj, self.ex.cache.idol_description)

        general_description = await self.format_card_fields(obj, self.ex.cache.general_description)
        website_description = await self.format_card_fields(obj, self.ex.cache.website_description)

        full_description = f"{general_description}" \
                           f"{card_description}" \
                           f"{website_description}"

        embed = await self.ex.create_embed(title=title, color=self.ex.get_random_color(), title_desc=full_description)
        if obj.tags:
            embed.add_field(name="Tags", value=', '.join(obj.tags), inline=False)
        if obj.aliases:
            embed.add_field(name="Aliases", value=', '.join(obj.aliases), inline=False)
        if obj.local_aliases.get(server_id):
            embed.add_field(name="Server Aliases", value=', '.join(obj.local_aliases.get(server_id)), inline=False)
        if group:
            if obj.members:
                try:
                    value = await self.get_member_names_as_string(obj)
                except:
                    value = f"The group ({obj.id}) has an Idol that doesn't exist. Please report it.\n"
                embed.add_field(name="Members", value=value, inline=False)
        else:
            if obj.groups:
                value = await self.get_group_names_as_string(obj)
                embed.add_field(name="Groups", value=value)
        if obj.thumbnail:
            embed.set_thumbnail(url=obj.thumbnail)
        if obj.banner:
            embed.set_image(url=obj.banner)
        return embed

    async def get_group_names_as_string(self, idol):
        """Get the group names split by a | ."""
        # note that this used to be simplified to one line, but in the case there are groups that do not exist,
        # a proper check and deletion of fake groups are required
        group_names = []
        for group_id in idol.groups:
            group = await self.get_group(group_id)
            if group:
                group_names.append(f"{group.name} ({group_id})")
            else:
                # make sure the cache exists first before deleting.
                if self.ex.cache.groups:
                    # delete the group connections if it doesn't exist.
                    await self.ex.conn.execute("DELETE FROM groupmembers.idoltogroup WHERE groupid = $1", group_id)
        return f"{' | '.join(group_names)}\n"

    async def check_channel_sending_photos(self, channel_id):
        """Checks a text channel ID to see if it is restricted from having idol photos sent."""
        channel = self.ex.cache.restricted_channels.get(channel_id)
        if channel:
            if not channel[1]:
                return False  # returns False if they are restricted.
        return True

    async def delete_restricted_channel_from_cache(self, channel_id, send_all):
        """Deletes restricted channel from cache."""
        r_channel = self.ex.cache.restricted_channels.get(channel_id)
        if r_channel:
            if r_channel[1] == send_all:
                self.ex.cache.restricted_channels.pop(channel_id)

    async def check_server_sending_photos(self,server_id):
        """Checks a server to see if it has a specific channel to send idol photos to"""
        for channel in self.ex.cache.restricted_channels:
            channel_info = self.ex.cache.restricted_channels.get(channel)
            if channel_info[0] == server_id and channel_info[1] == 1:
                return True  # returns True if they are supposed to send it to a specific channel.

    async def get_channel_sending_photos(self,server_id):
        """Returns a text channel from a server that requires idol photos to be sent to a specific text channel."""
        for channel_id in self.ex.cache.restricted_channels:
            channel_info = self.ex.cache.restricted_channels.get(channel_id)
            if channel_info[0] == server_id and channel_info[1] == 1:
                return self.ex.client.get_channel(channel_id)

    @staticmethod
    def log_idol_command(message):
        """Log an idol photo that was called."""
        log.console(f"IDOL LOG: ChannelID = {message.channel.id} - {message.author} "
                    f"({message.author.id})|| {message.clean_content} ")

    async def get_all_images_count(self):
        """Get the amount of images the bot has."""
        return self.ex.first_result(await self.ex.conn.fetchrow("SELECT COUNT(*) FROM groupmembers.imagelinks"))

    async def get_db_idol_called(self, member_id):
        """Get the amount of times an idol has been called from the database."""
        return self.ex.first_result(
            await self.ex.conn.fetchrow("SELECT Count FROM groupmembers.Count WHERE MemberID = $1", member_id))

    async def get_random_idol(self):
        """Get a random idol with at least 1 photo."""
        idol = random.choice(self.ex.cache.idols)
        if not idol.photo_count:
            idol = await self.get_random_idol()
        return idol

    @staticmethod
    async def get_all_groups():
        """Get all groups."""

    async def get_db_members_in_group(self, group_id):
        """Get the members in a specific group from the database."""
        async def get_member_ids_in_group():
            try:
                for idol_id in await self.ex.sql.s_groupmembers.fetch_members_in_group(group_id):
                    yield idol_id
            except:
                return

        return [idol[0] async for idol in get_member_ids_in_group()] or []

    async def get_db_aliases(self, object_id, group=False):
        """Get the aliases of an idol or group from the database."""
        global_aliases = []
        local_aliases = {}

        async def get_aliases():
            try:
                for t_alias, t_server_id in await self.ex.sql.s_groupmembers.fetch_aliases(object_id, group):
                    yield t_alias, t_server_id
            except:
                return

        async for alias, server_id in get_aliases():
            if server_id:
                server_list = local_aliases.get(server_id)
                if server_list:
                    server_list.append(alias)
                else:
                    local_aliases[server_id] = [alias]
            else:
                global_aliases.append(alias)
        return global_aliases, local_aliases

    async def get_db_groups_from_member(self, member_id):
        """Return all the group ids an idol is in from the database."""
        groups = await self.ex.conn.fetch("SELECT groupid FROM groupmembers.idoltogroup WHERE idolid = $1", member_id)
        return [group[0] for group in groups]

    async def add_idol_to_group(self, member_id: int, group_id: int):
        (await self.ex.u_group_members.get_group(group_id)).members.append(member_id)
        return await self.ex.conn.execute("INSERT INTO groupmembers.idoltogroup(idolid, groupid) VALUES($1, $2)",
                                     member_id, group_id)

    async def remove_idol_from_group(self, member_id: int, group_id: int):
        (await self.ex.u_group_members.get_group(group_id)).members.remove(member_id)
        return await self.ex.conn.execute("DELETE FROM groupmembers.idoltogroup WHERE idolid = $1 AND groupid = $2",
                                     member_id, group_id)

    async def send_names(self, ctx, mode, user_page_number=1, group_ids=None):
        """Send the names of all idols in an embed with many pages."""
        server_prefix = await self.ex.get_server_prefix(ctx)

        async def check_mode(embed_temp):
            """Check if it is grabbing their full names or stage names."""
            if mode == "fullname":
                embed_temp = await self.ex.set_embed_author_and_footer(embed_temp,
                                                                  f"Type {server_prefix}members for Stage Names.")
            else:
                embed_temp = await self.ex.set_embed_author_and_footer(embed_temp,
                                                                  f"Type {server_prefix}fullnames for Full Names.")
            return embed_temp

        is_mod = self.ex.check_if_mod(ctx)
        embed_lists = []
        page_number = 1
        embed = discord.Embed(title=f"Idol List Page {page_number}", color=0xffb6c1)
        counter = 1
        for group in self.ex.cache.groups:
            names = []
            if (group.name != "NULL" and group.photo_count != 0) or is_mod:
                if not group_ids or group.id in group_ids:
                    for group_member in group.members:
                        member = await self.get_member(group_member)
                        if member:
                            if member.photo_count or is_mod:
                                if mode == "fullname":
                                    member_name = member.full_name
                                else:
                                    member_name = member.stage_name
                                if is_mod:
                                    names.append(f"{member_name} ({member.id}) | ")
                                else:
                                    names.append(f"{member_name} | ")
                    final_names = "".join(names)
                    if not final_names:
                        final_names = "None"
                    if is_mod:
                        embed.insert_field_at(counter, name=f"{group.name} ({group.id})", value=final_names,
                                              inline=False)
                    else:
                        embed.insert_field_at(counter, name=f"{group.name}", value=final_names, inline=False)
                    if counter == 10:
                        page_number += 1
                        await check_mode(embed)
                        embed_lists.append(embed)
                        embed = discord.Embed(title=f"Idol List Page {page_number}", color=0xffb6c1)
                        counter = 0
                    counter += 1
        # if counter did not reach 10, current embed needs to be saved.
        await check_mode(embed)
        embed_lists.append(embed)
        if user_page_number > len(embed_lists) or user_page_number < 1:
            user_page_number = 1
        msg = await ctx.send(embed=embed_lists[user_page_number - 1])
        # if embeds list only contains 1 embed, do not paginate.
        if len(embed_lists) > 1:
            await self.ex.check_left_or_right_reaction_embed(msg, embed_lists, user_page_number - 1)

    async def set_embed_with_aliases(self, name, server_id=None):
        """Create an embed with the aliases of the names of groups or idols sent in"""
        members = await self.get_idol_where_member_matches_name(name, mode=1, server_id=server_id)
        groups, group_names = await self.get_group_where_group_matches_name(name, mode=1, server_id=server_id)
        embed_list = []
        count = 0
        page_number = 1
        embed = discord.Embed(title=f"{name} Aliases Page {page_number}", description="", color=self.ex.get_random_color())
        for member in members:
            aliases = ', '.join(member.aliases)
            local_aliases = member.local_aliases.get(server_id)
            if local_aliases:
                aliases += ", ".join(local_aliases)
            embed.add_field(name=f"{member.full_name} ({member.stage_name}) [Idol {member.id}]",
                            value=aliases or "None", inline=True)
            count += 1
            if count == 24:
                count = 0
                page_number += 1
                embed_list.append(embed)
                embed = discord.Embed(title=f"{name} Aliases Page {page_number}", description="",
                                      color=self.ex.get_random_color())
        for group in groups:
            aliases = ', '.join(group.aliases)
            embed.add_field(name=f"{group.name} [Group {group.id}]", value=aliases or "None", inline=True)
            count += 1
            if count == 24:
                count = 0
                page_number += 1
                embed_list.append(embed)
                embed = discord.Embed(title=f"{name} Aliases Page {page_number}", description="",
                                      color=self.ex.get_random_color())
        if count:
            embed_list.append(embed)
        return embed_list

    async def set_embed_with_all_aliases(self, mode, server_id=None):
        """Send the names of all aliases in an embed with many pages."""

        def create_embed():
            return discord.Embed(title=f"{mode} Global/Local Aliases Page {page_number}", color=self.ex.get_random_color())

        if mode == "Group":
            all_info = self.ex.cache.groups
            is_group = True
        else:
            all_info = self.ex.cache.idols
            is_group = False
        embed_list = []
        count = 0
        page_number = 1
        embed = create_embed()
        for info in all_info:
            aliases = ",".join(info.aliases)
            local_aliases = info.local_aliases.get(server_id)
            if local_aliases:
                aliases += ", ".join(local_aliases)
            if aliases:
                if not is_group:
                    embed.add_field(name=f"{info.full_name} ({info.stage_name}) [{info.id}]", value=aliases,
                                    inline=True)
                else:
                    embed.add_field(name=f"{info.name} [{info.id}]", value=aliases, inline=True)
                count += 1
            if count == 10:
                count = 0
                embed_list.append(embed)
                page_number += 1
                embed = create_embed()
        if count != 0:
            embed_list.append(embed)
        return embed_list

    async def check_idol_post_reactions(self, message, user_msg, idol, link, guessing_game=False):
        """Check the reactions on an idol post or guessing game."""
        try:
            if message is not None:
                reload_image_emoji = self.ex.keys.reload_emoji
                dead_link_emoji = self.ex.keys.dead_emoji
                if not guessing_game:
                    await message.add_reaction(reload_image_emoji)
                await message.add_reaction(dead_link_emoji)
                message = await message.channel.fetch_message(message.id)

                def image_check(user_reaction, reaction_user):
                    """check the user that reacted to it and which emoji it was."""
                    user_check = (reaction_user == user_msg.author) or (
                                reaction_user.id == self.ex.keys.owner_id) or reaction_user.id in self.ex.keys.mods_list
                    dead_link_check = str(user_reaction.emoji) == dead_link_emoji
                    reload_image_check = str(user_reaction.emoji) == reload_image_emoji
                    guessing_game_check = user_check and dead_link_check and user_reaction.message.id == message.id
                    idol_post_check = user_check and (
                                dead_link_check or reload_image_check) and user_reaction.message.id == message.id
                    if guessing_game:
                        return guessing_game_check
                    return idol_post_check

                async def reload_image():
                    """Wait for a user to react, and reload the image if it's the reload emoji."""
                    try:
                        reaction, user = await self.ex.client.wait_for('reaction_add', check=image_check, timeout=60)
                        if str(reaction) == reload_image_emoji:
                            channel = message.channel
                            await message.delete()
                            # message1 = await channel.send(embed=embed)
                            message1 = await channel.send(link)
                            await self.check_idol_post_reactions(message1, user_msg, idol, link)
                        elif str(reaction) == dead_link_emoji:
                            if await self.ex.u_patreon.check_if_patreon(user.id):
                                await message.delete()
                            else:
                                await message.clear_reactions()
                                server_prefix = await self.ex.get_server_prefix(message)
                                warning_msg = f"Report images as dead links (2nd reaction) ONLY if the image does not load or it's not a photo of the idol.\nYou can have this message removed by becoming a {server_prefix}patreon"
                                if guessing_game:
                                    warning_msg = f"This image has been reported as a dead image, not a photo of the idol, or a photo with several idols.\nYou can have this message removed by becoming a {server_prefix}patreon"
                                await message.edit(content=warning_msg, suppress=True, delete_after=45)
                            await self.send_dead_image(None, link, user, idol, int(guessing_game))
                    except asyncio.TimeoutError:
                        await message.clear_reactions()
                    except Exception as err:
                        log.console(err)

                await reload_image()
        except:
            pass

    async def get_dead_links(self):
        return await self.ex.conn.fetch("SELECT deadlink, messageid, idolid FROM groupmembers.deadlinkfromuser")

    async def delete_dead_link(self, link, idol_id):
        return await self.ex.conn.execute("DELETE FROM groupmembers.deadlinkfromuser WHERE deadlink = $1 AND idolid = $2",
                                     link, idol_id)

    async def set_forbidden_link(self, link, idol_id):
        return await self.ex.conn.execute("INSERT INTO groupmembers.forbiddenlinks(link, idolid) VALUES($1, $2)", link,
                                     idol_id)

    async def send_dead_image(self, channel, link, user, idol, is_guessing_game):
        channel = channel or self.ex.cache.dead_image_channel
        if not channel:
            return

        try:
            game = ""
            if is_guessing_game:
                game = "-- Guessing Game"
            special_message = f"""**Dead Image For {idol.full_name} ({idol.stage_name}) ({idol.id}) {game}
    Sent in by {user.name}#{user.discriminator} ({user.id}).**"""
            msg, api_url = await self.idol_post(channel, idol, photo_link=link, special_message=special_message)
            self.ex.cache.dead_image_cache[msg.id] = [str(link), user.id, idol.id, is_guessing_game]
            await self.ex.conn.execute(
                "INSERT INTO groupmembers.deadlinkfromuser(deadlink, userid, messageid, idolid, guessinggame) VALUES($1, $2, $3, $4, $5)",
                str(link), user.id, msg.id, idol.id, is_guessing_game)
            await msg.add_reaction(self.ex.keys.check_emoji)
            await msg.add_reaction(self.ex.keys.trash_emoji)
            await msg.add_reaction(self.ex.keys.next_emoji)
        except Exception as e:
            log.console(f"Send Dead Image - {e}")

    async def get_idol_where_member_matches_name(self, name, mode=0, server_id=None):
        """Get idol object if the name matches an idol"""
        idol_list = []
        name = name.lower()
        for idol in self.ex.cache.idols:
            local_aliases = None
            if server_id:
                local_aliases = idol.local_aliases.get(server_id)
            if not mode:
                if idol.full_name and idol.stage_name:
                    if name == idol.full_name.lower() or name == idol.stage_name.lower():
                        idol_list.append(idol)
            else:
                if idol.full_name and idol.stage_name:
                    if idol.stage_name.lower() in name or idol.full_name.lower() in name:
                        idol_list.append(idol)
            for alias in idol.aliases:
                if not mode:
                    if alias == name:
                        idol_list.append(idol)
                else:
                    if alias in name:
                        idol_list.append(idol)
            if local_aliases:
                for alias in local_aliases:
                    if await self.check_to_add_alias_to_list(alias, name, mode):
                        idol_list.append(idol)

        # remove any duplicates
        idols = list(dict.fromkeys(idol_list))
        return idols

    @staticmethod
    async def check_to_add_alias_to_list(alias, name, mode=0):
        """Check whether to add an alias to a list. Compares a name with an existing alias."""
        if not mode:
            if alias == name:
                return True
        else:
            if alias in name:
                return True
        return False

    async def get_group_where_group_matches_name(self, name, mode=0, server_id=None):
        """Get group ids for a specific name."""
        group_list = []
        name = name.lower()
        for group in self.ex.cache.groups:
            try:
                aliases = group.aliases
                local_aliases = None
                if server_id:
                    local_aliases = group.local_aliases.get(server_id)
                if not mode:
                    if group.name:
                        if name == group.name.lower():
                            group_list.append(group)
                else:
                    if group.name:
                        if group.name.lower() in name:
                            group_list.append(group)
                            name = (name.lower()).replace(group.name, "")
                for alias in aliases:
                    if await self.check_to_add_alias_to_list(alias, name, mode):
                        group_list.append(group)
                        if mode:
                            name = (name.lower()).replace(alias, "")
                if local_aliases:
                    for alias in local_aliases:
                        if await self.check_to_add_alias_to_list(alias, name, mode):
                            group_list.append(group)
                            if mode:
                                name = (name.lower()).replace(alias, "")

            except Exception as e:
                log.console(e)
        # remove any duplicates
        group_list = list(dict.fromkeys(group_list))
        # print(id_list)
        if not mode:
            return group_list
        else:
            return group_list, name

    async def process_names(self, ctx, page_number_or_group, mode):
        """Structures the input for idol names commands and sends information to transfer the names to the channels."""
        if isinstance(page_number_or_group, int):
            await self.send_names(ctx, mode, page_number_or_group)
        elif isinstance(page_number_or_group, str):
            server_id = await self.ex.get_server_id(ctx)
            groups, name = await self.get_group_where_group_matches_name(page_number_or_group, mode=1,
                                                                         server_id=server_id)
            await self.send_names(ctx, mode, group_ids=[group.id for group in groups])

    async def check_group_and_idol(self, message_content, server_id=None):
        """returns specific idols being called from a reference to a group ex: redvelvet irene"""
        groups, new_message = await self.get_group_where_group_matches_name(message_content, mode=1,
                                                                            server_id=server_id)
        members = await self.get_idol_where_member_matches_name(new_message, mode=1, server_id=server_id)
        member_list = [member
                       for group in groups for member in members
                       if member.id in group.members]
        return member_list or None

    async def update_member_count(self, idol):
        """Update the amount of times an idol has been called."""
        if not idol.called:
            idol.called = 1
            await self.ex.conn.execute("INSERT INTO groupmembers.count VALUES($1, $2)", idol.id, 1)
        else:
            idol.called += 1
            await self.ex.conn.execute("UPDATE groupmembers.Count SET Count = $1 WHERE MemberID = $2", idol.called,
                                  idol.id)

    async def set_as_group_photo(self, link):
        await self.ex.conn.execute("UPDATE groupmembers.imagelinks SET groupphoto = $1 WHERE link = $2", 1, str(link))

    async def get_google_drive_link(self, api_url):
        """Get the google drive link based on the api's image url."""
        # commenting this out because now the file ids are in the api urls.
        # return self.ex.first_result(
        #   await self.ex.conn.fetchrow("SELECT driveurl FROM groupmembers.apiurl WHERE apiurl = $1", str(api_url)))
        beginning_position = api_url.find("/idol/") + 6
        ending_position = api_url.find("image.")
        if ending_position == -1:
            ending_position = api_url.find("video.")
        api_url_id = int(api_url[beginning_position:ending_position])  # the file id hidden in the url
        return self.ex.first_result(await self.ex.conn.fetchrow("SELECT link FROM groupmembers.imagelinks WHERE id = $1", api_url_id))

    async def __post_msg(self, channel, file=None, embed=None, message_str=None, timeout=None):
        """Post a file,embed, or message to a text channel and return it.

        :param channel: (discord.Channel) Channel to send message to.
        :param file: (discord.File) A File to send.
        :param embed: (discord.Embed) An embed to send.
        :param message_str: (str)  A message to send.
        :param timeout: (int) A delay for deleting the message.

        :returns: (discord.Message) Message that was created.
        """
        message = None
        try:
            message = await channel.send(message_str, file=file, embed=embed, delete_after=timeout)
        except Exception as e:
            # link may not be properly registered.
            print(f"{e} -> u_groupmembers.__post_msg")
        return message

    async def __get_image_msg(self, channel, idol, group_id=None, photo_link=None, user_id=None, guild_id=None,
                              special_message=None, guessing_game=False, scores=None, msg_timeout=None):
        """Make an idol photo request to API and post a msg.

        :param channel: (discord.Channel) Channel that the embed/image should be posted to.
        :param idol: (IreneUtility Idol object) Idol that will be posted.
        :param photo_link: Image that will be embedded.
        :param group_id: Group ID the idol may be posted with. (used for if a group photo was called instead).
        :param special_message: Any message that should be applied to the post.
        :param user_id: User ID that is calling the photo.
        :param guild_id: Guild ID that the photo is being requested from.
        :param guessing_game: (bool) Whether the method is called from a guessing game.
        :param scores: (dict) Any scores that may come with a game. In a format of {user id : score}
        :param msg_timeout: Amount of time before deleting a message.
        """
        # args from this method (used for recursive purposes).
        args = {idol, group_id, channel}

        # kwargs from this method (used for recursive purposes).
        kwargs = {
            "photo_link": photo_link,
            "user_id": user_id,
            "guild_id": guild_id,
            "special_message": special_message,
            "guessing_game": guessing_game,
            "scores": scores,
            "msg_timeout": msg_timeout
        }

        # set defaults for image posting.
        file = None
        embed = None

        # params to pass into api endpoint.
        api_params = {
            'allow_group_photos': int(not guessing_game),
            'redirect': 0  # we do not want the endpoint to redirect us to the image.
        }

        # increment amount of times we are calling api.
        self.ex.cache.bot_api_idol_calls += 1

        # endpoint to access.
        endpoint = f"{self.api_endpoint if self.ex.test_bot else self.local_api_endpoint}{idol.id}"

        # make api request.
        async with self.ex.session.post(endpoint, headers=self.api_headers, params=api_params) as r:
            data = json.loads(await r.text())
            image_host_url = data.get('final_image_link')
            file_location = data.get('location')
            file_name = data.get('file_name')
            if r.status in [200, 301]:
                if self.ex.upload_from_host:
                    file = await self.__handle_file(file_location, file_name)
            elif r.status == 415:  # handle videos
                # Make sure we do not get videos in a guessing game.
                if guessing_game:
                    return await self.__get_image_msg(*args, **kwargs)

                file = await self.__handle_file(file_location, file_name)
                if not file:
                    return await self.__get_image_msg(*args, **kwargs)
            else:
                await self.__handle_error(channel, idol.id, r.status)

        if guessing_game:
            # discord may have bad image loading time, so we will wait 2 seconds.
            # this is important because we want the guessing time to be matched up to when the photo appears.
            await asyncio.sleep(2)

        if not file:
            embed = await self.get_idol_post_embed(group_id, idol, image_host_url, user_id=user_id,
                                                   guild_id=channel.guild.id, guessing_game=guessing_game,
                                                   scores=scores)
            embed.set_image(url=image_host_url)

        msg = await self.__post_msg(channel, file=file, embed=embed, message_str=special_message, timeout=msg_timeout)

        return msg, photo_link

    @staticmethod
    async def __handle_file(file_location, file_name):
        """Handles API Status 415 (Video Retrieved) and returns a discord File.

        :param request: The connection to the endpoint.
        :param file_location: Location of the file.
        :param file_name: Name of the file.

        :returns: (discord.File) Discord File that contains the video.
        """
        file_size = getsize(file_location)
        if file_size < 8388608:  # 8 MB
            return discord.File(file_location, file_name)

    @staticmethod
    async def __handle_error(channel, idol_id, status):
        """Handles API Status For Image Retrieval (400/404) (502)

        :param channel: (discord.Channel) Channel that the message should be posted to.
        :param idol_id: (int) Idol ID that was supposed to be posted.
        :param status: (int) Request Status
        """
        channel_msg = None

        if status in [400, 404]:
            log_msg = f"No photos were found for this idol ({idol_id}) - {status}."
            channel_msg = f"**ERROR: No photos were found for this idol ({idol_id}).**"
        elif status == 403:
            log_msg = f"API Key Missing or Invalid Key {status}."
        elif status == 500:
            log_msg = f"API Issue {status}."
        elif status == 502:
            channel_msg = log_msg = f"API is currently being overloaded with requests or is down {status}."
        else:
            log_msg = f"Idol Photo Status Code from API {status}."

        if log_msg:
            log.console(log_msg)
        if channel_msg:
            await channel.send(channel_msg)

    async def get_idol_post_embed(self, group_id, idol, photo_link, user_id=None, guild_id=None, guessing_game=False,
                                  scores=None):
        """The embed for an idol post."""
        if not guessing_game:
            if not group_id:
                embed = discord.Embed(title=f"{idol.full_name} ({idol.stage_name}) [{idol.id}]", color=self.ex.get_random_color(),
                                      url=photo_link)
            else:
                group = await self.get_group(group_id)
                embed = discord.Embed(title=f"{group.name} ({idol.stage_name}) [{idol.id}]",
                                      color=self.ex.get_random_color(), url=photo_link)
            patron_msg = f"Please consider becoming a {await self.ex.get_server_prefix(guild_id)}patreon."

            # when user_id is None, the post goes to the dead images channel.
            if user_id:
                if not await self.ex.u_patreon.check_if_patreon(user_id):
                    embed.set_footer(text=patron_msg)
        else:
            current_scores = ""
            if scores:
                for user_id in scores:
                    current_scores += f"<@{user_id}> -> {scores.get(user_id)}\n"
            embed = discord.Embed(description=current_scores,
                                  color=self.ex.get_random_color(), url=photo_link)
        return embed

    async def idol_post(self, channel, idol, **kwargs):
        """The main process for managing the errors behind an api call for an idol's photo.

        :param channel: (discord.Channel) Channel that the embed/image should be posted to.
        :param idol: (IreneUtility Idol object) Idol that will be posted.
        :param photo_link: Image that will be embedded.
        :param group_id: Group ID the idol may be posted with. (used for if a group photo was called instead).
        :param special_message: Any message that should be applied to the post.
        :param user_id: User ID that is calling the photo.
        :param guessing_game: (bool) Whether the method is called from a guessing game.
        :param scores: (dict) Any scores that may come with a game. In a format of {user id : score}
        :param msg_timeout: Amount of time before deleting a message.
        """
        msg, image_host = None, None

        try:
            kwargs["guild_id"] = channel.guild.id
            msg, image_host = await self.__get_image_msg(channel, idol, **kwargs)  # post image msg

            await self.update_member_count(idol)  # update amount of times an idol has been called.
        except AttributeError:  # resolve dms
            await channel.send("It is not possible to receive Idol Photos in DMs.")
        except discord.Forbidden:  # resolve 403
            pass
        except Exception as e:  # resolve all errors
            log.console(f"{e} -> u_groupmembers.idol_post")
        return msg, image_host

    def check_reset_limits(self):
        if time.time() - self.ex.cache.commands_used['reset_time'] > 86400:  # 1 day in seconds
            # reset the dict
            self.ex.cache.commands_used = {"reset_time": time.time()}

    def add_user_limit(self, message_sender):
        if message_sender.id not in self.ex.cache.commands_used:
            self.ex.cache.commands_used[message_sender.id] = [1, time.time()]
        else:
            self.ex.cache.commands_used[message_sender.id] = [self.ex.cache.commands_used[message_sender.id][0] + 1, time.time()]

    # noinspection PyPep8
    async def check_user_limit(self, message_sender, message_channel, no_vote_limit=False):
        user = await self.ex.get_user(message_sender)
        patron_message = self.ex.cache.languages[user.language]['groupmembers']['patron_msg']
        patron_message = await self.ex.replace(patron_message, [
            ['idol_post_send_limit', self.ex.keys.idol_post_send_limit],
            ['owner_super_patron_benefit', self.ex.keys.owner_super_patron_benefit],
            ['bot_id', self.ex.keys.bot_id],
            ['patreon_link', self.ex.keys.patreon_link]
        ])
        limit = self.ex.keys.idol_post_send_limit
        if no_vote_limit:
            # amount of votes that can be sent without voting.
            limit = self.ex.keys.idol_no_vote_send_limit
        if message_sender.id not in self.ex.cache.commands_used:
            return
        if not await self.ex.u_patreon.check_if_patreon(message_sender.id) and \
                self.ex.cache.commands_used[message_sender.id][0] > limit:
            # noinspection PyPep8
            if not await self.ex.u_patreon.check_if_patreon(message_channel.guild.owner.id,
                                                       super_patron=True) and not no_vote_limit:
                return await message_channel.send(patron_message)
            elif self.ex.cache.commands_used[message_sender.id][0] > self.ex.keys.owner_super_patron_benefit and not no_vote_limit:
                return await message_channel.send(patron_message)
            else:
                return True

    # noinspection PyPep8
    async def request_image_post(self, message, idol, channel):
        """Checks if the user can post an image, then posts it."""
        photo_msg, api_url, posted = None, None, False

        try:
            async with channel.typing():
                # check if there is a maintenance *checks if user also has perms during a maintenance*
                if not await self.ex.events.check_maintenance(message):
                    await self.ex.u_miscellaneous.send_maintenance_message(channel)
                    return photo_msg, api_url, posted

                # if the user is banned
                if await self.ex.u_miscellaneous.check_if_bot_banned(message.author.id):
                    return photo_msg, api_url, posted

                # if the user is a patron
                if await self.ex.u_patreon.check_if_patreon(message.author.id):
                    raise self.ex.exceptions.Pass

                # If the user has not voted and they have passed the no vote limit.
                if await self.check_user_limit(message.author, message.channel, no_vote_limit=True):
                    if not await self.get_if_user_voted(message.author.id):
                        return await self.send_vote_message(message)

                # finds out the user's current post limit and if it has been surpassed.
                if not await self.check_user_limit(message.author, channel):
                    raise self.ex.exceptions.Pass

        except self.ex.exceptions.Pass:
            # an image should be posted without going through further checcks.
            pass

        except Exception as e:
            log.console(e)

        # post the image.
        photo_msg, api_url = await self.idol_post(channel, idol, user_id=message.author.id)
        posted = True

        return photo_msg, api_url, posted

    async def choose_random_member(self, members=None, groups=None):
        """Choose a random member object from a member or group list given."""

        async def check_photo_count(t_member_ids):
            """chooses a random idol and returns one that has photos."""
            t_member_id = random.choice(t_member_ids)
            t_member = await self.get_member(t_member_id)
            if not t_member.photo_count:
                t_member = await check_photo_count(t_member_ids)
            return t_member

        idol = None
        group_idol = None
        groups_with_photos = []

        if groups:
            for group in groups:
                if group.photo_count:
                    groups_with_photos.append(group)
        if groups_with_photos:
            member_ids = (random.choice(groups_with_photos)).members
            group_idol = await check_photo_count(member_ids)

        if members:
            new_members = []
            for member in members:
                if member.photo_count:
                    new_members.append(member)
            if new_members:
                idol = random.choice(new_members)

        # This is checking for the case an idol and group have the same name.
        if idol and group_idol:
            return random.choice([idol, group_idol])

        return idol or group_idol

    async def get_member_names_as_string(self, group):
        """Get the member names split by a | ."""
        return f"{' | '.join([f'{(await self.get_member(idol_id)).stage_name} [{idol_id}]' for idol_id in group.members])}\n"


# self.ex.u_group_members = GroupMembers()
