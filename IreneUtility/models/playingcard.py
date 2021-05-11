import random
from decimal import Decimal
from math import log10
from random import randint

import IreneUtility.models
import IreneUtility.s_sql as sql
import IreneUtility.util.u_exceptions as exceptions


# noinspection PyBroadException
class PlayingCard:
    """Represents a custom playing card."""
    def __init__(self, id, file_name, card_name, file_location, image_url, background_idol, value):
        """

        :param id: Custom Card ID
        :param file_name: Custom Card File Name -> Typically the ID of the custom card followed by the file type.
        :param card_name: The card's name ex: "Ace of Spades"
        :param file_location: The full file location
        :param image_url: Image host url of the image
        :param background_idol: Idol object that is in the background of the card.
        :param value: the card's worth.
        """
        self.id: int = id
        self.file_name: str = file_name
        self.card_name: str = card_name
        self.file_location: str = file_location
        self.image_url: str = image_url
        self.background_idol: IreneUtility.models.Idol = background_idol
        self.value: int = value