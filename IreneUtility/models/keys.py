from discord.ext import commands
from dbl import DBLClient
from discordboats import client as discord_boats_client
from aiohttp import ClientSession as AioHTTPClient
from ksoftapi import Client as lyrics_client
import asyncpg


class Keys:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

        """Bot Tokens"""
        self.client_token: str = self.get_kwarg("client_token")
        self.test_client_token: str = self.get_kwarg("test_client_token")

        """General"""
        self.startup_time = self.get_kwarg("startup_time")  # bot startup time
        self.bot_name: str = self.get_kwarg("bot_name")  # bot name
        self.bot_id: int = self.get_kwarg("bot_id")  # bot id
        self.owner_id: int = self.get_kwarg("owner_id")  # bot owner id
        self.mods_list: list = self.get_kwarg("mods_list")  # list of mod ids
        self.bot_invite_link: str = self.get_kwarg("bot_invite_link")  # bot invite
        self.bot_support_server_id: int = self.get_kwarg("bot_support_server_id")  # bot support server id
        self.bot_support_server_link: str = self.get_kwarg("bot_support_server_link")  # bot support server invite
        self.bot_prefix: str = self.get_kwarg("bot_prefix")  # main bot prefix
        self.image_host: str = self.get_kwarg("image_host")  # link to image host (with slash at end)
        # channel id to test DCAPP posts #TODO: Remove since dc app was deleted.
        self.dc_app_test_channel_id: int = self.get_kwarg("dc_app_test_channel_id")
        self.report_channel_id: int = self.get_kwarg("report_channel_id")  # channel id for user bug reports.
        self.suggest_channel_id: int = self.get_kwarg("suggest_channel_id")  # channel id for user suggestions.
        self.dead_image_channel_id: int = self.get_kwarg("dead_image_channel_id")  # channel id for reported images.
        # channel id for unregistered idols ( user filled out forms ).
        self.add_idol_channel_id: int = self.get_kwarg("add_idol_channel_id")
        # channel id for unregistered groups ( user filled out forms ).
        self.add_group_channel_id: int = self.get_kwarg("add_group_channel_id")
        # channel id for new twitter posts (automatically posted every after t time).
        self.twitter_channel_id: int = self.get_kwarg("twitter_channel_id")
        # amount of idol photos a user can send daily with voting.
        self.idol_post_send_limit: int = self.get_kwarg("idol_post_send_limit")
        # amount of idol photos a user can request with a server owner as a super patron.
        self.owner_super_patron_benefit: int = self.get_kwarg("owner_super_patron_benefit")
        # amount of idol photos a user can request daily without voting.
        self.idol_no_vote_send_limit: int = self.get_kwarg("idol_no_vote_send_limit")
        self.reminder_limit: int = self.get_kwarg("reminder_limit")  # maximum amount of reminders
        # maximum amount of automatic idol photos a non-patron can be sent
        self.idol_send_limit: int = self.get_kwarg("idol_send_limit")
        self.currency_name: str = self.get_kwarg("currency_name")  # name of main currency
        self.icon_url: str = self.get_kwarg("icon_url")  # embed icon url
        self.footer_url: str = self.get_kwarg("footer_url")  # embed footer url
        self.n_word_list: list = self.get_kwarg("n_word_list")  # triggers for n-word
        self.client: commands.AutoShardedBot = self.get_kwarg("client")  # discord.py client

        """Reactions/Emojis Turned into Unicode Strings"""
        self.trash_emoji = self.get_kwarg("trash_emoji")  # trash emoji
        self.check_emoji = self.get_kwarg("check_emoji")  # check mark emoji
        self.reload_emoji = self.get_kwarg("reload_emoji")  # F reload emoji
        self.dead_emoji = self.get_kwarg("dead_emoji")  # dead (caution) emoji
        self.previous_emoji = self.get_kwarg("previous_emoji")  # left arrow
        self.next_emoji = self.get_kwarg("next_emoji")  # right arrow

        """Twitter"""
        self.twitter_account_id: str = self.get_kwarg("twitter_account_id")  # twitter account id
        self.twitter_username: str = self.get_kwarg("twitter_username")  # twitter username
        self.CONSUMER_KEY: str = self.get_kwarg("CONSUMER_KEY")  # twitter API consumer key
        self.CONSUMER_SECRET: str = self.get_kwarg("CONSUMER_SECRET")  # twitter API consumer secret
        self.ACCESS_KEY: str = self.get_kwarg("ACCESS_KEY")  # twitter API access key
        self.ACCESS_SECRET: str = self.get_kwarg("ACCESS_SECRET")  # twitter API access secret

        """Spotify"""
        self.spotify_client_id: str = self.get_kwarg("spotify_client_id")  # spotify client id
        self.spotify_client_secret: str = self.get_kwarg("spotify_client_secret")  # spotify client secret

        """Oxford"""
        self.oxford_app_id: str = self.get_kwarg("oxford_app_id")  # oxford app id
        self.oxford_app_key: str = self.get_kwarg("oxford_app_key")  # oxford app key

        """Urban Dictionary"""
        self.X_RapidAPI_headers: dict = self.get_kwarg("X_RapidAPI_headers")  # urban dictionary headers

        """Tenor"""
        self.tenor_key: str = self.get_kwarg("tenor_key")  # tenor api key

        """Top.gg"""
        self.top_gg_key: str = self.get_kwarg("top_gg_key")  # top gg key
        self.top_gg: DBLClient = self.get_kwarg("top_gg")  # top gg client (should only exist in production)

        """Discord Boats"""
        self.discord_boats_key: str = self.get_kwarg("discord_boats_key")  # discord boats key
        self.discord_boats: discord_boats_client = self.get_kwarg("discord_boats")  # discord boats client

        """Database Connection"""
        self.postgres_options: dict = self.get_kwarg("postgres_options")  # host, database, user, and password for DB.
        self.db_conn: asyncpg.pool.Pool = self.get_kwarg("db_conn")  # connection to db

        """Papago/Translator"""
        self.papago_client_id: str = self.get_kwarg("papago_client_id")  # papago client id
        self.papago_client_secret: str = self.get_kwarg("papago_client_secret")  # papago client secret
        self.translator = self.get_kwarg("translator")  # Translator
        self.translate_private_key = self.get_kwarg("translate_private_key")  # private key for translation

        """LastFM"""
        self.last_fm_api_key: str = self.get_kwarg("last_fm_api_key")  # last fm api key
        self.last_fm_shared_secret: str = self.get_kwarg("last_fm_shared_secret")  # last fm shared secret
        self.last_fm_root_url: str = self.get_kwarg("last_fm_root_url")  # last fm root url (ends with slash)
        self.last_fm_headers: dict = self.get_kwarg("last_fm_headers")  # headers for last fm request (user-agent)

        """Patreon"""
        self.patreon_link: str = self.get_kwarg("patreon_link")  # bot patreon link
        self.patreon_role_id: int = self.get_kwarg("patreon_role_id")  # patreon role id
        self.patreon_super_role_id: int = self.get_kwarg("patreon_super_role_id")  # patreon super role id

        """AioHTTP"""
        self.client_session: AioHTTPClient = self.get_kwarg("client_session")  # aiohttp client session

        """Wolfram"""
        self.wolfram_app_id: str = self.get_kwarg("wolfram_app_id")  # wolfram application id

        """Lyrics API - https://github.com/KSoft-Si/ksoftapi.py"""
        self.lyrics_api_key: str = self.get_kwarg("lyrics_api_key")  # lyrics api key
        self.lyric_client: lyrics_client = self.get_kwarg("lyric_client")  # lyrics client

        """Weverse - https://github.com/MujyKun/Weverse"""
        self.weverse_auth_token: str = self.get_kwarg("weverse_auth_token")  # Weverse account auth token
        self.weverse_image_folder: str = self.get_kwarg("weverse_image_folder")  # Weverse Image Directory (slash at end)

        """GroupMembers Directories"""
        self.idol_avatar_location: str = self.get_kwarg("idol_avatar_location")  # Idol Avatar Location (slash at end)
        self.idol_banner_location: str = self.get_kwarg("idol_banner_location")  # Idol Banner Location (slash at end)
        self.bias_game_location: str = self.get_kwarg("bias_game_location")  # Bias Game Location (slash at end)
        self.idol_photo_location: str = self.get_kwarg("idol_photo_location")  # Idol Photo Location (slash at end)

        """Twitch API"""
        self.twitch_client_id: str = self.get_kwarg("twitch_client_id")  # Twitch client id
        self.twitch_client_secret: str = self.get_kwarg("twitch_client_secret")  # Twitch client secret

        """DataDog - https://github.com/DataDog/datadogpy"""
        self.datadog_api_key: str = self.get_kwarg("datadog_api_key")  # datadog api key
        self.datadog_app_key: str = self.get_kwarg("datadog_app_key")  # datadog app key

        """BlackJack"""
        self.playing_card_location: str = self.get_kwarg("playing_card_location")

        """Bot API"""
        self.api_port: str = self.get_kwarg("api_port")  # port of Bot API

        """Bot Site"""
        self.site_port: str = self.get_kwarg("site_port")  # port of Bot Site
        self.bot_website: str = self.get_kwarg("bot_website")  # link to bot website (with slash at end)

        """Vlive"""
        self.vlive_base_url: str = self.get_kwarg("vlive_base_url")
        self.vlive_app_id: str = self.get_kwarg("vlive_app_id")

    def get_kwarg(self, kwarg_name):
        """Get a kwarg"""
        return self.kwargs.get(kwarg_name)

    async def connect_to_db(self):
        """Create a pool to the postgres database using asyncpg"""
        # pool is not being used as recommended, however, since we do not deal with millions of requests a second,
        # the current usage is fine. connections from the pool are also not released after completion and we let asyncpg
        # release the inactive connection once it recognizes it is inactive.
        # instead of acquiring a connection from the pool, we just let the pool select a connection for us and
        # execute directly that way. this limits the amount of methods we have access to,
        # but in the case those methods are needed, just acquire the connection and use that instead.
        self.db_conn: asyncpg.pool.Pool = await asyncpg.create_pool(**self.postgres_options, command_timeout=60)
        return self.db_conn
