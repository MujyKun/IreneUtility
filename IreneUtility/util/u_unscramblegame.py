from ..Base import Base
from . import u_logger as log


class UnScrambleGame(Base):
    def __init__(self, *args):
        super().__init__(*args)

    async def update_user_unscramble_game_score(self, difficulty, user_id, score):
        """Update a user's unscramble game score."""
        try:
            user_scores = self.ex.cache.unscramble_game_counter.get(user_id)
            # if the user does not exist, create them in the db & cache
            if not user_scores:
                await self.create_user_in_unscramble_game(user_id)
                user_scores = {}  # set to default so getting current user score does not error.
            difficulty_score = user_scores.get(difficulty) or 0
            # difficulty score will always exist, no need to have a condition.
            user_scores[difficulty] = difficulty_score + score
            await self.update_user_score_in_db(difficulty, user_scores[difficulty], user_id)
        except Exception as e:
            log.console(f"{e} -> update_user_unscramble_game_score")

    async def create_user_in_unscramble_game(self, user_id):
        """Inserts a user into the unscramble game db with no scores. This allows for updating scores easier."""
        self.ex.cache.unscramble_game_counter[user_id] = {"easy": 0, "medium": 0, "hard": 0}
        return await self.ex.conn.execute("INSERT INTO stats.unscramblegame(userid) VALUES ($1)", user_id)

    async def update_user_score_in_db(self, difficulty, score, user_id):
        return await self.ex.conn.execute(f"UPDATE stats.unscramblegame SET {difficulty} = $1 WHERE userid = $2", score,
                                          user_id)

    async def get_unscramble_game_top_ten(self, difficulty, members=None):
        """Get the top ten of a certain unscramble game difficulty"""
        # make sure it is actually a difficulty in case of s_sql-injection.
        # (condition created in case of future changes)
        if difficulty.lower() not in self.ex.cache.difficulty_levels:
            raise ValueError("invalid difficulty given to get_unscramble_game_top_ten()")
        if members:
            return await self.ex.conn.fetch(f"SELECT userid, {difficulty} FROM stats.unscramblegame WHERE {difficulty} "
                                            f"is not null AND userid IN {members} ORDER BY {difficulty} DESC LIMIT 10")
        return await self.ex.conn.fetch(f"SELECT userid, {difficulty} FROM stats.unscramblegame WHERE {difficulty} "
                                        f"is not null ORDER BY {difficulty} DESC LIMIT 10")

    async def get_user_score(self, difficulty: str, user_id):
        user_scores = self.ex.cache.unscramble_game_counter.get(user_id)
        if not user_scores:
            return 0
        difficulty_score = user_scores.get(difficulty) or 0
        return difficulty_score
