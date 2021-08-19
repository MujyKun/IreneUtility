from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..Utility import Utility


class BaseUtil:
    """Serves as an extension to avoid Circular imports while maintaining the main Utility object
    across the models that need to utilize certain methods.

    Note that we have this as a class so we do not need to constantly import if ex is None. This object makes it
    much easier to maintain.
    """
    def __init__(self):
        self.ex: Optional[Utility] = None


base_util = BaseUtil()

from .subscription import Subscription
from .file import File
from .twitterchannel import TwitterChannel
from .vlivechannel import VliveChannel
from .group import Group
from .idol import Idol
from .user import User
from .game import Game
from .idolcard import IdolCard
from .album import Album
from .gachavalue import GachaValues
from .keys import Keys
from .image import Image
from .command import Command
from .playingcard import PlayingCard
from .guessinggame import GuessingGame
from .unscramblegame import UnScrambleGame
from .biasgame import BiasGame
from .blackjackgame import BlackJackGame
