from . import u_logger as log
import random
import discord
from IreneUtility.Base import Base
from IreneUtility.models import BlackJackGame
from discord.ext import commands


# noinspection PyPep8
class BlackJack(Base):
    def __init__(self, *args):
        super().__init__(*args)

    async def find_game(self, user) -> BlackJackGame:
        """
        Find a blackjack game that a user is in.

        :param user: A Utility User object, Context, or User ID
        :return: BlackJack Game
        """
        if isinstance(user, commands.Context):
            user = await self.ex.get_user(user.id)
        elif isinstance(user, int):
            # transform into Utility Object
            user = await self.ex.get_user(user)

        for blackjack_game in self.ex.cache.blackjack_games:
            if user in [blackjack_game.first_player, blackjack_game.second_player]:
                return blackjack_game
