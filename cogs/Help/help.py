import copy
from datetime import timedelta

from discord.ext import commands
from fuzzywuzzy import fuzz, process

from .menus import DidYouMeanMenu
from ..utils.formats import pretty_print_timedelta


async def fuzzy_command_search(ctx, min_score=75):
    """Search for commands which are similar in name to the one invoked.
    Returns a maximum of 5 commands which must all be at least matched
    greater than ``min_score``.
    Inspired by https://github.com/Cog-Creators/Red-DiscordBot/redbot/core/utils/_internal_utils.py
    """
    term = ctx.invoked_with
    choices = ctx.bot.commands

    extracted = process.extract(term, choices, limit=5)

    matched_commands = []
    for cmd, score in extracted:
        if score < min_score:
            # exit early if we are lower than min_score
            break

        try:
            if await cmd.can_run(ctx):
                matched_commands.append(cmd)

        except commands.DisabledCommand:
            pass

    return matched_commands


class CustomHelpCommand(commands.DefaultHelpCommand):
    def add_command_formatting(self, command):
        """A utility function to format the non-indented block of commands
        and groups.
        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """
        super().add_command_formatting(command)

        cooldown = self.get_command_cooldown(command)
        if cooldown:
            self.paginator.add_line(f'Cooldown: {cooldown}', empty=True)

    def get_command_cooldown(self, command):
        """Retrieve the cooldown from the command, and format it in
        a nice string.
        """
        cooldown = command._buckets._cooldown

        if cooldown is not None:
            per = timedelta(seconds=cooldown.per)
            name = cooldown.type.name
            suffix = f'per {name}' if name != 'default' else 'globally'

            return (
                f'{cooldown.rate} time(s) '
                f'per {pretty_print_timedelta(per)} '
                f'{suffix}.'
                )

        else:
            return ''


class Help(commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand(
            dm_help=self._original_help_command.dm_help,
            )
        bot.help_command.cog = self
        self.bot = bot

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Error handler for general exceptions."""

        if isinstance(error, commands.CommandNotFound):
            maybe_cmds = await fuzzy_command_search(ctx)
            if maybe_cmds:
                maybe_cmd = maybe_cmds[0]
                menu = DidYouMeanMenu(maybe_cmd=maybe_cmd,
                                      clear_reactions_after=True)
                await menu.start(ctx)

            else:
                await ctx.send('I do not know of a command like that...')

        elif (ctx.command is not None
                and not hasattr(ctx.command, 'on_error')):
            raise error
