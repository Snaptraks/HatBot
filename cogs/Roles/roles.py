import discord
import asyncio
from discord.ext import commands

import numpy as np

from ..utils.cogs import BasicCog


class Roles(BasicCog):
    """Collection of commands to add/remove a role."""

    def __init__(self, bot):
        super().__init__(bot)
        # do something else?

    @commands.command()
    async def roles(self, ctx):
        """List of available roles."""

        available = self.get_available_roles(ctx)
        blue_dia = ':small_blue_diamond:'
        content = 'Here are the roles you can `!join`/`!leave`:\n'
        content += '\n'.join([f'{blue_dia} {r}' for r in available])
        content += f'\nFor example: `!join {np.random.choice(available)}`'

        await ctx.send(content)

    # TODO: merge the join/leave commands to avoid duplicate code
    @commands.command()
    async def join(self, ctx, *, role: discord.Role = None):
        """Add yourself to a role.
        To select a role to add, enter the command and the role's name
        as the argument (case sentitive, please do not @mention the role).
        """
        if role is None:
            content = 'Please enter a role from `!roles`.'

        elif role not in self.get_available_roles(ctx):
            content = 'It is not a role you can join... :dizzy_face:'

        else:
            await ctx.author.add_roles(role)
            content = f'You joined the {role.name} role! :smile:'

        bot_msg = await ctx.send(content)
        await asyncio.sleep(30)
        await ctx.channel.delete_messages([ctx.message, bot_msg])

    @commands.command()
    async def leave(self, ctx, *, role: discord.Role = None):
        """Remove yourself from a role.
        To select a role to remove, enter the command and the role's name
        as the argument (case sentitive, please do not @mention the role).
        """
        if role is None:
            content = 'Please enter a role from `!roles`.'

        elif role not in self.get_available_roles(ctx):
            content = 'It is not a role you can leave... :dizzy_face:'

        else:
            await ctx.author.remove_roles(role)
            content = f'You left the {role} role! :frowning:'

        bot_msg = await ctx.send(content)
        await asyncio.sleep(30)
        await ctx.channel.delete_messages([ctx.message, bot_msg])

    @join.error
    @leave.error
    async def join_leave_error(self, ctx, error):
        """Error handling for the join and leave commands."""

        if isinstance(error, commands.BadArgument):
            bot_msg = await ctx.send('I did not find that role, I\'m sorry!')
            await asyncio.sleep(30)
            await ctx.channel.delete_messages([ctx.message, bot_msg])
        else:
            raise error

    def get_available_roles(self, ctx):
        everyone, *roles = ctx.guild.roles
        available = [r for r in roles if r.permissions == everyone.permissions]
        available = [r for r in available if not r.managed]
        available = [r for r in available if not r.hoist]
        # return the roles form top of list to bottom
        return sorted(available)[::-1]
