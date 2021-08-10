from . import VliveChannel, base_util, TwitterChannel


class Group:
    """A group of idols/celebrities"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('groupid')
        self.name = kwargs.get('groupname')
        self.debut_date = kwargs.get('debutdate')
        self.disband_date = kwargs.get('disbanddate')
        self.description = kwargs.get('description')
        self.twitter = kwargs.get('twitter')
        self.youtube = kwargs.get('youtube')
        self.melon = kwargs.get('melon')
        self.instagram = kwargs.get('instagram')
        self.vlive = kwargs.get('vlive')
        if self.vlive:
            self.vlive = VliveChannel(self.vlive)
            base_util.ex.cache.vlive_channels[self.vlive.id.lower()] = self.vlive
        if self.twitter:
            self.twitter = TwitterChannel(self.twitter)
            base_util.ex.cache.twitter_channels[self.twitter.id.lower()] = self.twitter
        self.spotify = kwargs.get('spotify')
        self.fancafe = kwargs.get('fancafe')
        self.facebook = kwargs.get('facebook')
        self.tiktok = kwargs.get('tiktok')
        self.aliases = []
        self.local_aliases = {}  # server_id: [aliases]
        self.members = []  # idol ids, not idol objects.
        self.fandom = kwargs.get('fandom')
        self.company = kwargs.get('company')
        self.website = kwargs.get('website')
        self.thumbnail = kwargs.get('thumbnail')
        self.banner = kwargs.get('banner')
        self.gender = kwargs.get('gender')
        self.skill = kwargs.get('skill')
        self.photo_count = 0
        self.tags = kwargs.get('tags')
        if self.tags:
            self.tags = self.tags.split(',')

    async def send_images_to_host(self):
        file_name = f"{self.id}_GROUP.png"
        if self.thumbnail:
            file_loc = f"{base_util.ex.keys.idol_avatar_location}{file_name}"
            if 'images.irenebot.com' not in self.thumbnail:
                await base_util.ex.download_image(self.thumbnail, file_loc)
            image_url = f"https://images.irenebot.com/avatar/{file_name}"
            if base_util.ex.check_file_exists(file_loc):
                await base_util.ex.sql.s_groupmembers.set_group_thumbnail(self.id, image_url)
                self.thumbnail = image_url
        if self.banner:
            file_loc = f"{base_util.ex.keys.idol_banner_location}{file_name}"
            if 'images.irenebot.com' not in self.banner:
                await base_util.ex.download_image(self.banner, file_loc)
            image_url = f"https://images.irenebot.com/banner/{file_name}"
            if base_util.ex.check_file_exists(file_loc):
                await base_util.ex.sql.s_groupmembers.set_group_banner(self.id, image_url)
                self.banner = image_url

    def set_attribute(self, column, content):
        """Sets the attribute for a column in the DB.

        :param column: Column Name in DB
        :param content: Content to set the attribute to.
        """
        if column.lower() == "id":
            raise NotImplementedError

        key_to_replace = None
        for key, value in self.__dict__.items():
            if column == "groupname":
                key_to_replace = "name"
                break

            altered_key = key.replace(" ", "")
            altered_key = altered_key.replace("_", "")

            if column.lower() == altered_key:
                key_to_replace = key
                break  # we do not want to raise an exception of the object data changing.

        if key_to_replace:
            self.__dict__[key_to_replace] = content
