from IreneUtility.s_sql import self


async def fetch_playing_cards():
    """Fetch playing cards."""
    return await self.conn.fetch("SELECT c.id, c.filename, v.id, v.name, v.value, c.bgidolid FROM blackjack.playingcards c, "
                                 "blackjack.cardvalues v WHERE c.cardvalueid = v.id")


async def generate_playing_card(card_value_id, bg_idol_id) -> int:
    """
    Add a playing card and return the custom id.

    Note that we could technically have a file format name of "(card id)_(idol id).png", but in the case
    we would like to add several images for one idol, it would be better that we go by the unique index of the table,
    even if it does take two more sql queries than needed be.

    :param card_value_id: Number from 1 to 52 that represents the custom card.
    :param bg_idol_id: Idol ID of the background.
    :return: Custom ID of card.
    """
    await self.conn.execute("INSERT INTO blackjack.playingcards(cardvalueid, bgidolid) VALUES ($1 , $2)",
                            card_value_id, bg_idol_id)
    custom_id = (await self.conn.fetchrow("SELECT id FROM blackjack.playingcards WHERE cardvalueid = $1 AND "
                                         "bgidolid = $2 AND filename IS NULL ORDER BY id DESC", card_value_id,
                                         bg_idol_id))[0]
    await self.conn.execute("UPDATE blackjack.playingcards SET filename = $1 WHERE id = $2", f"{custom_id}.png",
                            custom_id)
    return custom_id


async def delete_playing_cards():
    """Delete all custom playing cards from table."""
    await self.conn.execute("DELETE FROM blackjack.playingcards")
