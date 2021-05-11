from . import Game as Game_Base, User, PlayingCard
from typing import List


class BlackJackGame(Game_Base):
    def __init__(self, *args, first_player):
        super().__init__(*args)
        self.first_player: User = first_player
        self.first_player.in_currency_game = True
        self.second_player: User
        self.first_player_cards: List[PlayingCard] = []
        self.second_player_cards: List[PlayingCard] = []
