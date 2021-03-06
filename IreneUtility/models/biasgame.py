from . import Game as Game_Base
import random
import asyncio
from math import log2
from ..util import u_logger as log
import discord


# noinspection PyBroadException,PyPep8
class BiasGame(Game_Base):
    def __init__(self, *args, bracket_size=8, gender="all"):
        super().__init__(*args)
        self.force_ended = False
        self.current_bracket_teams = []
        # secondary is the next teams up the bracket and is a temporary holder to be moved into current bracket teams.
        self.secondary_bracket_teams = []
        # contains all brackets to backtrace when generating bracket image.
        self.all_brackets_together = []
        self.original_idols_in_game = []
        self.bracket_winner = None
        self.number_of_idols_left = 2 * bracket_size

        if bracket_size > 32:
            bracket_size = 32
        elif bracket_size < 4:
            bracket_size = 4
        self.bracket_size = 2**int(log2(bracket_size))  # rounds down to the closest power of 2

        if gender.lower() in self.ex.cache.male_aliases:
            self.gender = 'male'
        elif gender.lower() in self.ex.cache.female_aliases:
            self.gender = 'female'
        else:
            self.gender = 'all'

    async def check_message(self, message, first_idol, second_idol):
        """Check the reactions of the message and process results"""
        def check_response(user_reaction, reaction_user):
            return user_reaction.emoji in ['➡', '⬅'] and reaction_user != message.author \
                   and user_reaction.message.id == message.id and reaction_user.id == self.host_id

        def add_winner(idol):
            """Add the winner to the next bracket and have them face the previous idol that won."""
            if self.secondary_bracket_teams:
                latest_fight = self.secondary_bracket_teams[-1]
                if len(latest_fight) == 1:
                    latest_fight.append(idol)
                    return
            self.secondary_bracket_teams.append([idol])

        try:
            reaction, _ = await self.ex.client.wait_for('reaction_add', check=check_response, timeout=60)
            if reaction.emoji == '⬅':
                add_winner(first_idol)
            elif reaction.emoji == '➡':
                add_winner(second_idol)
            else:
                raise self.ex.exceptions.ShouldNotBeHere("Bias game reaction was returned from wait_for() "
                                                         "when it is neither ⬅ nor ➡")
            await message.delete()
        except asyncio.TimeoutError:
            await message.delete()
            await self.end_game()

    async def generate_brackets(self):
        """Generates the brackets and the idols going against each other"""
        idol_selection = self.ex.cache.gender_selection.get(self.gender)
        idol_selection = [idol for idol in idol_selection if idol.thumbnail]
        self.original_idols_in_game = random.sample(idol_selection, 2 * self.bracket_size)

        even_idols = self.original_idols_in_game[::2]
        odd_idols = self.original_idols_in_game[1::2]
        self.current_bracket_teams = [list(idol_pair) for idol_pair in zip(even_idols, odd_idols)]

    async def run_current_bracket(self):
        """Generate a new question for the bias game."""
        self.number_of_idols_left = len(self.current_bracket_teams) * 2
        for first_idol, second_idol in self.current_bracket_teams:
            if self.force_ended:
                return
            try:
                first_idol_group = (await self.ex.u_group_members.get_group(random.choice(first_idol.groups))).name
            except Exception as e:
                first_idol_group = first_idol.full_name
                log.useless(f"{e} (Exception)-> Using Idol Full Name instead of Group Name for {first_idol_group}",
                            method=self.run_current_bracket)
            try:
                second_idol_group = (await self.ex.u_group_members.get_group(random.choice(second_idol.groups))).name
            except Exception as e:
                second_idol_group = second_idol.full_name
                log.useless(f"{e} (Exception2) -> Using Idol Full Name instead of Group Name for {second_idol_group}",
                            method=self.run_current_bracket)

            msg_body = f"""
**@{self.host_ctx.author.display_name}**
Remaining Idols: {self.number_of_idols_left}
{first_idol_group} ({first_idol.stage_name}) **VS** {second_idol_group} ({second_idol.stage_name})
                        """
            display_name = f"{first_idol.stage_name} VS {second_idol.stage_name}.png"
            file_location = await self.ex.u_bias_game.create_bias_game_image(first_idol.id, second_idol.id)
            image_file = discord.File(fp=file_location, filename=display_name)
            msg = await self.channel.send(msg_body, file=image_file)
            await msg.add_reaction(self.ex.keys.previous_emoji)  # left arrow by default
            await msg.add_reaction(self.ex.keys.next_emoji)  # right arrow by default
            await self.check_message(msg, first_idol, second_idol)
            self.number_of_idols_left -= 1

        self.all_brackets_together.append(self.current_bracket_teams)
        if len(self.current_bracket_teams) == 1:
            return

        self.current_bracket_teams = self.secondary_bracket_teams
        self.secondary_bracket_teams = []

    async def end_game(self):
        """End the game"""
        if not self.force_ended:
            await self.channel.send(await self.ex.get_msg(self.host_id, 'biasgame', 'force_closed'))
        self.force_ended = True
        return True

    async def print_winner(self):
        msg_body = f"> The winner is {self.bracket_winner.stage_name}."
        file_location = await self.ex.u_bias_game.create_bias_game_bracket(
            self.all_brackets_together, self.host_id, self.bracket_winner)

        image_file = discord.File(fp=file_location, filename=f"{self.host_id}.png")
        await self.channel.send(msg_body, file=image_file)

    async def update_user_wins(self):
        if self.bracket_winner:
            wins = self.ex.first_result(await self.ex.conn.fetchrow(
                "SELECT wins FROM biasgame.winners WHERE userid = $1 AND idolid = $2",
                self.host_id, self.bracket_winner.id))
            if wins:
                await self.ex.conn.execute(
                    "UPDATE biasgame.winners SET wins = $1 WHERE userid = $2 AND idolid = $3",
                    wins + 1, self.host_id, self.bracket_winner.id)
            else:
                await self.ex.conn.execute(
                    "INSERT INTO biasgame.winners(idolid, userid, wins) VALUES ($1, $2, $3)",
                    self.bracket_winner.id, self.host_id, 1)

    async def process_game(self):
        """Process bias guessing game by sending messages and new questions until the game should end."""
        try:
            await self.generate_brackets()
            while self.number_of_idols_left > 1 and not self.force_ended:
                try:
                    await self.run_current_bracket()
                except Exception as e:
                    # this would usually error if the file location set is incorrect.
                    log.console(f"{e} (RuntimeError)", method=self.process_game)
                    raise RuntimeError
            if self.force_ended:
                return
            self.bracket_winner = self.secondary_bracket_teams[0][0]
            await self.print_winner()
            await self.update_user_wins()
        except Exception as e:
            await self.channel.send(await self.ex.get_msg(self.host_id, 'biasgame', 'unexpected_error'))
            log.console(f"{e} (Exception2)", method=self.process_game)
