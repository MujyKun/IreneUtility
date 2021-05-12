import random

import discord.ext.commands

from . import Game as Game_Base, User, PlayingCard
from IreneUtility.util import u_logger as log
from typing import List
import asyncio


class BlackJackGame(Game_Base):
    """BlackJack Game for two users."""
    def __init__(self, *args, first_player, first_player_bet):
        """

        :param args: utility_obj, ctx
        :param first_player_bet: Amount the first player bet.
        """
        super().__init__(*args)
        self.first_player: User = first_player
        self.second_player: User = None

        self.first_player.in_currency_game = True  # set first person to be in a game.

        # cards the users have
        self.first_player_cards: List[PlayingCard] = []
        self.second_player_cards: List[PlayingCard] = []

        # whether the players are done.
        self.first_player_stand = False
        self.second_player_stand = False

        # we need the display name of second player, so we will hold their Context.
        self.second_player_ctx: discord.ext.commands.Context = None

        # player bets
        self.first_player_bet: int = first_player_bet
        self.second_player_bet: int = 0

        self.deck = [i+1 for i in range(52)]  # a deck containing the ids of each non-custom playing card.

    async def check_message(self):
        """Check incoming messages in the text channel and determines if the player wants to hit or stand."""
        if self.force_ended:
            return

        stop_phrases = ['stop', 'end', 'quit']
        hit_phrases = ['hit', 'new']
        stand_phrases = ['stand', 'stay']

        def check_player_response(message):
            """Checks if it is a player's response and filters."""
            if message.channel != self.channel:
                return False
            elif message.content.lower() in stop_phrases:
                return True
            elif message.content.lower() in hit_phrases or message.content.lower() in stand_phrases:
                return True
            else:
                return False

        try:
            msg = await self.ex.client.wait_for('message', check=check_player_response, timeout=60)
            await msg.add_reaction(self.ex.keys.check_emoji)
            if msg.content.lower() in stop_phrases:
                await self.end_game()
                return
            elif msg.content.lower() in hit_phrases:
                # let the player hit
                return await self.hit(msg.author.id == self.first_player.id)
            elif msg.content.lower() in stand_phrases:
                # let the player stand
                return await self.stand(msg.author.id == self.first_player.id)
            else:
                raise self.ex.exceptions.ShouldNotBeHere("A condition was not properly checked. "
                                                         "-> BlackJackGame.check_message()")
        except asyncio.TimeoutError:
            if not self.force_ended:
                await self.end_game()

    async def end_game(self):
        """End the blackjack game."""
        self.first_player_stand = True
        self.second_player_stand = True
        self.first_player.in_currency_game = False
        self.second_player.in_currency_game = False
        if self.force_ended:
            await self.channel.send(await self.ex.get_msg(self.host_id, 'biasgame', 'force_closed'))
        self.force_ended = True
        try:
            self.ex.cache.blackjack_games.remove(self)
        except Exception as e:
            log.useless(f"{BlackJackGame.end_game()} could not find the game to remove from cache.")
        return True

    async def hit(self, first_player=True):
        """
        Let a player hit

        :param first_player: True if it is the first player that wants to hit. Otherwise its the second player.
        """
        if await self.check_standing(first_player):
            return await self.stand(first_player)  # msg that the user is already standing will be sent.

        random_card = await self.choose_random_card()
        self.first_player_cards.append(random_card) if first_player else self.second_player_cards.append(random_card)

        user_score = await self.calculate_score(self.first_player_cards if first_player else self.second_player_cards)
        user_id = self.first_player.id if first_player else self.second_player.id
        msg = await self.ex.get_msg(self.host_ctx, "blackjack", "hit", [
            ["mention", f"<@{user_id}>"],
            ["string", random_card.card_name],
            ["integer", f"0{user_score}" if len(str(user_score)) == 1 else user_score]])
        await random_card.send_file(self.channel, message=msg, url=False)
        if user_score >= 35:
            await self.stand(first_player)

    async def stand(self, first_player=True):
        """
        Let a player stand

        :param first_player: True if it is the first player that wants to stand. Otherwise its the second player.
        """
        if first_player:
            name = self.host_ctx.author.display_name
            if self.first_player_stand:
                # player was already standing
                return await self.channel.send(await self.ex.get_msg(self.host_ctx, "blackjack", "already_standing",
                                                                     ["name", name]))
            self.first_player_stand = True
        else:
            name = self.second_player_ctx.author.display_name
            if self.second_player_stand:
                # player was already standing
                return await self.channel.send(await self.ex.get_msg(self.host_ctx, "blackjack", "already_standing",
                                                                     ["name", name]))
            self.second_player_stand = True
        return await self.channel.send(await self.ex.get_msg(self.host_ctx, "blackjack", "now_standing",
                                                             ["name", name]))

    async def check_standing(self, first_player=True):
        """
        Check if a player is standing.

        :param first_player: True if it is the first player that wants to stand. Otherwise its the second player.
        :return: True if the user is standing.
        """
        return self.first_player_stand if first_player else self.second_player_stand


    async def choose_random_card(self) -> PlayingCard:
        """Chooses a random card that is available in the deck."""
        random_card_id = random.choice(self.deck)

        # choose a custom playing card from the card id
        random_card = random.choice(self.ex.cache.playing_cards[random_card_id])

        # remove card if from deck so it is never accessed again
        self.deck.remove(random_card_id)
        return random_card

    async def calculate_score(self, cards: List[PlayingCard]) -> int:
        """Calculate the score of a player.

        :param cards: List of PlayingCards the user has in their deck.
        :return: Score of the player
        """
        total_card_value = 0
        aces = 0
        for card in cards:
            await asyncio.sleep(0)  # bare yield
            total_card_value += card.value
            if card.value == 11:
                aces += 1

        # handle aces by reducing the value from 11 to 1 if the total value is over 21
        while aces > 0 and total_card_value > 21:
            total_card_value -= 10
            aces -= 1

        return total_card_value

    async def determine_winner(self) -> User:
        """Determine the winner of the blackjack game."""
        first_player_score = await self.calculate_score(self.first_player_cards)
        second_player_score = await self.calculate_score(self.second_player_cards)
        if first_player_score == second_player_score:
            # tie
            return None
        elif first_player_score > 21 and second_player_score > 21:
            # both busted
            winner = self.first_player if (first_player_score - 21) < (second_player_score - 21) \
                else self.second_player
        elif first_player_score <= 21 and second_player_score <= 21:
            # neither busted
            winner = self.first_player if (21 - first_player_score) < (21 - second_player_score) \
                else self.second_player
        elif first_player_score > 21 and second_player_score <= 21:
            # player 1 busted
            winner = second_player_score
        elif second_player_score > 21 and first_player_score <= 21:
            # player 2 busted
            winner = first_player_score
        else:
            raise self.ex.exceptions.ShouldNotBeHere("A condition was not properly checked for in "
                                                     "BlackJackGame.determine_winner().")
        return winner

    async def deal_with_bets(self):
        """Properly deal with bets and appropriately remove/add the bets from the players balances."""
        winner = await self.determine_winner()
        if not winner:
            return

        if winner == self.first_player:
            await self.first_player.update_balance(add=self.second_player_bet)
            await self.second_player.update_balance(remove=self.second_player_bet)
        else:
            await self.first_player.update_balance(remove=self.first_player_bet)
            await self.second_player.update_balance(add=self.first_player_bet)

    async def announce_winner(self):
        """Announce the winner of the game."""
        winner = await self.determine_winner()
        first_player_score = await self.calculate_score(self.first_player_cards)
        second_player_score = await self.calculate_score(self.second_player_cards)
        if not winner:
            # tie
            return await self.channel.send(await self.ex.get_msg(self.host_ctx, "blackjack", "announce_tie", [
                ["name", self.host_ctx.author.display_name], ["name2", self.second_player_ctx.author.display_name],
                ["integer", first_player_score]]))
        if winner == self.first_player:
            # first player won
            return await self.channel.send(await self.ex.get_msg(self.host_ctx, "blackjack", "announce_winner", [
                ["name", self.host_ctx.author.display_name], ["name2", self.second_player_ctx.author.display_name],
                ["integer", first_player_score], ["integer2", second_player_score]]))
        else:
            # second player won
            return await self.channel.send(await self.ex.get_msg(self.host_ctx, "blackjack", "announce_winner", [
                ["name", self.second_player_ctx.author.display_name],
                ["name2", self.host_ctx.author.display_name],
                ["integer", second_player_score],
                ["integer2", first_player_score]]))

    async def finalize_game(self):
        """Finalize the game by dealing with bets, announcing the winner, and officially ending the game."""
        await self.announce_winner()
        await self.deal_with_bets()
        await self.end_game()


    async def process_game(self):
        """Start the blackjack game."""
        try:
            self.second_player.in_currency_game = True

            for i in range(2):
                await asyncio.sleep(0)  # bare yield
                await self.hit(True)
                await self.hit(False)

            while not self.first_player_stand or not self.second_player_stand:
                await asyncio.sleep(0)
                await self.check_message()
            # We can now properly end the game because both players have stood.
            if not self.force_ended:
                await self.finalize_game()

        except Exception as e:
            await self.channel.send(await self.ex.get_msg(self.host_id, 'biasgame', 'unexpected_error'))
            log.console(e)
