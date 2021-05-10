class Game:
    def __init__(self, utility_obj, ctx):
        """

        :param utility_obj: Utility object.
        :param ctx: Context
        :param max_rounds: The amount of rounds to stop at.
        :param timeout: Amount of time to guess a phoot.
        :param gender: Male/Female/All Gender of the idols in the photos.
        :param difficulty: Easy/Medium/Hard difficulty of the game.
        """
        self.ex = utility_obj
        self.host_ctx = ctx
        self.host_id = ctx.author.id
        self.host_user = None  # Utility user object
        self.channel = ctx.channel
        self.force_ended = False

    async def end_game(self):
        """Ends a guessing game."""

    async def process_game(self):
        """Starts processing the game."""
