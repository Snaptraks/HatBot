import asyncio
from datetime import timedelta
import discord
from discord.ext import commands
from discord.utils import escape_markdown
import logging

from ..utils.cog import BasicCog


logger = logging.getLogger('discord')


class Moderation(BasicCog):
    """Cog for moderation of a Discord Guild."""
    
    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(self, ctx, member: discord.Member, time='15m'):
        """Prevents the member to send messages and add reactions.
        Syntax is '!mute <member> [time]', where time is ##A, where
        ## is a number (any) and A is ONE of (s, m, h, d) for
        seconds, minutes, hours, and days respectively. Defaults to
        15 minutes ('15m')."""
        guild_permissions = member.guild_permissions
        wait_time = parse_time(time).total_seconds()
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
                    await channel.set_permissions(member, overwrite=overwrite)

            await asyncio.sleep(wait_time)
            await ctx.invoke(self.unmute, member)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Removes the mute on member."""
        for channel in ctx.guild.text_channels:
            permissions = channel.permissions_for(member)

            if permissions.read_messages:
                # This removes the PermissionOverwrite on the channel, it
                # does not grant send_messages=True
                await channel.set_permissions(member, overwrite=None)

    @mute.error
    async def mute_error(self, ctx, error):
        """Handles errors."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need to provide someone to mute.')

        elif isinstance(error, commands.BadArgument):
            await ctx.send('Unknown member.')


def parse_time(time):
    # TODO: make a better time parsing function
    units = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        }

    for u in units.keys():
        if u in time:
            duration = timedelta(**{units[u]: float(time[:-1])})
            return duration

    raise ValueError('Invalid time format.')
