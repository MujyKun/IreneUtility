import discord


# noinspection PyBroadException
class File:
    """Represents an OS file."""
    def __init__(self, file_location, image_url):
        """
        :param file_location: The full file location
        :param image_url: Image host url of the image
        """

        self.file_location: str = file_location
        self.image_url: str = image_url

    async def send_file(self, channel: discord.TextChannel, message=None, url=False):
        """

        :param channel: Discord Text Channel to send the file to.
        :param message: Message followed with the image.
        :param url: True/False if the url should be posted instead.
        """
        if not url:
            local_file = discord.File(self.file_location, spoiler=True)
            return await channel.send(message, file=local_file)
        else:
            if message is None:
                message = url
            else:
                message += f" {self.image_url}"
            return await channel.send(message)