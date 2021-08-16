from typing import Optional, List

from ..Base import Base
from .. import models
from . import u_logger as log
import datetime
import discord
import asyncio
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
        self.successful_codes = [200, 301, 415]

    async def get_if_user_voted(self, user_id):
        """
        Check if a user voted:

        :param user_id: The user's ID.
        :returns: (bool) True if they voted in the past 24 hours.
        """
        time_stamp = self.ex.first_result(
            await self.ex.conn.fetchrow("SELECT votetimestamp FROM general.lastvoted WHERE userid = $1", user_id))
        if time_stamp:
            tz_info = time_stamp.tzinfo
            current_time = datetime.datetime.now(tz_info)
            check = current_time - time_stamp
            log.console(f"It has been {check.seconds} seconds since {user_id} voted.", method=self.get_if_user_voted)
            return check.seconds <= 86400
        log.console(f"{user_id} has not voted in the past 24 hours.", method=self.get_if_user_voted)

    def check_idol_object(self, obj):
        """
        Check if we are dealing with an Idol object

        :param obj: Object to check.
        :returns: (bool) Whether the object is an Idol.
        """
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
        alias = alias.lower()
        obj.aliases.append(alias)
        is_group = int(not self.check_idol_object(obj))
        await self.ex.sql.s_groupmembers.set_global_alias(obj.id, alias, is_group)

    async def set_local_alias(self, obj, alias, server_id):
        """Set an idol/group alias for a server"""
        alias = alias.lower()
        local_aliases = obj.local_aliases.get(server_id)
        if local_aliases:
            local_aliases.append(alias)
        else:
            obj.local_aliases[server_id] = [alias]
        is_group = int(not self.check_idol_object(obj))
        await self.ex.sql.s_groupmembers.set_local_alias(obj.id, alias, is_group, server_id)

    async def remove_global_alias(self, obj, alias):
        """Remove a global idol/group alias """
        obj.aliases.remove(alias)
        is_group = int(not self.check_idol_object(obj))
        await self.ex.sql.s_groupmembers.remove_global_alias(obj.id, alias, is_group)

    async def remove_local_alias(self, obj, alias, server_id):
        """Remove a server idol/group alias"""
        is_group = int(not self.check_idol_object(obj))
        local_aliases = obj.local_aliases.get(server_id)
        if local_aliases:
            local_aliases.remove(alias)
        await self.ex.sql.s_groupmembers.remove_local_alias(obj.id, alias, is_group, server_id)

    async def get_member(self, idol_id) -> Optional[models.Idol]:
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

    async def get_group(self, group_id) -> Optional[models.Group]:
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

    async def format_card_fields(self, obj, card_formats):
        """Formats all relevant card fields to be displayed"""
        final_string = ""
        for attr_name, display_format in card_formats.items():
            attribute = getattr(obj, attr_name)
            if isinstance(attribute, self.ex.u_objects.Subscription):  # vlive or twitter
                attribute = attribute.id
            if not attribute:
                continue
            if isinstance(display_format, str):
                final_string += f"{display_format}{attribute}\n"
            elif isinstance(display_format, list) and len(display_format) == 2:
                final_string += f"{display_format[0]}{attribute}{display_format[1]}\n"
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
        group_names = []
        for group_id in idol.groups:
            group = await self.get_group(group_id)
            if group:
                group_names.append(f"{group.name} ({group_id})")
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

    async def check_server_sending_photos(self, server_id):
        """Checks a server to see if it has a specific channel to send idol photos to"""
        for channel in self.ex.cache.restricted_channels:
            channel_info = self.ex.cache.restricted_channels.get(channel)
            if channel_info[0] == server_id and channel_info[1] == 1:
                return True  # returns True if they are supposed to send it to a specific channel.

    async def get_channel_sending_photos(self, server_id):
        """Returns a text channel from a server that requires idol photos to be sent to a specific text channel."""
        for channel_id in self.ex.cache.restricted_channels:
            channel_info = self.ex.cache.restricted_channels.get(channel_id)
            if channel_info[0] == server_id and channel_info[1] == 1:
                return self.ex.client.get_channel(channel_id)

    def log_idol_command(self, message):
        """Log an idol photo that was called."""
        log.console(f"IDOL LOG: ChannelID = {message.channel.id} - {message.author} "
                    f"({message.author.id})|| {message.clean_content} ", method=self.log_idol_command)

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
        (await self.ex.u_group_members.get_member(member_id)).groups.append(group_id)
        return await self.ex.conn.execute("INSERT INTO groupmembers.idoltogroup(idolid, groupid) VALUES($1, $2)",
                                          member_id, group_id)

    async def remove_idol_from_group(self, member_id: int, group_id: int):
        (await self.ex.u_group_members.get_group(group_id)).members.remove(member_id)
        (await self.ex.u_group_members.get_member(member_id)).groups.remove(group_id)

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
        embed = discord.Embed(title=f"{name} Aliases Page {page_number}", description="",
                              color=self.ex.get_random_color())
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
            return discord.Embed(title=f"{mode} Global/Local Aliases Page {page_number}",
                                 color=self.ex.get_random_color())

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
                        log.console(f"{err} (Exception)", method=self.check_idol_post_reactions)

                await reload_image()
        except:
            pass

    async def get_dead_links(self):
        return await self.ex.conn.fetch("SELECT deadlink, messageid, idolid FROM groupmembers.deadlinkfromuser")

    async def delete_dead_link(self, link, idol_id):
        return await self.ex.conn.execute(
            "DELETE FROM groupmembers.deadlinkfromuser WHERE deadlink = $1 AND idolid = $2",
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
            log.console(f"{e} (Exception) - Send Dead Image", method=self.send_dead_image)

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
                log.console(f"{e} (Exception)", method=self.get_group_where_group_matches_name)
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
        """Set a photo as a group photo."""
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
        return self.ex.first_result(await self.ex.conn.fetchrow("SELECT link FROM groupmembers.imagelinks WHERE id = $1"
                                                                , api_url_id))

    @staticmethod
    async def __post_msg(channel, file=None, embed=None, message_str=None, timeout=None):
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
            if message_str or embed or file:
                message = await channel.send(message_str, file=file, embed=embed, delete_after=timeout)
        except discord.Forbidden:
            raise discord.Forbidden
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
        msg = None

        # params to pass into api endpoint.
        api_params = {
            'allow_video': int(not guessing_game),
            'redirect': 0,  # we do not want the endpoint to redirect us to the image.
            'min_faces': 1,
            'max_faces': 1 if guessing_game else 999
        }

        # increment amount of times we are calling api.
        self.ex.cache.bot_api_idol_calls += 1

        # endpoint to access.
        endpoint = f"{self.api_endpoint if self.ex.test_bot else self.local_api_endpoint}{idol.id}"

        # make api request.
        async with self.ex.session.post(endpoint, headers=self.api_headers, params=api_params) as r:
            if r.status in self.successful_codes:
                # define variables if we had a successful connection.
                data = await r.json()
                image_host_url = data.get('final_image_link')
                file_location = data.get('location')
                file_name = data.get('file_name')

            if r.status in [200, 301]:
                if self.ex.upload_from_host:
                    file = await self.__handle_file(file_location, file_name)
            elif r.status == 415:  # handle videos
                # Make sure we do not get videos in a guessing game.
                # The new api params will make sure that we do not reach this point in a guessing game.
                # However, just in case the file was not properly scanned (new uploads), this condition will remain.
                if guessing_game:
                    return await self.__get_image_msg(*args, **kwargs)

                file = await self.__handle_file(file_location, file_name)
                if not file:
                    return await self.__get_image_msg(*args, **kwargs)
            else:
                # deal with errors.
                await self.__handle_error(channel, idol.id, r.status)
                return msg, photo_link

        if guessing_game:
            # discord may have bad image loading time, so we will wait 2 seconds.
            # this is important because we want the guessing time to be matched up to when the photo appears.
            if not self.ex.upload_from_host:
                await asyncio.sleep(2)

        if (not file or self.ex.upload_from_host) and r.status != 415:
            embed = await self.get_idol_post_embed(group_id, idol, image_host_url, user_id=user_id,
                                                   guild_id=channel.guild.id, guessing_game=guessing_game,
                                                   scores=scores)

            embed_image_url = image_host_url if not self.ex.upload_from_host else f"attachment://{file_name}"

            # If the file is too big, we will use the image host url.
            if self.ex.upload_from_host and not file:
                embed_image_url = image_host_url

            embed.set_image(url=embed_image_url)

        msg = await self.__post_msg(channel, file=file, embed=embed, message_str=special_message, timeout=msg_timeout)

        return msg, photo_link

    @staticmethod
    async def __handle_file(file_location, file_name):
        """Handles API Status 415 (Video Retrieved) / 200 / 301 and returns a discord File.

        :param file_location: Location of the file.
        :param file_name: Name of the file.

        :returns: (discord.File) Discord File that contains the video.
        """
        file_size = getsize(file_location)
        if file_size < 8388608:  # 8 MB
            return discord.File(file_location, file_name)

    async def __handle_error(self, channel, idol_id, status):
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
            log.console(log_msg, method=self.__handle_error)
        if channel_msg:
            await channel.send(channel_msg)
        self.ex.api_issues += 1

    async def get_idol_post_embed(self, group_id, idol, photo_link, user_id=None, guild_id=None, guessing_game=False,
                                  scores=None):
        """The embed for an idol post."""
        if not guessing_game:
            if not group_id:
                embed = discord.Embed(title=f"{idol.full_name} ({idol.stage_name}) [{idol.id}]",
                                      color=self.ex.get_random_color(),
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
            if isinstance(channel, discord.DMChannel):
                await channel.send("It is not possible to receive Idol Photos in DMs.")
                return None, None
            kwargs["guild_id"] = channel.guild.id
            msg, image_host = await self.__get_image_msg(channel, idol, **kwargs)  # post image msg

            await self.update_member_count(idol)  # update amount of times an idol has been called.

            # update amount of times a user has called an idol.
            user_id = kwargs.get("user_id")
            if user_id:
                user = self.ex.get_user_main(user_id)
                user.called_idol()

        except AttributeError as e:  # resolve dms
            log.console(f"{e} (AttributeError)", method=self.idol_post)
        except discord.Forbidden:  # resolve 403
            raise discord.Forbidden  # let the client decide what to do.
        except TypeError:
            ...  # missing 2 required positional arguments response & message.
        except Exception as e:  # resolve all errors
            log.console(f"{e} (Exception)", method=self.idol_post)
        return msg, image_host

    def check_reset_limits(self):
        """Checks if the user idol calls needs to be reset back to 0."""
        if time.time() - self.ex.cache.last_idol_reset_time > 86400:  # 1 day in seconds
            self.ex.cache.last_idol_reset_time = time.time()  # reset the time
            # reset user idol calls.
            await self.ex.run_blocking_code(self.reset_user_idol_calls)

    def reset_user_idol_calls(self):
        """Resets all user idol calls to zero."""
        users = self.ex.cache.users.copy()
        for user in users.values():
            user.idol_calls = 0

    # noinspection PyPep8
    async def check_user_limit(self, message_sender, message_channel, no_vote_limit=False):
        """
        Check the user's idol limit.

        :param message_sender: d.py Author
        :param message_channel: d.py Text Channel
        :param no_vote_limit: (bool) True if there is a vote limit to check for.

        :returns: (bool) True if the limit was passed.
        """
        user = await self.ex.get_user(message_sender.id)

        if not user.idol_calls:
            return

        guild_owner = await self.ex.get_user(message_channel.guild.owner.id)

        limit = self.ex.keys.idol_post_send_limit if not no_vote_limit else self.ex.keys.idol_no_vote_send_limit

        if not user.patron and user.idol_calls > limit:
            # Check the server owner's super patron status and whether to provide more idol calls.
            guild_owner_check_failed = not guild_owner.super_patron and not no_vote_limit
            user_capped_with_benefit = user.idol_calls > self.ex.keys.owner_super_patron_benefit and not no_vote_limit

            if guild_owner_check_failed or user_capped_with_benefit:
                await message_channel.send(await self.ex.get_msg(user, "groupmembers", "patron_msg", [
                    ['idol_post_send_limit', self.ex.keys.idol_post_send_limit],
                    ['owner_super_patron_benefit', self.ex.keys.owner_super_patron_benefit],
                    ['bot_id', self.ex.keys.bot_id],
                    ['patreon_link', self.ex.keys.patreon_link]
                ]))
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

                # if the user is requesting from the support server
                if channel.guild:
                    if channel.guild.id == self.ex.keys.bot_support_server_id:
                        raise self.ex.exceptions.Pass

                # If the user has not voted and they have passed the no vote limit.
                if await self.check_user_limit(message.author, message.channel, no_vote_limit=True):
                    if not await self.get_if_user_voted(message.author.id):
                        return await self.send_vote_message(message)

                # finds out the user's current post limit and if it has been surpassed.
                if not await self.check_user_limit(message.author, channel):
                    # this is a successful post.
                    raise self.ex.exceptions.Pass

                return  # do not need to go past this point since we raise a pass exception for success.

        except self.ex.exceptions.Pass:
            # an image should be posted without going through further checks.
            pass

        except Exception as e:
            log.console(f"{e} (Exception)", method=self.request_image_post)

        try:
            # post the image.
            photo_msg, api_url = await self.idol_post(channel, idol, user_id=message.author.id)
            posted = True
        except discord.Forbidden:
            pass

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

    async def manage_send_idol_photo(self, text_channel, idol_id, limit=None):
        """Adds/Removes/Updates idol ids based on the text channel that will be used to send idol photos after t time.

        :param text_channel: discord.TextChannel or text channel id for the idol photo to be sent to
        :param idol_id: idol id to add or remove.
        :param limit: (int) the limit for what the text channel can have. If this is exceeded,
            u_exceptions.Limit will be raised.
        :returns:
            False if text channel input was incorrect.
            'insert' if the idol id was inserted.
            'remove' if the idol id was removed.
            'delete' if the channel was completely removed from the table.
        """
        if isinstance(text_channel, discord.TextChannel):
            text_channel_id = text_channel.id
        elif isinstance(text_channel, int):
            text_channel_id = text_channel
        else:
            return False

        channel = self.ex.client.get_channel(text_channel_id)  # we do not need to fetch here since its ok if its None

        # cache may store ID or discord.TextChannel
        current_idol_ids: list = self.ex.cache.send_idol_photos.get(text_channel_id) or self.ex. \
            cache.send_idol_photos.get(text_channel)

        # check if the text channel does not have any idols.
        if not current_idol_ids:
            await self.ex.sql.s_groupmembers.insert_send_idol_photo(text_channel_id, idol_id)
            self.ex.cache.send_idol_photos[channel or text_channel_id] = [idol_id]
            return "insert"

        # check if the idol already exists with the channel
        if idol_id in current_idol_ids:
            current_idol_ids.remove(idol_id)
            if not current_idol_ids:
                try:
                    self.ex.cache.send_idol_photos.pop(text_channel_id)
                except KeyError:
                    pass

                try:
                    self.ex.cache.send_idol_photos.pop(text_channel)
                except KeyError:
                    pass

                await self.ex.sql.s_groupmembers.delete_send_idol_photo_channel(text_channel_id)
                return "delete"
            await self.ex.sql.s_groupmembers.update_send_idol_photo(text_channel_id, current_idol_ids)
            return "remove"

        # add the idol
        if limit:
            if (len(current_idol_ids)) + 1 > limit:
                raise self.ex.exceptions.Limit
        current_idol_ids.append(idol_id)
        await self.ex.sql.s_groupmembers.update_send_idol_photo(text_channel_id, current_idol_ids)
        return "insert"

    async def delete_channel_from_send_idol(self, text_channel):
        """Deletes a channel permanently from the send idol cache.

        :param text_channel: (discord.TextChannel or int) Key to pop from the cache. The client should know which it is.
        """
        log.console(f"Removing Text Channel "
                    f"{text_channel.id if isinstance(text_channel, discord.TextChannel) else text_channel} "
                    f"from Send Idol Cache Permanently.", method=self.delete_channel_from_send_idol)
        await self.ex.sql.s_groupmembers.delete_send_idol_photo_channel(text_channel)
        try:
            self.ex.cache.send_idol_photos.pop(text_channel)
        except KeyError:
            pass

    async def get_idol_by_image_id(self, image_id):
        """Get an idol object by the unique image id.

        :returns: Idol Object or NoneType
        """
        try:
            idol_id = (await self.ex.sql.s_groupmembers.get_idol_id_by_image_id(image_id)) or None
            if not idol_id:
                return None
            idol = await self.get_member(int(idol_id))
            return idol
        except:
            return None

    async def add_new_idol(self, full_name, stage_name, group_ids: List[str], *args) -> models.Idol:
        """Add new idol to DB and Cache.

        :param full_name: Full name of the Idol.
        :param stage_name: Stage name of the Idol.
        :param group_ids: Group IDs to add to the Idol.
        """
        await self.ex.sql.s_groupmembers.insert_new_idol(*args)

        idol_obj = await self.add_idol_to_cache(
            **(await self.ex.sql.s_groupmembers.fetch_latest_idol(full_name, stage_name)))

        for group_id in group_ids:
            group_id.replace(" ", "")
            group_id = int(group_id)
            await self.add_idol_to_group(idol_obj.id, group_id)
            idol_obj.groups.append(group_id)

        await idol_obj.send_images_to_host()
        return idol_obj

    async def add_new_group(self, group_name, *args) -> models.Group:
        """Add new Group to the DB and cache.

        :param group_name: Group name of the group.
        """
        await self.ex.sql.s_groupmembers.insert_new_group(*args)

        group_obj = await self.add_group_to_cache(
            **(await self.ex.sql.s_groupmembers.fetch_latest_group(group_name)))

        await group_obj.send_images_to_host()
        return group_obj

    async def fix_links(self):
        """Fix all idol/group images that aren't located on the host."""
        for idol in self.ex.cache.idols:
            await asyncio.sleep(0)  # bare yield
            await idol.send_images_to_host()

        for group in self.ex.cache.groups:
            await asyncio.sleep(0)  # bare yield
            await group.send_images_to_host()

    async def add_idol_to_cache(self, **kwargs) -> models.Idol:
        """Add new idol to Cache.

        :returns: (models.Idol) The Idol object that was created.
        """
        idol_obj = self.ex.u_objects.Idol(**kwargs)
        idol_obj.aliases, idol_obj.local_aliases = await self.ex.u_group_members.get_db_aliases(idol_obj.id)
        # add all group ids and remove potential duplicates
        idol_obj.groups = list(dict.fromkeys(await self.ex.u_group_members.get_db_groups_from_member(idol_obj.id)))
        idol_obj.called = await self.ex.u_group_members.get_db_idol_called(idol_obj.id)
        idol_obj.photo_count = self.ex.cache.idol_photos.get(idol_obj.id) or 0
        self.ex.cache.idols.append(idol_obj)

        if not idol_obj.photo_count:
            return idol_obj

        # all of the below conditions must be idols with photos.
        if idol_obj.gender == 'f':
            self.ex.cache.idols_female.add(idol_obj)
        if idol_obj.gender == 'm':
            self.ex.cache.idols_male.add(idol_obj)
        # add all idols to the hard difficulty
        self.ex.cache.idols_hard.add(idol_obj)
        if idol_obj.difficulty in ['medium', 'easy']:
            self.ex.cache.idols_medium.add(idol_obj)
        if idol_obj.difficulty == 'easy':
            self.ex.cache.idols_easy.add(idol_obj)
        return idol_obj

    async def add_group_to_cache(self, **kwargs) -> models.Group:
        """Add new group to Cache.

        :returns: (models.Group) The Group object that was created.
        """
        group_obj = self.ex.u_objects.Group(**kwargs)
        group_obj.aliases, group_obj.local_aliases = await self.get_db_aliases(group_obj.id, group=True)
        # add all idol ids and remove potential duplicates
        group_obj.members = list(
            dict.fromkeys(await self.get_db_members_in_group(group_obj.id)))

        group_obj.photo_count = self.ex.cache.group_photos.get(group_obj.id) or 0
        self.ex.cache.groups.append(group_obj)
        return group_obj

    async def update_info(self, obj_id, column, content, group=False):
        """Update the information of an idol/group in cache and db.

        :param obj_id: (int) Idol/Group ID
        :param column: (str) Column name
        :param content: (str) Content to update with.
        :param group: (bool) If the object is a group.
        """
        obj_id = int(obj_id)

        try:
            # if the user passed in an integer, we should change the type to not cause db issues.
            content = int(content)
        except:
            ...

        if group:
            if column.lower() not in self.ex.sql.s_groupmembers.GROUP_COLUMNS:
                raise NotImplementedError
        else:
            if column.lower() not in self.ex.sql.s_groupmembers.IDOL_COLUMNS:
                raise NotImplementedError

        date = None
        if column.lower() in self.ex.sql.s_groupmembers.DATE_COLUMNS:
            date = datetime.datetime.strptime(content, "%Y-%m-%d")

        obj = await self.get_group(obj_id) if group else await self.get_member(obj_id)
        if not obj:
            raise KeyError

        obj.set_attribute(column, content)

        if column.lower() in self.ex.sql.s_groupmembers.IMAGE_COLUMNS:
            await obj.send_images_to_host()

        await self.ex.sql.s_groupmembers.update_info(obj_id, column, date if date else content, group)

        return obj



