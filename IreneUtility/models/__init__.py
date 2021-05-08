class BaseUtil:
    """Serves as an extension to avoid Circular imports while maintaining the main Utility object
    across the models that need to utilize certain methods.

    Note that we have this as a class so we do not need to constantly import if ex is None. This object makes it
    much easier to maintain.
    """
    def __init__(self):
        self.ex = None


base_util = BaseUtil()

from .group import Group
from .idol import Idol
from .user import User
from .idolcard import IdolCard
from .album import Album
from .gachavalue import GachaValues

