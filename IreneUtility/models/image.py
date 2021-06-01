from . import File, Idol


# noinspection PyBroadException
class Image(File):
    """Represents a custom playing card."""
    def __init__(self, p_id, file_name, file_location, image_url, background_idol, face_count=None):
        """
        :param p_id: Unique Image ID
        :param file_name: File Name
        :param file_location: The full file location
        :param image_url: Image host url of the image
        :param background_idol: Idol object that the image belongs to.
        """
        super().__init__(file_location, image_url)
        self.id: int = p_id
        self.file_name: str = file_name
        self.background_idol: Idol = background_idol
        self.face_count = face_count
