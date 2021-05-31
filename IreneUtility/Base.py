from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Utility


class Base:
    """
    Base Class that will hold the utility object for a subclass.
    Meant to be a parent class.
    """
    def __init__(self, utility_object):
        self.ex: Utility.Utility = utility_object
