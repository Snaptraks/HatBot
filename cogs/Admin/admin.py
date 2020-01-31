import asyncio
import copy
from datetime import datetime, timedelta
import logging
import json
import re

import discord
from discord.ext import commands

from ..utils.cogs import BasicCog


logger = logging.getLogger('discord')


# class Admin(commands.Cog):
class Admin(BasicCog):
    """Collection of administrative commands."""

    def __init__(self, bot):
        super().__init__(bot)

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(aliases=['stop', 'quit', 'exit'])
    async def kill(self, ctx):
        """Stop the bot. Does not restart it."""

        await self.bot.logout()

    @commands.group(aliases=['cog', 'c'], invoke_without_command=True)
    async def cogs(self, ctx):
        """List current active cogs."""

        out_str = f'Active Cogs:\n`{", ".join(self.bot.cogs.keys())}`'
        await ctx.send(out_str)

    @cogs.command(name='load', aliases=['l'])
    async def cogs_load(self, ctx, module):
        """Load an extension."""

        await ctx.message.add_reaction('\U00002934')  # :arrow_heading_up:
        await self._cogs_manage(ctx, self.bot.load_extension, module)

    @cogs.command(name='unload', aliases=['u'])
    async def cogs_unload(self, ctx, module):
        """Unload an extension."""

        await ctx.message.add_reaction('\U00002935')  # :arrow_heading_down:
        await self._cogs_manage(ctx, self.bot.unload_extension, module)

    @cogs.group(name='reload', aliases=['r'], invoke_without_command=True)
    async def cogs_reload(self, ctx, module):
        """Reload an extension."""

        # :arrows_counterclockwise:
        await ctx.message.add_reaction('\U0001F504')
        await self._cogs_manage(ctx, self.bot.reload_extension, module)

    @cogs_reload.command(name='all')
    async def cogs_reload_all(self, ctx):
        """Reload all currently loaded extensions."""

        # :arrows_counterclockwise:
        await ctx.message.add_reaction('\U0001F504')
        loaded_extensions = list(self.bot.cogs.keys())
        for cog in loaded_extensions:
            await self._cogs_manage(ctx, self.bot.reload_extension, cog)

    async def _cogs_manage(self, ctx, method, module):
        """Helper method to load/unload/reload modules.
        This allows for more uniform handling (especially when exceptions
        occur) and less code repetition.
        """
        # Assume all cogs are in folder cogs/ in the bot's root
        if not module.startswith('cogs.'):
            module = f'cogs.{module}'

        # try it, and if an exception is raised, .error is called
        method(module)

    @cogs_load.after_invoke
    @cogs_unload.after_invoke
    @cogs_reload.after_invoke
    async def cogs_after_invoke(self, ctx):
        module = ctx.args[2]
        if not ctx.command_failed:
            print(f'Successfully {ctx.invoked_with}ed extension {module}.')
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @cogs_reload_all.after_invoke
    async def cogs_reload_all_after_invoke(self, ctx):
        if not ctx.command_failed:
            print('Successfully reloaded all extensions.')
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @cogs_load.error
    @cogs_unload.error
    @cogs_reload.error
    async def cogs_error(self, ctx, error):
        module = ctx.args[2]
        exc = f'{type(error).__name__}: {error}'
        print(f'Failed to {ctx.invoked_with} extension {module}.\n{exc}')
        await ctx.message.add_reaction('\N{CROSS MARK}')
        raise error

    @cogs_reload_all.error
    async def cogs_reload_all_error(self, ctx, error):
        exc = f'{type(error).__name__}: {error}'
        print('Failed to reload some extension.')
        await ctx.message.add_reaction('\N{CROSS MARK}')
        await ctx.send(exc)  # because there is lots of info
        raise error

    @commands.command()
    async def uptime(self, ctx):
        """Display the uptime in days, and the boot time."""

        # message = 'I have been online for {}! (Since {:%Y-%m-%d %H:%M:%S})'
        uptime_ = datetime.now() - self.bot.boot_time
        out_str = (f'I have been online for {uptime_.days} days! '
                   f'(Since {self.bot.boot_time:%c})')
        await ctx.send(out_str)

    @commands.command()
    async def susay(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send a message in the requested channel as the Bot.
        If in DMs, will send to any channel with the given ID.
        If in a guild, will only work in the current one.
        """

        await channel.send(message)
        if ctx.guild:
            await ctx.message.delete()

    @commands.command()
    async def sudo(self, ctx, who: discord.Member, *, command: str):
        """Run a command as another user.
        There is no need to include the prefix in the sudo'ed command,
        as it is added automatically.
        """
        msg = copy.copy(ctx.message)
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)
