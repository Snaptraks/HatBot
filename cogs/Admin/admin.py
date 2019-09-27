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
        # self.bot = bot
        self.boottime = datetime.now()

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(aliases=['stop', 'quit', 'exit'])
    async def kill(self, ctx):
        """Stop the bot. Does not restart it."""

        await self.bot.logout()

    @commands.command()
    async def cogs(self, ctx):
        """List current active cogs."""

        out_str = f'Active Cogs:\n`{", ".join(self.bot.cogs.keys())}`'
        await ctx.send(out_str)

    @commands.command()
    async def load(self, ctx, module):
        """Load a module."""

        try:
            self.bot.load_extension(module)
        except Exception as e:
            exc = f'{type(e).__name__}: {e}'
            print(f'Failed to load extension {module}\n{exc}')
            await ctx.message.add_reaction('\N{CROSS MARK}')
            raise e
        else:
            print(f'Successfully loaded extension {module}')
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    async def unload(self, ctx, module):
        """Unload a module."""

        try:
            self.bot.unload_extension(module)
        except Exception as e:
            exc = f'{type(e).__name__}: {e}'
            print(f'Failed to unload extension {module}\n{exc}')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        else:
            print(f'Successfully unloaded extension {module}')
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    async def reload(self, ctx, module):
        """Reload a module."""

        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            exc = f'{type(e).__name__}: {e}'
            print(f'Failed to reload extension {module}\n{exc}')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        else:
            print(f'Successfully reloaded extension {module}')
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command()
    async def uptime(self, ctx):
        """Display the uptime in days, and the boot time."""

        # message = 'I have been online for {}! (Since {:%Y-%m-%d %H:%M:%S})'
        uptime_ = datetime.now() - self.boottime
        out_str = (f'I have been online for {uptime_.days} days! '
                   f'(Since {self.boottime:%c})')
        await ctx.send(out_str)

    @commands.command()
    async def susay(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send a message in the requested channel as the Bot."""

        await channel.send(message)
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
