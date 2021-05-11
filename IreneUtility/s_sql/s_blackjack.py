from IreneUtility.s_sql import self


async def fetch_playing_cards():
    """
    Fetch playing cards.


    """
    return await self.conn.fetch("SELECT c.id, c.filename, v.id, v.name, v.value, c.bgidolid FROM blackjack.playingcards c, "
                                 "blackjack.cardvalues v WHERE c.cardvalueid = v.id")
