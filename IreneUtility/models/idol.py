from . import VliveChannel, base_util, TwitterChannel


class Idol:
    """Represents an Idol/Celebrity."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.full_name = kwargs.get('fullname')
        self.stage_name = kwargs.get('stagename')
        self.former_full_name = kwargs.get('formerfullname')
        self.former_stage_name = kwargs.get('formerstagename')
        self.birth_date = kwargs.get('birthdate')
        self.birth_country = kwargs.get('birthcountry')
        self.birth_city = kwargs.get('birthcity')
        self.gender = kwargs.get('gender')
        self.description = kwargs.get('description')
        self.height = kwargs.get('height')
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
        self.groups = []  # group ids, not group objects.
        self.zodiac = kwargs.get('zodiac')
        self.thumbnail = kwargs.get('thumbnail')
        self.banner = kwargs.get('banner')
        self.blood_type = kwargs.get('bloodtype')
        self.photo_count = 0
        # amount of times the idol has been called.
        self.called = 0
        self.tags = kwargs.get('tags')
        self.difficulty = kwargs.get('difficulty') or "medium"  # easy = 1, medium = 2, hard = 3
        if self.tags:
            self.tags = self.tags.split(',')

    async def send_images_to_host(self):
        """Download Images to Host."""
        file_name = f"{self.id}_IDOL.png"
        if self.thumbnail:
            file_loc = f"{base_util.ex.keys.idol_avatar_location}{file_name}"
            if base_util.ex.keys.image_host not in self.thumbnail:
                await base_util.ex.download_image(self.thumbnail, file_loc)
                if base_util.ex.check_file_exists(file_loc):
                    image_url = f"{base_util.ex.keys.image_host}avatar/{file_name}"
                    await base_util.ex.sql.s_groupmembers.set_member_thumbnail(self.id, image_url)
                    self.thumbnail = image_url
            self.thumbnail = self.thumbnail.replace("//", "/")

        if self.banner:
            file_loc = f"{base_util.ex.keys.idol_banner_location}{file_name}"
            if base_util.ex.keys.image_host not in self.banner:
                await base_util.ex.download_image(self.banner, file_loc)
                image_url = f"{base_util.ex.keys.image_host}banner/{file_name}"
                if base_util.ex.check_file_exists(file_loc):
                    await base_util.ex.sql.s_groupmembers.set_member_banner(self.id, image_url)
                    self.banner = image_url
            self.banner = self.banner.replace("//", "/")

    def set_attribute(self, column, content):
        """Sets the attribute for a column in the DB.

        :param column: Column Name in DB
        :param content: Content to set the attribute to.
        """
        if column.lower() == "id":
            raise NotImplementedError

        key_to_replace = None
        for key, value in self.__dict__.items():
            altered_key = key.replace(" ", "")
            altered_key = altered_key.replace("_", "")

            if column.lower() == altered_key:
                key_to_replace = key
                break  # we do not want to raise an exception of the object data changing.

        if key_to_replace:
            self.__dict__[key_to_replace] = content
