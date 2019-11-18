from datetime import timedelta

from discord.ext import commands

from ..utils.formats import pretty_print_timedelta

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
            bucket_type_name = cooldown.type.name
            per = timedelta(seconds=cooldown.per)

            if bucket_type_name == 'default':
                bucket_type_name = 'global'

            return (
                f'{cooldown.rate} time(s) '
                f'per {pretty_print_timedelta(per)} '
                f'per {bucket_type_name}.'
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
