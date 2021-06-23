import discord
from ..Base import Base
from . import u_logger as log
import aiofiles
import asyncio


# noinspection PyBroadException,PyPep8
class Weverse(Base):
    def __init__(self, *args):
        super().__init__(*args)
        
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
            channels.append([channel_id, None, False])
        else:
            self.ex.cache.weverse_channels[community_name] = [[channel_id, None, False]]

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
        await self.ex.conn.execute("DELETE FROM weverse.channels WHERE channelid = $1 AND communityname = $2", channel_id,
                              community_name)
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
        await self.ex.conn.execute("UPDATE weverse.channels SET roleid = $1 WHERE channelid = $2 AND communityname = $3",
                              role_id, channel_id, community_name.lower())
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
        comment_body = await self.ex.weverse_client.fetch_comment_body(notification.community_id, notification.contents_id)
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

            if self.ex.upload_from_host:
                # file locations
                return embed, photos

            # image links
            message = "\n".join(photos)
            return embed, message
        return None, None

    async def download_weverse_post(self, url, file_name):
        """Downloads an image url and returns image host url.

        If we are to upload from host, it will return the folder location instead.
        """
        async with self.ex.session.get(url) as resp:
            fd = await aiofiles.open(self.ex.keys.weverse_image_folder + file_name, mode='wb')
            await fd.write(await resp.read())
        if self.ex.upload_from_host:
            return f"{self.ex.keys.weverse_image_folder}{file_name}"
        return f"https://images.irenebot.com/weverse/{file_name}"

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

    async def send_weverse_to_channel(self, channel_info, message_text, embed, is_comment, community_name):
        channel_id = channel_info[0]
        role_id = channel_info[1]
        comments_disabled = channel_info[2]

        if not (is_comment and comments_disabled):
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
                    if isinstance(message_text, list):
                        # a list of file locations
                        for photo_location in message_text:
                            file_list.append(discord.File(photo_location))

                    if role_id:
                        message_text = f"<@&{role_id}>\n{message_text if not file_list else ''}"
                    msg_list.append(await channel.send(message_text if not file_list else None, files=(file_list or
                                                                                                       None)))
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
