import discord
from discord.ext import commands


def has_role_above(item):
    """A check decorator that checks if the member invoking the command
    has their top role equal or above the role specified via the name
    or ID specified.

    If a string is specified, you must give the exact name of the role,
    including caps and spelling.

    If an integer is specified, you must give the exact snowflake ID
    of the role.
    """
    def predicate(ctx):
        if not isinstance(ctx.channel, discord.abc.GuildChannel):
            raise commands.NoPrivateMessage()

        if isinstance(item, int):
            role = discord.utils.get(ctx.author.roles, id=item)

        else:
            role = discord.utils.get(ctx.author.roles, name=item)

        if role is None:
            raise commands.MissingRole(item)

        return role <= ctx.author.top_role

    return commands.check(predicate)
