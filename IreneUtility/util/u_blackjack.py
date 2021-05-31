import asyncio
from PIL import Image
from ..Base import Base
from ..models import BlackJackGame
from . import u_logger as log
from discord.ext import commands
from os import unlink, listdir


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
            user = await self.ex.get_user(user.author.id)
        elif isinstance(user, int):
            # transform into Utility Object
            user = await self.ex.get_user(user)

        for blackjack_game in self.ex.cache.blackjack_games:
            if user in [blackjack_game.first_player, blackjack_game.second_player]:
                return blackjack_game

    async def generate_playing_cards(self):
        """Generate custom playing cards with the background as an idol avatar."""
        # delete all cards to not have duplicates and to properly regenerate avatar changes.
        await self.ex.sql.s_blackjack.delete_playing_cards()
        try:
            # remove all player cards existing on OS.
            (self.ex.thread_pool.submit(self.remove_all_card_files)).result()
        except Exception as e:
            log.console(e)

        for idol in self.ex.cache.idols:
            try:
                for i in range(52):
                    await asyncio.sleep(0)
                    unique_id = await self.ex.sql.s_blackjack.generate_playing_card(i+1, idol.id)

                    (self.ex.thread_pool.submit(self.merge_images, f"{i+1}.png", f"{idol.id}_IDOL.png", unique_id
                                                )).result()
            except Exception as e:
                log.console(e)

        await self.ex.u_cache.create_playing_cards()  # reset playing card cache.
        await self.ex.u_cache.process_cache_time(self.ex.u_cache.create_playing_cards, "Playing Cards")

    def remove_all_card_files(self):
        """Remove all card files from OS."""
        for file in listdir(self.ex.keys.playing_card_location):
            unlink(file)

    def merge_images(self, card_file_name, idol_file_name, unique_id):
        """
        Merges a template card with an idol avatar.

        :param card_file_name: A Card's File name & type without the directory.
        :param idol_file_name: An Idol's File name & type without the directory.
        :param unique_id: The unique row id in the database table that will be the merged file name.
        """
        # Open Files
        with Image.open(f"Cards/{card_file_name}") as card_file, \
                Image.open(f"{self.ex.keys.idol_avatar_location}{idol_file_name}") as idol_file:
            # Convert images to RGBA
            card_file = card_file.convert("RGBA")
            idol_file = idol_file.convert("RGBA")

            # Resize Idol Photo
            idol_file = idol_file.resize((card_file.width, card_file.height))

            # Paste the Card File at (width, height)
            idol_file.paste(card_file, None, card_file)

            # Save this image
            idol_file.save(f"{self.ex.keys.playing_card_location}{unique_id}.png")
