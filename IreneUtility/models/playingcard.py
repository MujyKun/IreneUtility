from . import Image


# noinspection PyBroadException
class PlayingCard(Image):
    """Represents a custom playing card."""
    def __init__(self, *args, card_id, card_name, value):
        """

        :param p_id: Custom Card ID
        :param file_name: Custom Card File Name -> Typically the ID of the custom card followed by the file type.
        :param card_id: The original card (numbered 1 to 52)
        :param card_name: The card's name ex: "Ace of Spades"
        :param file_location: The full file location
        :param image_url: Image host url of the image
        :param background_idol: Idol object that is in the background of the card.
        :param value: the card's worth.
        """
        super().__init__(*args)
        self.card_id: int = card_id
        self.card_name: str = card_name
        self.value: int = value
