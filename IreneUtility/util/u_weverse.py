import discord
from ..Base import Base
from Weverse.models import Notification
from . import u_logger as log
import aiofiles
import asyncio


# noinspection PyBroadException,PyPep8
class Weverse(Base):
    def __init__(self, *args):
        super().__init__(*args)
        self.current_notification_id = 0
        self.notifications_already_posted = {}  # channel_id : [notification ids]
        
    async def add_weverse_channel(self, channel_id, community_name):
        """Add a channel to get updates for a community"""
        community_name = community_name.lower()
        await self.ex.conn.execute("INSERT INTO weverse.channels(channelid, communityname) VALUES($1, $2)", channel_id,
                                   community_name)
        await self.add_weverse_channel_to_cache(channel_id, community_name)

    async def add_weverse_channel_to_cache(self, channel_id, community_name):
        """Add a weverse channel to cache."""
        community_name = community_name.lower()
        channels = self.ex.cache.weverse_channels.get(community_name)
        if channels:
            channels.append([channel_id, None, False, False])
        else:
            self.ex.cache.weverse_channels[community_name] = [[channel_id, None, False, False]]

    async def check_weverse_channel(self, channel_id, community_name):
        """Check if a channel is already getting updates for a community"""
        channels = self.ex.cache.weverse_channels.get(community_name.lower())
        if channels:
            for channel in channels:
                if channel_id == channel[0]:
                    return True
        return False

    async def get_weverse_channels(self, community_name):
        """Get all of the channel ids for a specific community name"""
        return self.ex.cache.weverse_channels.get(community_name.lower())

    async def delete_weverse_channel(self, channel_id, community_name):
        """Delete a community from a channel's updates."""
        community_name = community_name.lower()
        await self.ex.conn.execute("DELETE FROM weverse.channels WHERE channelid = $1 AND communityname = $2",
                                   channel_id, community_name)
        channels = await self.get_weverse_channels(community_name)

        if not channels:
            return

        for channel in channels:
            if channel[0] == channel_id:
                if channels:
                    channels.remove(channel)
                else:
                    self.ex.cache.weverse_channels.pop(community_name)

    async def add_weverse_role(self, channel_id, community_name, role_id):
        """Add a weverse role to notify."""
        await self.ex.conn.execute("UPDATE weverse.channels SET roleid = $1 WHERE channelid = $2 AND communityname = "
                                   "$3", role_id, channel_id, community_name.lower())
        await self.replace_cache_role_id(channel_id, community_name, role_id)

    async def delete_weverse_role(self, channel_id, community_name):
        """Remove a weverse role from a server (no longer notifies a role)."""
        await self.ex.conn.execute(
            "UPDATE weverse.channels SET roleid = NULL WHERE channel_id = $1 AND communityname = $2", channel_id,
            community_name.lower())
        await self.replace_cache_role_id(channel_id, community_name, None)

    async def replace_cache_role_id(self, channel_id, community_name, role_id):
        """Replace the server role that gets notified on Weverse Updates."""
        channels = self.ex.cache.weverse_channels.get(community_name)
        for channel in channels:
            cache_channel_id = channel[0]
            if cache_channel_id == channel_id:
                channel[1] = role_id

    async def change_weverse_comment_media_status(self, channel_id, community_name, t_disabled, updated=False,
                                                  media=False):
        """Change a channel's subscription and whether or not they receive updates on comments/comments.

        :param channel_id: (int) Channel id on discord
        :param community_name: (str) Community name on Weverse
        :param t_disabled: (integer) Represents the current status of the disable.
        :param updated: (bool) Whether it needs to be updated.
        :param media: (bool) Whether to disable media or not.
        """
        t_disabled = bool(t_disabled)
        community_name = community_name.lower()

        if updated:
            await self.ex.conn.execute(
                f"UPDATE weverse.channels SET {'comments' if not media else 'media'}disabled "
                f"= $1 WHERE channelid = $2 AND communityname = $3",
                int(t_disabled), channel_id, community_name)
        channels = self.ex.cache.weverse_channels.get(community_name)
        for channel in channels:
            cache_channel_id = channel[0]
            if cache_channel_id == channel_id:
                if media:
                    channel[3] = t_disabled
                else:
                    channel[2] = t_disabled

    async def change_weverse_media_status(self, channel_id, community_name, media_disabled, updated=False):
        """Change a channel's subscription and whether or not they receive updates on media."""

    async def set_comment_embed(self, notification, embed_title):
        """Set Comment Embed for Weverse."""
        comment_body = await self.ex.weverse_client.fetch_comment_body(notification.community_id,
                                                                       notification.contents_id)
        if not comment_body:
            artist_comments = await self.ex.weverse_client.fetch_artist_comments(notification.community_id,
                                                                                 notification.contents_id)
            if artist_comments:
                comment_body = (artist_comments[0]).body
            else:
                return
        translation = await self.ex.weverse_client.translate(notification.contents_id, is_comment=True,
                                                             community_id=notification.community_id)

        if not translation:
            # translate using Irene's API instead.
            translation_json = await self.ex.u_miscellaneous.translate(comment_body, "KR", "EN") or {"code": -1}
            if translation_json.get("code") == 0:
                translation = translation_json.get("text")

        embed_description = f"**{notification.message}**\n\n" \
                            f"Content: **{comment_body}**\n" \
                            f"Translated Content: **{translation}**"
        embed = await self.ex.create_embed(title=embed_title, title_desc=embed_description)
        return embed

    async def set_post_embed(self, notification, embed_title):
        """Set Post Embed for Weverse.

        :returns: Embed and ( a list of file locations OR a string with image urls )
        """
        post = self.ex.weverse_client.get_post_by_id(notification.contents_id)
        if post:
            translation = await self.ex.weverse_client.translate(post.id, is_post=True, p_obj=post,
                                                                 community_id=notification.community_id)
            if not translation:
                # translate using Irene's API instead.
                translation_json = await self.ex.u_miscellaneous.translate(post.body, "KR", "EN") or {"code": -1}
                if translation_json.get("code") == 0:
                    translation = translation_json.get("text")

            # artist = self.weverse_client.get_artist_by_id(notification.artist_id)
            embed_description = f"**{notification.message}**\n\n" \
                                f"Artist: **{post.artist.name} ({post.artist.list_name[0]})**\n" \
                                f"Content: **{post.body}**\n" \
                                f"Translated Content: **{translation}**"
            embed = await self.ex.create_embed(title=embed_title, title_desc=embed_description)

            # will either be file locations or image links.
            photos = [await self.download_weverse_post(photo.original_img_url, photo.file_name) for photo in
                      post.photos]

            images = []
            image_urls = []
            for photo in photos:
                image = photo[0]
                from_host = photo[1]

                if from_host:
                    # file locations
                    images.append(image)
                else:
                    image_urls.append(image)

            message = "\n".join(image_urls)
            return embed, images, message
        return None, None, None

    async def download_weverse_post(self, url, file_name):
        """Downloads an image url and returns image host url.

        If we are to upload from host, it will return the folder location instead (Unless the file is more than 8mb).


        :returns: list of photos/image links, whether it is from the host.
        """
        from_host = False
        async with self.ex.session.get(url) as resp:
            async with aiofiles.open(self.ex.keys.weverse_image_folder + file_name, mode='wb') as fd:
                data = await resp.read()
                await fd.write(data)
                log.console(f"{len(data)} - Length of Weverse File - {file_name}")
                if len(data) >= 8000000:  # 8 mb
                    return [f"https://images.irenebot.com/weverse/{file_name}", from_host]

        if self.ex.upload_from_host:
            from_host = True
            return [f"{self.ex.keys.weverse_image_folder}{file_name}", from_host]
        return [f"https://images.irenebot.com/weverse/{file_name}", from_host]

    async def set_media_embed(self, notification, embed_title):
        """Set Media Embed for Weverse."""
        media = self.ex.weverse_client.get_media_by_id(notification.contents_id)
        if media:
            embed_description = f"**{notification.message}**\n\n" \
                                f"Title: **{media.title}**\n" \
                                f"Content: **{media.body}**\n"
            embed = await self.ex.create_embed(title=embed_title, title_desc=embed_description)
            message = media.video_link
            return embed, message
        return None, None

    async def send_weverse_to_channel(self, channel_info, message_text, embed, is_comment, is_media, community_name,
                                      images=None):
        channel_id = channel_info[0]
        role_id = channel_info[1]
        comments_disabled = channel_info[2]
        media_disabled = channel_info[3]

        if (is_comment and comments_disabled) or (is_media and media_disabled):
            return  # if the user has the post disabled, we should not post it.

        try:
            channel = self.ex.client.get_channel(channel_id)
            if not channel:
                # fetch channel instead (assuming discord.py cache did not load)
                channel = await self.ex.client.fetch_channel(channel_id)
        except:
            # remove the channel from future updates as it cannot be found.
            return await self.delete_weverse_channel(channel_id, community_name.lower())

        msg_list = []
        file_list = []

        try:
            msg_list.append(await channel.send(embed=embed))
            if message_text:
                # Since an embed already exists, any individual content will not load
                # as an embed -> Make it it's own message.
                if images:
                    # a list of file locations
                    for photo_location in images:
                        file_list.append(discord.File(photo_location))

                if role_id:
                    message_text = f"<@&{role_id}>\n{message_text if message_text else ''}"
                msg_list.append(await channel.send(message_text if message_text else None, files=(file_list or None)))
                log.console(f"Weverse Post for {community_name} sent to {channel_id}.",
                            method=self.send_weverse_to_channel)
        except discord.Forbidden as e:
            # no permission to post
            log.console(f"{e} (discord.Forbidden) - Weverse Post Failed to {channel_id} for {community_name}",
                        method=self.send_weverse_to_channel)
            # remove the channel from future updates as we do not want it to clog our rate-limits.
            return await self.delete_weverse_channel(channel_id, community_name.lower())
        except Exception as e:
            log.console(f"{e} (Exception) - Weverse Post Failed to {channel_id} for {community_name}",
                        method=self.send_weverse_to_channel)
            return

        if self.ex.weverse_announcements:
            for msg in msg_list:
                try:
                    await msg.publish()
                except Exception as e:
                    log.useless(f"{e} (Exception) - Failed to publish Message {msg.id}.",
                                method=self.send_weverse_to_channel)

    async def disable_type(self, ctx, community_name, media=False):
        """Disable media/comments on a community and deal with the user messages.


        :param ctx: Context Object
        :param community_name: Weverse community name
        :param media: Whether the post type is media
        """
        post_type = "media" if media else "comments"
        if self.ex.weverse_announcements:
            if ctx.author.id != self.ex.keys.owner_id:
                msg = await self.ex.get_msg(ctx.author.id, "weverse", "bot_owner_only",
                                            ["support_server_link", self.ex.keys.bot_support_server_link])
                return await ctx.send(msg)

        channel_id = ctx.channel.id
        if not await self.ex.u_weverse.check_weverse_channel(channel_id, community_name):
            return await ctx.send(f"This channel is not subscribed to weverse updates from {community_name}.")
        for channel in await self.ex.u_weverse.get_weverse_channels(community_name):
            await asyncio.sleep(0)
            if channel[0] != channel_id:
                continue
            await self.change_weverse_comment_media_status(channel_id, community_name,
                                                           (not channel[2]) if not media else
                                                           (not channel[3]), updated=True, media=media)
            if channel[2]:
                return await ctx.send(f"> This channel will no longer receive {post_type} from {community_name}.")
            return await ctx.send(f"> This channel will now receive {post_type} from {community_name}.")

    async def send_notification(self, notification: Notification):
        """Send a notification to all of the needed channels.


        :param notification: (Weverse Notification)
        """
        is_comment = False
        is_media = False
        images = None
        community_name = notification.community_name or notification.bold_element
        if not community_name:
            return
        channels = await self.ex.u_weverse.get_weverse_channels(community_name.lower())
        if not channels:
            log.console("WARNING: There were no channels to post the Weverse notification to.")
            return

        noti_type = self.ex.weverse_client.determine_notification_type(notification.message)
        embed_title = f"New {community_name} Notification!"
        message_text = None
        if noti_type == 'comment':
            is_comment = True
            embed = await self.ex.u_weverse.set_comment_embed(notification, embed_title)
        elif noti_type == 'post':
            is_media = True
            embed, images, message_text = await self.ex.u_weverse.set_post_embed(notification, embed_title)
        elif noti_type == 'media':
            is_media = True
            embed, message_text = await self.ex.u_weverse.set_media_embed(notification, embed_title)
        elif noti_type == 'announcement':
            return None  # not keeping track of announcements ATM
        else:
            return None

        if not embed:
            log.console(f"WARNING: Could not receive Weverse information for {community_name}. "
                        f"Noti ID:{notification.id} - "
                        f"Contents ID: {notification.contents_id} - "
                        f"Noti Type: {notification.contents_type}")
            return  # we do not want constant attempts to send a message.

        server_text_channel_ids = []  # text channels that belong to the support server

        try:
            support_server = self.ex.client.get_guild(self.ex.keys.bot_support_server_id) or self.ex.client. \
                fetch_guild(self.ex.keys.bot_support_server_id)

            server_text_channel_ids = [channel.id for channel in support_server.text_channels]
        except:
            warning_msg = "WARNING: Support Server could not be found for Weverse Cache to get the text channel IDs."
            log.console(warning_msg)
            log.useless(warning_msg)

        for channel_info in channels:
            channel_id = channel_info[0]
            if self.ex.weverse_announcements and channel_id not in server_text_channel_ids:
                # we do not want to remove the existing list of channels in the database, so we will use a filtering
                # method instead
                continue

            # sleeping for 2 seconds before every channel post. still needs to be properly tested
            # for rate-limits

            # after testing, Irene has been rate-limited too often, so we will introduce announcement
            # channels to the support server instead of constantly sending the same content to every channel.
            if not self.ex.weverse_announcements:
                await asyncio.sleep(2)

            notification_ids = self.notifications_already_posted.get(channel_id)
            if not notification_ids:
                await self.ex.u_weverse.send_weverse_to_channel(channel_info, message_text, embed, is_comment, is_media,
                                                                community_name, images=images)
                self.notifications_already_posted[channel_id] = [notification.id]
            else:
                if notification.id in notification_ids:
                    # it was already posted
                    continue

                self.notifications_already_posted[channel_id].append(notification.id)
                await self.ex.u_weverse.send_weverse_to_channel(channel_info, message_text, embed,
                                                                is_comment, is_media, community_name, images=images)
