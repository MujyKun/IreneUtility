from .. import Utility

import discord.ext.commands


class Game:
    def __init__(self, utility_obj, ctx):
        """

        :param utility_obj: Utility object.
        :param ctx: Context
        """
        self.ex: Utility.Utility = utility_obj
        self.host_ctx: discord.ext.commands.Context = ctx
        self.host_id: int = ctx.author.id
        self.host_user = None  # Utility user object
        self.channel = ctx.channel
        self.force_ended = False

    async def end_game(self):
        """Ends a guessing game."""

    async def process_game(self):
        """Starts processing the game."""
