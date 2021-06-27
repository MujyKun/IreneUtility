from ..Base import Base
from os import listdir
from random import choice
from . import u_logger as log


class Twitter(Base):
    def __init__(self, *args):
        super().__init__(*args)
        
    async def update_status(self, context):
        self.ex.api.update_status(status=context)
        tweet = self.ex.api.user_timeline(user_id=f'{self.ex.keys.twitter_account_id}', count=1)[0]
        return f"https://twitter.com/{self.ex.keys.twitter_username}/status/{tweet.id}"

    async def delete_status(self, context):
        self.ex.api.destroy_status(context)

    async def recent_tweets(self, context):
        tweets = self.ex.api.user_timeline(user_id=f'{self.ex.keys.twitter_account_id}', count=context)
        final_tweet = ""
        for tweet in tweets:
            final_tweet += f"> **Tweet ID:** {tweet.id} | **Tweet:** {tweet.text}\n"
        return final_tweet

    async def upload_random_image(self):
        """Uploads a random (BUT UNIQUE) idol photo to twitter.

        :returns: twitter body message & twitter link to the post.
        """
        try:
            # random_file = (self.ex.thread_pool.submit(self.get_random_idol_photo)).result()
            random_file = await self.ex.run_blocking_code(self.get_random_idol_photo)
            if not random_file:
                return False

            unique_text_pos = random_file.find("image")
            if unique_text_pos == -1:
                unique_text_pos = random_file.find("video")

                # we do not actually want videos, so we will recall the method.
                if unique_text_pos != -1:
                    return await self.upload_random_image()

            if not unique_text_pos:
                return False  # could not find image id.

            image_id = int(random_file[0:unique_text_pos])

            # check if the file is already uploaded.
            if await self.ex.sql.s_twitter.check_photo_uploaded(image_id):
                # can result in infinite loop if there is only one file in the folder.
                # but the maximum recursion depth will cancel this out.
                return await self.upload_random_image()

            idol = await self.ex.u_group_members.get_idol_by_image_id(image_id)
            body_message = f"({image_id})"
            if idol:
                body_message += f" - {idol.full_name} ({idol.stage_name}) [{idol.id}]"

            full_file_location = f"{self.ex.keys.idol_photo_location}{random_file}"
            media = self.ex.api.media_upload(full_file_location)
            status = self.ex.api.update_status(status=body_message, media_ids=[media.media_id])
            await self.ex.sql.s_twitter.insert_photo_uploaded(image_id, media.media_id)
            return status.text
        except Exception as e:
            log.console(f"{e} (Exception)", method=self.upload_random_image)

    def get_random_idol_photo(self):
        """Get a random idol photo existing in the file directory.

        This method may block the heartbeat due to OS operation.
        Should be run separately.
        """
        return choice(listdir(self.ex.keys.idol_photo_location))

