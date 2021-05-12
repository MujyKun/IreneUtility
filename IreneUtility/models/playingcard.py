import IreneUtility.models
from . import File


# noinspection PyBroadException
class PlayingCard(File):
    """Represents a custom playing card."""
    def __init__(self, p_id, file_name, card_id, card_name, file_location, image_url, background_idol, value):
        """

        :param id: Custom Card ID
        :param file_name: Custom Card File Name -> Typically the ID of the custom card followed by the file type.
        :param card_id: The original card (numbered 1 to 52)
        :param card_name: The card's name ex: "Ace of Spades"
        :param file_location: The full file location
        :param image_url: Image host url of the image
        :param background_idol: Idol object that is in the background of the card.
        :param value: the card's worth.
        """
        super().__init__(file_location, image_url)
        self.id: int = p_id
        self.file_name: str = file_name
        self.card_id: int = card_id
        self.card_name: str = card_name
        self.background_idol: IreneUtility.models.Idol = background_idol
        self.value: int = value
