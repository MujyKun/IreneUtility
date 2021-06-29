from . import self


async def insert_photo_uploaded(image_id, media_id):
    """Insert an image so that we can keep track of twitter media uploads.

    :param image_id: Unique Image ID
    :param media_id: Twitter Media ID
    """
    return await self.conn.execute("INSERT INTO twitter.mediauploaded(imageid, mediaid) VALUES ($1, $2)", image_id,
                                   media_id)


async def check_photo_uploaded(image_id):
    """Checks if a photo was already uploaded.

    :param image_id: The unique image id.
    :returns: Count of the image id in the table (should be 0 or 1)
    """
    return (await self.conn.fetchrow("SELECT COUNT(*) FROM twitter.mediauploaded WHERE imageid = $1", image_id))[0]
