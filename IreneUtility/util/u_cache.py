from discord.ext import tasks
from ..Base import Base
from . import u_logger as log
import time
import asyncio
import aiofiles
import datetime
import json


# noinspection PyBroadException,PyPep8
class Cache(Base):
    def __init__(self, *args):
        super().__init__(*args)
        
    async def process_cache_time(self, method, name):
        """Process the cache time."""
        past_time = time.time()
        result = await method()
        if result is None or result:  # expecting False on methods that fail to load, do not simplify None.
            creation_time = await self.ex.u_miscellaneous.get_cooldown_time(time.time() - past_time)
            log.console(f"Cache for {name} Created in {creation_time}.")
        return result

    async def create_cache(self, on_boot_up=True):
        """Create the general cache on startup"""
        past_time = time.time()
        # reset custom user cache
        self.ex.cache.users = {}

        cache_info = [
            # patrons are no longer instantly after intents were pushed in place making d.py cache a lot slower.
            # it is instead looped in another method until d.py cache loads.
            [self.load_language_packs, "Language Packs"],
            [self.create_idols, "Idol Photo Count"],
            [self.create_groups, "Group Photo Count"],
            [self.create_user_notifications, "User Notifications"],
            [self.create_patreons, "Patrons"],
            [self.create_mod_mail, "ModMail"],
            [self.create_bot_bans, "Bot Bans"],
            [self.create_logging_channels, "Logged Channels"],
            [self.create_server_prefixes, "Server Prefixes"],
            [self.create_welcome_message_cache, "Welcome Messages"],
            [self.create_temp_channels, "Temp Channels"],
            [self.create_n_word_counter, "NWord Counter"],
            [self.create_command_counter, "Command Counter"],
            [self.create_idol_cache, "Idol Objects"],
            [self.create_group_cache, "Group Objects"],
            [self.create_restricted_channel_cache, "Restricted Idol Channels"],
            [self.create_dead_link_cache, "Dead Links"],
            [self.create_bot_status_cache, "Bot Status"],
            [self.create_bot_command_cache, "Custom Commands"],
            [self.create_weverse_channel_cache, "Weverse Text Channels"],
            [self.create_self_assignable_role_cache, "Self-Assignable Roles"],
            [self.create_reminder_cache, "Reminders"],
            [self.create_timezone_cache, "Timezones"],
            [self.create_guessing_game_cache, "Guessing Game Scores"],
            [self.create_twitch_cache, "Twitch Channels"],
            [self.create_currency_cache, "Currency"],
            [self.create_levels_cache, "Levels"],
            [self.create_language_cache, "User Language"],
            [self.create_playing_cards, "Playing Cards"],
            [self.create_guild_cache, "DB Guild"],
            [self.ex.weverse_client.start, "Weverse"],
            [self.create_gg_filter_cache, "Guessing Game Filter"],
            [self.create_welcome_role_cache, "Welcome Roles"],
            [self.create_disabled_games_cache, "Disabled Games In Channels"]
            # [self.create_image_cache, "Image"],

        ]
        for method, cache_name in cache_info:
            if cache_name in ["DB Guild", "Patrons"]:
                # if the discord cache is loaded, make sure to update the patreon cache since our user objects
                # are reset every time this function is called.
                if not self.ex.discord_cache_loaded or on_boot_up:
                    continue

            if cache_name == "Weverse":
                # do not load weverse cache if the bot has already been running.
                if not self.ex.test_bot and not self.ex.weverse_client.cache_loaded and on_boot_up:
                    # noinspection PyUnusedLocal
                    task = asyncio.create_task(self.process_cache_time(method, "Weverse"))
                continue

            await self.process_cache_time(method, cache_name)
        creation_time = await self.ex.u_miscellaneous.get_cooldown_time(time.time() - past_time)
        log.console(f"Cache Completely Created in {creation_time}.")
        self.ex.irene_cache_loaded = True

    async def create_disabled_games_cache(self):
        """Creates a list of channels with disabled games."""
        self.ex.cache.channels_with_disabled_games = []
        for channel_id in await self.ex.sql.s_moderator.fetch_games_disabled():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.channels_with_disabled_games.append(channel_id[0])

    async def create_image_cache(self):
        """Creates Image objects and stores them in local cache.

        Note that usage of these images is unnecessary as a call to the API would be more efficient.
        Therefore, IreneBot will not be using the image objects directly.
        """
        # image_file_types = ["png", "jpeg", "jpg"]
        video_file_types = ["mp4", "webm"]
        for p_id, member_id, link, group_photo, face_count, file_type \
                in await self.ex.sql.s_groupmembers.fetch_all_images():
            await asyncio.sleep(0)  # bare yield
            idol = await self.ex.u_group_members.get_member(member_id)
            img_or_vid = "image" if file_type not in video_file_types else "video"
            file_name = f"{p_id}{img_or_vid}.{file_type}"
            image_host_url = f"{self.ex.keys.image_host}idol/{file_name}/"
            image_file_location = f"{self.ex.keys.idol_photo_location}{file_name}"
            image = self.ex.u_objects.Image(p_id, file_name, image_file_location, image_host_url, idol,
                                            face_count=face_count)
            idol_images = self.ex.cache.idol_images.get(member_id)
            if idol_images:
                idol_images.append(image)
            else:
                self.ex.cache.idol_images[member_id] = [image]

    async def create_welcome_role_cache(self):
        self.ex.cache.welcome_roles = {}
        for guild_id, role_id in await self.ex.sql.s_general.fetch_welcome_roles():
            try:
                await asyncio.sleep(0)  # bare yield

                try:
                    guild = self.ex.client.get_guild(guild_id) or await self.ex.client.fetch_guild(guild_id)
                except Exception as e:
                    log.console(f"{e} -> Do not have access to fetch guild {guild_id}.")
                    guild = None

                if not guild:
                    continue

                for role in guild.roles:
                    if role.id == role_id:
                        self.ex.cache.welcome_roles[guild] = role
            except Exception as e:
                log.console(f"{e} ->  Failed to process welcome role cache for {guild_id}")

    async def create_playing_cards(self):
        """Crache cache for playing cards."""
        self.ex.cache.playing_cards = {}

        for custom_card_id, file_name, card_id, card_name, value, bg_idol_id in await self.ex.sql.s_blackjack.fetch_playing_cards():
            await asyncio.sleep(0)  # bare yield
            idol = await self.ex.u_group_members.get_member(bg_idol_id)
            card = self.ex.u_objects.PlayingCard(custom_card_id, file_name,
                                                 f"{self.ex.keys.playing_card_location}{file_name}",
                                                 f"{self.ex.keys.image_host}cards/{file_name}", idol,
                                                 card_id=card_id, card_name=card_name, value=value)
            similar_cards = self.ex.cache.playing_cards.get(card_id)
            if similar_cards:
                similar_cards.append(card)
            else:
                self.ex.cache.playing_cards[card_id] = [card]

    async def create_language_cache(self):
        """Create cache for user languages."""
        for user_id, language in await self.ex.sql.s_user.fetch_languages():
            user = await self.ex.get_user(user_id)
            user.language = language

    async def load_language_packs(self):
        """Create cache for language packs."""
        self.ex.cache.languages = {}

        async def get_language_module_and_message():
            # get the modules and messages for each language
            for t_language in self.ex.cache.languages.values():
                await asyncio.sleep(0)  # bare yield
                for t_module in t_language.values():
                    for t_message_name in t_module.keys():
                        yield t_module, t_message_name

        # load the json for every language to cache
        for file_name in self.ex.cache.languages_available:
            await asyncio.sleep(0)  # bare yield
            async with aiofiles.open(f"languages/{file_name}.json") as file:
                self.ex.cache.languages[file_name] = json.loads(await file.read())

        # make the content of all curly braces bolded in all available languages.
        async for module, message_name in get_language_module_and_message():
            await asyncio.sleep(0)  # bare yield
            module[message_name] = self.apply_bold_to_braces(module[message_name])

    @staticmethod
    def apply_bold_to_braces(text: str) -> str:
        """Applys bold markdown in between braces."""
        text = text.replace("{", "**{")
        text = text.replace("}", "}**")
        return text

    async def create_levels_cache(self):
        """Create the cache for user levels."""
        for user_id, rob, daily, beg, profile_level in await self.ex.sql.s_levels.fetch_levels():
            user = await self.ex.get_user(user_id)
            if rob:
                user.rob_level = rob
            if daily:
                user.daily_level = daily
            if beg:
                user.beg_level = beg
            if profile_level:
                user.profile_level = profile_level

    async def create_currency_cache(self):
        """Create cache for currency"""
        for user_id, money in await self.ex.sql.s_currency.fetch_currency():
            user = await self.ex.get_user(user_id)
            user.balance = int(money)

    async def create_gg_filter_cache(self):
        """Create filtering of guessing game cache."""
        for user_info in await self.ex.sql.s_guessinggame.fetch_filter_enabled():
            user_id = user_info[0]
            user = await self.ex.get_user(user_id)
            user.gg_filter = True

        # reset cache for filtered groups
        for user in self.ex.cache.users.values():
            user.gg_groups = []

        # go through all filtered groups regardless if it is enabled
        # so we do not have to change during filter toggle.
        for user_id, group_id in await self.ex.sql.s_guessinggame.fetch_filtered_groups():
            user = await self.ex.get_user(user_id)
            group = await self.ex.u_group_members.get_group(group_id)
            user.gg_groups.append(group)

    async def create_twitch_cache(self):
        """Create cache for twitch followings"""
        self.ex.cache.twitch_channels = {}
        self.ex.cache.twitch_guild_to_channels = {}
        self.ex.cache.twitch_guild_to_roles = {}

        for guild_id, channel_id, role_id in await self.ex.sql.s_twitch.fetch_twitch_guilds():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.twitch_guild_to_channels[guild_id] = channel_id
            self.ex.cache.twitch_guild_to_roles[guild_id] = role_id

        for username, guild_id in await self.ex.sql.s_twitch.fetch_twitch_notifications():
            await asyncio.sleep(0)  # bare yield
            guilds_in_channel = self.ex.cache.twitch_channels.get(username)
            if guilds_in_channel:
                guilds_in_channel.append(guild_id)
            else:
                self.ex.cache.twitch_channels[username] = [guild_id]

    async def create_guessing_game_cache(self):
        """Create cache for guessing game scores"""
        self.ex.cache.guessing_game_counter = {}

        for user_id, easy_score, medium_score, hard_score in await self.ex.sql.s_guessinggame.fetch_gg_stats():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.guessing_game_counter[user_id] = {"easy": easy_score, "medium": medium_score, "hard": hard_score}

    async def create_timezone_cache(self):
        """Create cache for timezones"""
        for user_id, timezone in await self.ex.sql.s_user.fetch_timezones():
            user = await self.ex.get_user(user_id)
            user.timezone = timezone

    async def create_reminder_cache(self):
        """Create cache for reminders"""
        for reason_id, user_id, reason, time_stamp in await self.ex.sql.s_reminder.fetch_reminders():
            user = await self.ex.get_user(user_id)
            reason_list = [reason_id, reason, time_stamp]
            if user.reminders:
                user.reminders.append(reason_list)
            else:
                user.reminders = [reason_list]

    async def create_self_assignable_role_cache(self):
        """Create cache for self assignable roles"""
        self.ex.cache.assignable_roles = {}

        for role_id, role_name, server_id in await self.ex.sql.s_selfassignroles.fetch_all_self_assign_roles():
            await asyncio.sleep(0)  # bare yield
            cache_info = self.ex.cache.assignable_roles.get(server_id)
            if not cache_info:
                self.ex.cache.assignable_roles[server_id] = {}
                cache_info = self.ex.cache.assignable_roles.get(server_id)
            if not cache_info.get('roles'):
                cache_info['roles'] = [[role_id, role_name]]
            else:
                cache_info['roles'].append([role_id, role_name])

        for channel_id, server_id in await self.ex.sql.s_selfassignroles.fetch_all_self_assign_channels():
            await asyncio.sleep(0)  # bare yield
            cache_info = self.ex.cache.assignable_roles.get(server_id)
            if cache_info:
                cache_info['channel_id'] = channel_id
            else:
                self.ex.cache.assignable_roles[server_id] = {'channel_id': channel_id}

    async def create_weverse_channel_cache(self):
        """Create cache for channels that are following a community on weverse."""
        self.ex.cache.weverse_channels = {}

        for channel_id, community_name, role_id, comments_disabled in await self.ex.sql.s_weverse.fetch_weverse():
            await asyncio.sleep(0)  # bare yield
            await self.ex.u_weverse.add_weverse_channel_to_cache(channel_id, community_name)
            await self.ex.u_weverse.add_weverse_role(channel_id, community_name, role_id)
            await self.ex.u_weverse.change_weverse_comment_status(channel_id, community_name, comments_disabled)

    async def create_command_counter(self):
        """Updates Cache for command counter and sessions"""
        self.ex.cache.command_counter = {}
        session_id = await self.get_session_id()

        for command_name, count in await self.ex.sql.s_session.fetch_command(session_id):
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.command_counter[command_name] = count

        self.ex.cache.current_session = self.ex.first_result(await self.ex.sql.s_session.fetch_session_usage(datetime.date.today()))

    async def create_restricted_channel_cache(self):
        """Create restricted idol channel cache"""
        self.ex.cache.restricted_channels = {}
        for channel_id, server_id, send_here in await self.ex.sql.s_groupmembers.fetch_restricted_channels():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.restricted_channels[channel_id] = [server_id, send_here]

    async def create_bot_command_cache(self):
        """Create custom command cache"""
        self.ex.cache.custom_commands = {}

        for server_id, command_name, message in await self.ex.sql.s_customcommands.fetch_custom_commands():
            await asyncio.sleep(0)  # bare yield
            cache_info = self.ex.cache.custom_commands.get(server_id)
            if cache_info:
                cache_info[command_name] = message
            else:
                self.ex.cache.custom_commands[server_id] = {command_name: message}

    async def create_bot_status_cache(self):
        self.ex.cache.bot_statuses = []

        for status in await self.ex.sql.s_general.fetch_bot_statuses():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.bot_statuses.append(status[0])

    async def create_dead_link_cache(self):
        """Creates Dead Link Cache"""
        self.ex.cache.dead_image_cache = {}
        try:
            self.ex.cache.dead_image_channel = await self.ex.client.fetch_channel(self.ex.keys.dead_image_channel_id)
        except Exception as e:
            log.useless(f"{e} - Failed to fetch dead image channel - Cache.create_dead_link_cache")

        for dead_link, user_id, message_id, idol_id, guessing_game in await self.ex.sql.s_groupmembers.fetch_dead_links():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.dead_image_cache[message_id] = [dead_link, user_id, idol_id, guessing_game]

    async def create_idol_cache(self):
        """Create Idol Objects and store them as cache."""
        self.ex.cache.idols = []
        # Clear and update these cache values to prevent breaking the memory reference made by
        # self.ex.cache.difficulty_selection and self.ex.cache.gender_selection
        self.ex.cache.idols_female.clear()
        self.ex.cache.idols_male.clear()
        self.ex.cache.idols_easy.clear()
        self.ex.cache.idols_medium.clear()
        self.ex.cache.idols_hard.clear()

        for idol in await self.ex.sql.s_groupmembers.fetch_all_idols():
            await asyncio.sleep(0)  # bare yield
            idol_obj = self.ex.u_objects.Idol(**idol)
            idol_obj.aliases, idol_obj.local_aliases = await self.ex.u_group_members.get_db_aliases(idol_obj.id)
            # add all group ids and remove potential duplicates
            idol_obj.groups = list(dict.fromkeys(await self.ex.u_group_members.get_db_groups_from_member(idol_obj.id)))
            idol_obj.called = await self.ex.u_group_members.get_db_idol_called(idol_obj.id)
            idol_obj.photo_count = self.ex.cache.idol_photos.get(idol_obj.id) or 0
            self.ex.cache.idols.append(idol_obj)

            if not idol_obj.photo_count:
                continue

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

        self.ex.cache.gender_selection['all'] = set(self.ex.cache.idols)

    async def create_group_cache(self):
        """Create Group Objects and store them as cache"""
        self.ex.cache.groups = []

        for group in await self.ex.sql.s_groupmembers.fetch_all_groups():
            await asyncio.sleep(0)  # bare yield
            group_obj = self.ex.u_objects.Group(**group)
            group_obj.aliases, group_obj.local_aliases = await self.ex.u_group_members.get_db_aliases(group_obj.id,
                                                                                                 group=True)
            # add all idol ids and remove potential duplicates
            group_obj.members = list(
                dict.fromkeys(await self.ex.u_group_members.get_db_members_in_group(group_obj.id)))
            group_obj.photo_count = self.ex.cache.group_photos.get(group_obj.id) or 0
            self.ex.cache.groups.append(group_obj)

    async def process_session(self):
        """Sets the new session id, total used, and time format for distinguishing days."""
        current_time_format = datetime.date.today()
        if self.ex.cache.session_id is None:
            if self.ex.cache.total_used is None:
                self.ex.cache.total_used = (self.ex.first_result(await self.ex.sql.s_session.fetch_total_session_usage())) or 0
            try:
                await self.ex.sql.s_session.add_new_session(self.ex.cache.total_used, 0, current_time_format)
            except:
                # session for today already exists.
                pass
            self.ex.cache.session_id = self.ex.first_result(await self.ex.sql.s_session.fetch_session_id(datetime.date.today()))
            self.ex.cache.session_time_format = current_time_format
        else:
            # check that the date is correct, and if not, call get_session_id to get the new session id.
            if current_time_format != self.ex.cache.session_time_format:
                self.ex.cache.current_session = 0
                self.ex.cache.session_id = None
                self.ex.cache.session_id = await self.get_session_id()

    async def get_session_id(self):
        """Force get the session id, this will also set total used and the session id."""
        await self.process_session()
        return self.ex.cache.session_id

    async def create_n_word_counter(self):
        """Update NWord Cache"""
        for user_id, n_word_counter in await self.ex.sql.s_general.fetch_n_word():
            user = await self.ex.get_user(user_id)
            user.n_word = n_word_counter

    async def create_temp_channels(self):
        """Create the cache for temp channels."""
        self.ex.cache.temp_channels = {}

        for channel_id, delay in await self.ex.sql.s_general.fetch_temp_channels():
            await asyncio.sleep(0)  # bare yield
            removal_time = delay
            if removal_time < 60:
                removal_time = 60
            self.ex.cache.temp_channels[channel_id] = removal_time

    async def create_welcome_message_cache(self):
        """Create the cache for welcome messages."""
        self.ex.cache.welcome_messages = {}

        for channel_id, server_id, message_id, enabled in await self.ex.sql.s_general.fetch_welcome_messages():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.welcome_messages[server_id] = {"channel_id": channel_id, "message": message_id, "enabled": enabled}

    async def create_server_prefixes(self):
        """Create the cache for server prefixes."""
        self.ex.cache.server_prefixes = {}

        for server_id, prefix in await self.ex.sql.s_general.fetch_server_prefixes():
            await asyncio.sleep(0)  # bare yield
            self.ex.cache.server_prefixes[server_id] = prefix

    async def create_logging_channels(self):
        """Create the cache for logged servers and channels."""
        self.ex.cache.logged_channels = {}
        self.ex.cache.list_of_logged_channels = []

        for p_id, server_id, channel_id, send_all in await self.ex.sql.s_logging.fetch_logged_servers():
            await asyncio.sleep(0)  # bare yield
            channel_ids = []
            for channel in await self.ex.sql.s_logging.fetch_logged_channels(p_id):
                await asyncio.sleep(0)  # bare yield
                self.ex.cache.list_of_logged_channels.append(channel[0])
                channel_ids.append(channel[0])
            self.ex.cache.logged_channels[server_id] = {
                "send_all": send_all,
                "logging_channel": channel_id,
                "channels": channel_ids
            }

    async def create_bot_bans(self):
        """Create the cache for banned users from the bot."""
        for user in await self.ex.sql.s_general.fetch_bot_bans():
            user_id = user[0]
            user_obj = await self.ex.get_user(user_id)
            user_obj.bot_banned = True

    async def create_mod_mail(self):
        """Create the cache for existing mod mail"""
        self.ex.cache.mod_mail = {}

        for user_id, channel_id in await self.ex.sql.s_general.fetch_mod_mail():
            user = await self.ex.get_user(user_id)
            user.mod_mail_channel_id = channel_id
            self.ex.cache.mod_mail[user_id] = [channel_id]  # full list

    async def create_patreons(self):
        """Create the cache for Patrons."""
        try:
            permanent_patrons = await self.ex.u_patreon.get_patreon_users()
            # normal patrons contains super patrons as well
            normal_patrons = [patron.id for patron in await self.ex.u_patreon.get_patreon_role_members(super_patron=False)]
            super_patrons = [patron.id for patron in await self.ex.u_patreon.get_patreon_role_members(super_patron=True)]

            # the reason for db cache is because of the new discord rate limit
            # where it now takes 20+ minutes for discord cache to fully load, meaning we can only
            # access the roles after 20 minutes on boot.
            # this is an alternative to get patreons instantly and later modifying the cache after the cache loads.
            # remove any patrons from db set cache that should not exist or should be modified.
            cached_patrons = await self.ex.sql.s_patreon.fetch_cached_patrons()
            cached_patron_ids = []

            for user_id, super_patron in cached_patrons:
                await asyncio.sleep(0)  # bare yield
                cached_patron_ids.append(user_id)
                if user_id not in normal_patrons:
                    # they are not a patron at all, so remove them from db cache
                    await self.ex.sql.s_patreon.delete_patron(user_id)
                elif user_id in super_patrons and not super_patron:
                    # if they are a super patron but their db is cache is a normal patron
                    await self.ex.sql.s_patreon.update_patron(user_id, 1)
                elif user_id not in super_patrons and super_patron:
                    # if they are not a super patron, but the db cache says they are.
                    await self.ex.sql.s_patreon.update_patron(user_id, 0)
            # fix db cache and live Irene cache
            for patron in normal_patrons:
                if patron not in cached_patron_ids:
                    # patron includes both normal and super patrons.
                    await self.ex.sql.s_patreon.add_patron(patron, 0)
                user = await self.ex.get_user(patron)
                user.patron = True

            for patron in super_patrons:
                if patron not in cached_patron_ids:
                    await self.ex.sql.s_patreon.update_patron(patron, 1)
                user = await self.ex.get_user(patron)
                user.patron = True
                user.super_patron = True

            for patron in permanent_patrons:
                user = await self.ex.get_user(patron[0])
                user.patron = True
                user.super_patron = True
            return True
        except Exception as e:
            log.console(f"{e} - create_patreons")
            return False

    async def create_user_notifications(self):
        """Set the cache for user phrases"""
        self.ex.cache.user_notifications = []
        notifications = await self.ex.conn.fetch("SELECT guildid,userid,phrase FROM general.notifications")
        for guild_id, user_id, phrase in notifications:
            user = await self.ex.get_user(user_id)
            user.notifications.append([guild_id, phrase])
            self.ex.cache.user_notifications.append([guild_id, user_id, phrase])  # full list.

    async def create_groups(self):
        """Set cache for group photo count"""
        self.ex.cache.group_photos = {}
        all_group_counts = await self.ex.conn.fetch(
            "SELECT g.groupid, g.groupname, COUNT(f.link) FROM groupmembers.groups g, groupmembers.member m, groupmembers.idoltogroup l, groupmembers.imagelinks f WHERE m.id = l.idolid AND g.groupid = l.groupid AND f.memberid = m.id GROUP BY g.groupid ORDER BY g.groupname")
        for group in all_group_counts:
            self.ex.cache.group_photos[group[0]] = group[2]

    async def create_guild_cache(self):
        """Update the DB Guild Cache. Useful for updating info for API."""
        # much simpler to just delete all of the cache and reinsert instead of updating fields.
        try:
            log.console("Attempting to send guild information to DB.")
            await self.ex.conn.execute("DELETE FROM stats.guilds")

            guild_data = []
            for guild in self.ex.client.guilds:
                await asyncio.sleep(0)
                guild_data.append(
                    (guild.id, guild.name, len(guild.emojis), f"{guild.region}", guild.afk_timeout, guild.icon,
                     guild.owner_id,
                     guild.banner, guild.description, guild.mfa_level, guild.splash,
                     guild.premium_tier, guild.premium_subscription_count, len(guild.text_channels),
                     len(guild.voice_channels), len(guild.categories), guild.emoji_limit, guild.member_count,
                     len(guild.roles), guild.shard_id, guild.created_at)
                )

            async with self.ex.conn.acquire() as direct_conn:
                await direct_conn.copy_records_to_table('guilds', records=guild_data, schema_name="stats")
        except Exception as e:
            log.console(f"{e} - Failed to update guild cache")

    async def create_idols(self):
        """Set cache for idol photo count"""
        self.ex.cache.idol_photos = {}
        all_idol_counts = await self.ex.conn.fetch(
            "SELECT memberid, COUNT(link) FROM groupmembers.imagelinks GROUP BY memberid")
        for idol_id, count in all_idol_counts:
            self.ex.cache.idol_photos[idol_id] = count

    @tasks.loop(seconds=0, minutes=0, hours=12, reconnect=True)
    async def update_cache(self):
        """Looped every 12 hours to update the cache in case of anything faulty."""
        while not self.ex.conn:
            await asyncio.sleep(1)
        await self.create_cache(on_boot_up=not self.ex.irene_cache_loaded)

    @tasks.loop(seconds=0, minutes=0, hours=0, reconnect=True)
    async def update_patron_and_guild_cache(self):
        """Looped until patron cache is loaded.
        This was added due to intents slowing d.py cache loading rate.
        """
        # create a temporary patron list based on the db cache while waiting for the discord cache to load
        try:
            if self.ex.conn:
                if not self.ex.temp_patrons_loaded:
                    while not self.ex.irene_cache_loaded:
                        # wait until Irene's cache has been loaded before creating temporary patrons
                        # this is so that the user objects do not overwrite each other
                        # when being created.
                        await asyncio.sleep(5)
                    cached_patrons = await self.ex.conn.fetch("SELECT userid, super FROM patreon.cache")
                    for user_id, super_patron in cached_patrons:
                        user = await self.ex.get_user(user_id)
                        if super_patron:
                            log.console(f"Made {user_id} a temporary super patron & patron.")
                            user.super_patron = True
                        else:
                            log.console(f"Made {user_id} a temporary patron.")
                        user.patron = True
                    self.ex.temp_patrons_loaded = True
                    log.console("Cache for Temporary Patrons has been created.")
                while not self.ex.discord_cache_loaded:
                    await asyncio.sleep(60)  # check every minute if discord cache has loaded.

                # update patron cache
                if await self.process_cache_time(self.create_patreons, "Patrons"):
                    self.update_patron_cache_hour.start()
                    self.update_patron_and_guild_cache.stop()
        except Exception as e:
            log.console(e)

    @tasks.loop(seconds=0, minutes=0, hours=1, reconnect=True)
    async def update_patron_cache_hour(self):
        """Update Patron Cache every hour in the case of unaccounted errors."""
        # this is to make sure on the first run it doesn't update since it is created elsewhere.
        if self.ex.loop_count:
            await self.process_cache_time(self.create_patreons, "Patrons")
        self.ex.loop_count += 1

    @tasks.loop(seconds=0, minutes=1, hours=0, reconnect=True)
    async def send_cache_data_to_data_dog(self):
        """Sends metric information about cache to data dog every minute."""
        try:
            if self.ex.thread_pool:
                user_notifications = 0
                patron_count = 0
                mod_mail = 0
                bot_banned = 0
                active_user_reminders = 0
                for user in self.ex.cache.users.values():
                    user_notifications += len(user.notifications)
                    if user.patron:
                        patron_count += 1
                    if user.mod_mail_channel_id:
                        mod_mail += 1
                    if user.bot_banned:
                        bot_banned += 1
                    active_user_reminders += len(user.reminders)

                playing_card_amount = 0
                for list_of_playing_card in self.ex.cache.playing_cards.values():
                    playing_card_amount += len(list_of_playing_card)

                user_copy = self.ex.cache.users.copy()
                gg_filtered_enabled = len([user for user in user_copy.values() if user.gg_filter])

                metric_info = {
                    'total_commands_used': self.ex.cache.total_used,
                    'bias_games': len(self.ex.cache.bias_games),
                    'guessing_games': len(self.ex.cache.guessing_games),
                    'patrons': patron_count,
                    'custom_server_prefixes': len(self.ex.cache.server_prefixes),
                    'session_commands_used': self.ex.cache.current_session,
                    'user_notifications': user_notifications,
                    'mod_mail': mod_mail,
                    'banned_from_bot': bot_banned,
                    'logged_servers': len(self.ex.cache.logged_channels),
                    # server count is based on discord.py guild cache which takes a large amount of time to load fully.
                    # There may be inaccurate data points on a new instance of the bot due to the amount of
                    # time that it takes.
                    'server_count': len(self.ex.client.guilds),
                    'welcome_messages': len(self.ex.cache.welcome_messages),
                    'temp_channels': len(self.ex.cache.temp_channels),
                    'amount_of_idols': len(self.ex.cache.idols),
                    'amount_of_groups': len(self.ex.cache.groups),
                    'channels_restricted': len(self.ex.cache.restricted_channels),
                    'amount_of_bot_statuses': len(self.ex.cache.bot_statuses),
                    'commands_per_minute': self.ex.cache.commands_per_minute,
                    'amount_of_custom_commands': len(self.ex.cache.custom_commands),
                    'discord_ping': self.ex.get_ping(),
                    'n_words_per_minute': self.ex.cache.n_words_per_minute,
                    'bot_api_idol_calls': self.ex.cache.bot_api_idol_calls,
                    'bot_api_translation_calls': self.ex.cache.bot_api_translation_calls,
                    'messages_received_per_min': self.ex.cache.messages_received_per_minute,
                    'errors_per_minute': self.ex.cache.errors_per_minute,
                    'wolfram_per_minute': self.ex.cache.wolfram_per_minute,
                    'urban_per_minute': self.ex.cache.urban_per_minute,
                    'active_user_reminders': active_user_reminders,
                    'weverse_channels_following': sum([len(channels) for channels in self.ex.cache.weverse_channels.
                                                      values()]),
                    'weverse_following_txt': len(self.ex.cache.weverse_channels.get("txt") or []),
                    'weverse_following_bts': len(self.ex.cache.weverse_channels.get("bts") or []),
                    'weverse_following_gfriend': len(self.ex.cache.weverse_channels.get("gfriend") or []),
                    'weverse_following_seventeen': len(self.ex.cache.weverse_channels.get("seventeen") or []),
                    'weverse_following_enhypen': len(self.ex.cache.weverse_channels.get("enhypen") or []),
                    'weverse_following_nuest': len(self.ex.cache.weverse_channels.get("nu'est") or []),
                    'weverse_following_cl': len(self.ex.cache.weverse_channels.get("cl") or []),
                    'weverse_following_p1harmony': len(self.ex.cache.weverse_channels.get("p1harmony") or []),
                    'weverse_following_weeekly': len(self.ex.cache.weverse_channels.get("weeekly") or []),
                    'weverse_following_sunmi': len(self.ex.cache.weverse_channels.get("sunmi") or []),
                    'weverse_following_henry': len(self.ex.cache.weverse_channels.get("henry") or []),
                    'weverse_following_dreamcatcher': len(self.ex.cache.weverse_channels.get("dreamcatcher") or []),
                    'twitch_channels_followed': len(self.ex.cache.twitch_channels.keys() or []),
                    'text_channels_following_twitch': sum([len(channels) for channels in self.ex.cache.twitch_channels.
                                                          values()]),
                    'voice_clients': len(self.ex.client.voice_clients or []),
                    'servers_using_self_assignable_roles': len(self.ex.cache.assignable_roles.keys() or []),
                    'total_amount_of_self_assignable_roles': sum([len(channel_and_roles.get('roles') or [])
                                                                  for channel_and_roles in
                                                                  self.ex.cache.assignable_roles.values()]),
                    'channels_with_games_disabled': len(self.ex.cache.channels_with_disabled_games),
                    'dead_image_cache': len(self.ex.cache.dead_image_cache),
                    'user_objects': len(self.ex.cache.users),
                    'welcome_roles': len(self.ex.cache.welcome_roles),
                    'playing_cards': playing_card_amount,
                    'members_in_support_server': len(self.ex.cache.member_ids_in_support_server),
                    'gg_filter_enabled': gg_filtered_enabled
                }

                # set all per minute metrics to 0 since this is a 60 second loop.
                self.ex.cache.n_words_per_minute = 0
                self.ex.cache.commands_per_minute = 0
                self.ex.cache.bot_api_idol_calls = 0
                self.ex.cache.bot_api_translation_calls = 0
                self.ex.cache.messages_received_per_minute = 0
                self.ex.cache.errors_per_minute = 0
                self.ex.cache.wolfram_per_minute = 0
                self.ex.cache.urban_per_minute = 0
                for metric_name in metric_info:
                    try:
                        metric_value = metric_info.get(metric_name)
                        # add to thread pool to prevent blocking.
                        # noinspection PyUnusedLocal
                        result = (self.ex.thread_pool.submit(self.ex.u_data_dog.send_metric, metric_name, metric_value)).result()
                    except Exception as e:
                        log.console(e)
        except Exception as e:
            # loop appears to stop working after a while and no errors were recognized in log file
            # adding this try except to see if issue continues.
            log.console(e)
