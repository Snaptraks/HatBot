from typing import Callable

import discord
from discord import app_commands
from discord.ext import commands


class NotOwner(app_commands.CheckFailure):
    """Exception raised when the message author is not the owner of the bot.

    This inherits from app_commands.CheckFailure
    """


def has_role_or_above[T](item) -> Callable[[T], T]:
    """A check decorator that checks if the member invoking the command
    has their top role equal or above the role specified via the name
    or ID specified.

    If a string is specified, you must give the exact name of the role,
    including caps and spelling.

    If an integer is specified, you must give the exact snowflake ID
    of the role.
    """

    def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage()

        if isinstance(item, int):
            role = discord.utils.get(ctx.guild.roles, id=item)

        else:
            role = discord.utils.get(ctx.guild.roles, name=item)

        if role is None:
            raise commands.MissingRole(item)

        assert isinstance(ctx.author, discord.Member)
        return role <= ctx.author.top_role

    return commands.check(predicate)


async def _is_owner(interaction: discord.Interaction) -> bool:
    """Interaction based version of the discord.ext.commands.Bot.is_owner method."""

    if isinstance(interaction.client, commands.Bot):
        return await interaction.client.is_owner(interaction.user)

    else:
        app = await interaction.client.application_info()

        if app.team:
            ids = {m.id for m in app.team.members}
            return interaction.user.id in ids
        else:
            return interaction.user.id == app.owner.id


def is_owner[T]() -> Callable[[T], T]:
    """A check decorator that checks if the user invoking the command
    is the owner of the bot.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        if not await _is_owner(interaction):
            raise NotOwner("You do not own this bot.")
        return True

    return app_commands.check(predicate)
