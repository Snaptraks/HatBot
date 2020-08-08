import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging

from ..utils.cogs import BasicCog
from ..utils.converters import Duration


logger = logging.getLogger('discord')


class Moderation(BasicCog):
    """Cog for moderation of a Discord Guild."""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(self, ctx, member: discord.Member, time: Duration = None,
                   *, reason=None):
        """Prevent the member to send messages and add reactions.
        Syntax is '!mute <member> [time] [reason]'. time defaults to
        15 minutes ('15m'). The reason is optional and added to the Audit Log.
        """
        guild_permissions = member.guild_permissions
        if time is None:
            wait_time = timedelta(minutes=15)
        else:
            wait_time = time - datetime.utcnow()
        # Because sometimes members have nicknames with markdown
        escaped_name = escape_markdown(member.display_name)

        if guild_permissions.kick_members:
            # do not mute someone who has permissions to kick members
            await ctx.send(f'Cannot mute {escaped_name} due to roles.')

        elif member.bot:
            # do not mute bots
            await ctx.send(f'Cannot mute {escaped_name} (is a bot).')

        else:
            overwrite = discord.PermissionOverwrite(
                add_reactions=False,
                send_messages=False,
            )

            log_str = (f'{ctx.author.display_name} has muted '
                       f'member {member} (<@{member.id}>) for {time}.')
            logger.info(log_str)

            for channel in ctx.guild.text_channels:
                permissions = channel.permissions_for(member)

                if permissions.read_messages:
                    await channel.set_permissions(
                        member,
                        overwrite=overwrite,
                        reason=reason
                    )

            await asyncio.sleep(wait_time.total_seconds())
            await ctx.invoke(self.unmute, member)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Remove the mute on member."""

        for channel in ctx.guild.text_channels:
            permissions = channel.permissions_for(member)

            if permissions.read_messages:
                # This removes the PermissionOverwrite on the channel, it
                # does not grant send_messages=True
                await channel.set_permissions(member, overwrite=None)

    @mute.error
    async def mute_error(self, ctx, error):
        """Handle errors."""

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need to provide someone to mute.')

        elif isinstance(error, commands.BadArgument):
            await ctx.send('Unknown member.')
