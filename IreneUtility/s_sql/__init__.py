class SqlConnection:
    """Used so that we have a stable reference to our DB Connection. This way we do not need to worry if our
    connection at any starting point is None as long as it gets set eventually"""
    def __init__(self):
        self.conn = None


self = SqlConnection()

from . import db_structure, s_biasgame, s_blackjack, s_cache, s_currency, s_customcommands, \
    s_database, s_gacha, s_general, s_groupmembers, s_guessinggame, s_lastfm, \
    s_levels, s_logging, s_miscellaneous, s_moderator, s_patreon, s_reminder, \
    s_selfassignroles, s_session, s_twitch, s_twitter, s_user, s_weverse, s_unscramblegame
