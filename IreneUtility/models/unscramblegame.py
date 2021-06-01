from . import Game as Game_Base
import asyncio
import random
import async_timeout
from ..util import u_logger as log


# noinspection PyBroadException,PyPep8
class UnScrambleGame(Game_Base):
    def __init__(self, *args, max_rounds=20, timeout=20, gender="all", difficulty="medium"):
        """

        :param utility_obj: Utility object.
        :param ctx: Context
        :param max_rounds: The amount of rounds to stop at.
        :param timeout: Amount of time to guess a phoot.
        :param gender: Male/Female/All Gender of the idols in the photos.
        :param difficulty: Easy/Medium/Hard difficulty of the game.
        """
        super().__init__(*args)
        self.host_user = None  # Utility user object
        # user_id : score
        self.players = {}
        self.rounds = 0
        self.idol = None
        self.correct_answer: str = ""
        self.timeout = timeout
        self.max_rounds = max_rounds
        self.force_ended = False
        self.gender = None
        self.post_attempt_timeout = 10
        if gender.lower() in self.ex.cache.male_aliases:
            self.gender = 'male'
        elif gender.lower() in self.ex.cache.female_aliases:
            self.gender = 'female'
        else:
            self.gender = "all"
        if difficulty in self.ex.cache.difficulty_selection.keys():
            self.difficulty = difficulty
        else:
            self.difficulty = "medium"

        self.idol_set: list = []
        self.results_posted = False

    async def credit_user(self, user_id):
        """Increment a user's score"""
        score = self.players.get(user_id)
        if not score:
            self.players[user_id] = 1
        else:
            self.players[user_id] = score + 1
        self.rounds += 1

    async def check_message(self):
        """Check incoming messages in the text channel and determine if it is correct."""
        if self.force_ended:
            return

        def check_correct_answer(message):
            """Check if the user has the correct answer."""
            if message.channel != self.channel:
                return False
            msg_lower = message.content.lower()
            if msg_lower == self.correct_answer.lower():
                return True
            if message.author.id == self.host_id:
                return msg_lower in self.ex.cache.stop_phrases
        try:
            msg = await self.ex.client.wait_for('message', check=check_correct_answer, timeout=self.timeout)
            await msg.add_reaction(self.ex.keys.check_emoji)
            message_lower = msg.content.lower()
            if message_lower == self.correct_answer.lower():
                await self.credit_user(msg.author.id)
            elif message_lower in self.ex.cache.stop_phrases or self.force_ended:
                self.force_ended = True
                return
            else:
                # the only time this code is reached is when a prefix was changed in the middle of a round.
                # for example, if the user had to guess "irene", but their server prefix was 'i', then
                # the bot will change the msg content to "%rene" and the above conditions will not properly work.
                # if we had reached this point, we'll give them +1 instead of ending the game
                await self.credit_user(msg.author.id)

        except asyncio.TimeoutError:
            if not self.force_ended:
                await self.print_answer()
                self.rounds += 1

    async def create_new_question(self):
        """Create a new question and send it to the channel."""
        # noinspection PyBroadException
        if self not in self.ex.cache.unscramble_games.values():
            # This is a double check in case the user tried to force end the game but the game is still going on.
            # just in case, since we do not want the channel to be spammed with posts.
            self.force_ended = True
            self.rounds = self.max_rounds + 1
            return

        question_posted = False
        while not question_posted:
            try:
                # Create random idol selection
                if not self.idol_set:
                    raise LookupError(f"No valid idols for the group {self.gender} and {self.difficulty}.")
                self.idol = random.choice(self.idol_set)

                # Create acceptable answers
                await self.create_acceptable_answers()

                log.console(f"{self.correct_answer} - Unscramble {self.channel.id}")

                """
                In order to create the scrambled word:
                -> First, we will take all of the words (split by spaces) 
                in the name and put them individually into a list and shuffle their order.
                
                -> Then, in every word, we will shuffle the characters.
                -> If the difficulty is hard, we will make the entire scrambled name lower case.
                """
                word_list = self.correct_answer.split()  # word of the correct answers in a list to shuffle.
                random.shuffle(word_list)
                scrambled_word = ""
                for word in word_list:
                    char_list = [char for char in word]
                    random.shuffle(char_list)
                    if scrambled_word:
                        scrambled_word += " "  # adding a space before next word.
                    scrambled_word += "".join(char_list)
                if self.difficulty == "hard":
                    scrambled_word = scrambled_word.lower()

                await self.channel.send(f"The name I want you to unscramble is `{scrambled_word}`.")

                question_posted = True
            except LookupError as e:
                raise e
            except Exception as e:
                log.console(f"{e} - unscramblegame.create_new_question")
                continue

    async def display_winners(self):
        """Displays the winners and their scores."""
        final_scores = ""
        if self.players:
            for user_id in self.players:
                final_scores += f"<@{user_id}> -> {self.players.get(user_id)}\n"
        return await self.channel.send(f">>> Unscramble game has finished.\nScores:\n{final_scores}")

    async def end_game(self):
        """Ends an unscramble game."""
        if self.results_posted:
            return True

        self.force_ended = True
        self.rounds = self.max_rounds
        await self.update_scores()
        await self.display_winners()
        self.results_posted = True
        return True

    async def update_scores(self):
        """Updates all player scores"""
        for user_id in self.players:
            await self.ex.u_unscramblegame.update_user_unscramble_game_score(self.difficulty, user_id=user_id,
                                                                             score=self.players.get(user_id))

    async def print_answer(self):
        """Prints the current round's answer."""
        await self.channel.send(f"The correct answer was {self.correct_answer}")

    async def create_acceptable_answers(self):
        """Create acceptable answers."""
        possible_answers = []

        if self.difficulty in ["easy", "medium", "hard"]:
            possible_answers.append(self.idol.stage_name)

        elif self.difficulty in ["medium", "hard"]:
            for group_id in self.idol:
                await asyncio.sleep(0)  # bare yield
                group = await self.ex.u_group_members.get_group(group_id)
                if group.name == "NULL":  # we do not want a test group to be represented as the final question.
                    continue
                possible_answers.append(group.name)

            possible_answers.append(self.idol.full_name)

        elif self.difficulty in ["hard"]:
            if self.idol.former_full_name:
                possible_answers.append(self.idol.former_full_name)
            if self.idol.former_stage_name:
                possible_answers.append(self.idol.former_stage_name)
            if self.idol.aliases:
                for alias in self.idol.aliases:
                    await asyncio.sleep(0)  # bare yield
                    possible_answers.append(alias)

        else:
            raise self.ex.exceptions.ShouldNotBeHere("unscramblegame.create_acceptable_answers")

        self.correct_answer = (random.choice(possible_answers))  # we do not worry/care about case-sensitivity here.

    async def create_idol_pool(self):
        """Create the game's idol pool."""
        idol_gender_set = self.ex.cache.gender_selection.get(self.gender)
        idol_difficulty_set = self.ex.cache.difficulty_selection.get(self.difficulty)
        self.ex.cache.idols_female.update({idol for idol in self.ex.cache.idols if idol.gender == 'f'
                                           and idol.photo_count})
        self.idol_set = list(idol_gender_set & idol_difficulty_set)

    async def process_game(self):
        """Ignores errors and continuously makes new questions until the game should end."""
        self.host_user = await self.ex.get_user(self.host_id)
        await self.create_idol_pool()
        try:
            while self.rounds < self.max_rounds and not self.force_ended:
                try:
                    await self.create_new_question()
                except LookupError as e:
                    await self.channel.send(f"The gender, difficulty, and filtered settings selected have no idols. "
                                            f"Ending Game.")
                    log.console(e)
                    return
                await self.check_message()
            await self.end_game()
        except Exception as e:
            await self.channel.send(f"An error has occurred and the game has ended. Please report this.")
            log.console(e)
