import asyncio
from datetime import datetime

import discord
from discord.ext import commands

from ..utils.cogs import BasicCog
from ..utils.converters import Duration


class Reminders(BasicCog):
    """Cog to create reminders."""

    def __init__(self, bot):
        super().__init__(bot)
        self.reminders = {}

    @commands.group(aliases=['remindme'], invoke_without_command=True)
    async def remind(self, ctx, future: Duration, *, to_remind: str):
        """Send a reminder in the future about something.
        Syntax: `!remind 1h30m to take out the trash`. The future argument
        has to either be in one word, or in "quotes".
        """
        delay = future - datetime.utcnow()

        task = asyncio.create_task(self.remind_task(ctx, delay, to_remind))
        try:
            self.reminders[ctx.author.id].append(
                (future, to_remind, task)
                )
        except KeyError:
            self.reminders[ctx.author.id] = [
                (future, to_remind, task)
                ]

        await ctx.send(f'Ok! I will remind you {to_remind} in {delay}.')

    @remind.command(name='list')
    async def remind_list(self, ctx):
        """Print a list of active reminders."""

        self._clean_tasks(ctx.author.id)

        try:
            reminders = self.reminders[ctx.author.id]
        except KeyError:
            reminders = []

        out_str = ''
        for i, t in enumerate(reminders):
            future, to_remind, task = t
            delay = future - datetime.utcnow()
            delay_str = str(delay).split('.')[0]
            out_str += f'[{i + 1}] {to_remind} in {delay_str}.\n'

        if out_str == '':
            out_str = 'No active reminders.'

        await ctx.send(out_str)

    @remind.command(name='cancel')
    async def remind_cancel(self, ctx, index: int):
        """Cancel a scheduled reminder.
        The command takes the index of the reminder as shown in `remind list`.
        """
        try:
            reminders = self.reminders[ctx.author.id]
        except KeyError:
            reminders = []

        try:
            task = reminders[index - 1]
        except IndexError:
            out_str = f'No such reminder at index {index}.'
            task = None

        if task:
            task[2].cancel()
            out_str = f'Cancelled the reminder {task[1]}!'

        await ctx.send(out_str)

    @remind.command(name='clear')
    async def remind_clear(self, ctx):
        """Cancel all the current active reminders."""

        try:
            reminders = self.reminders[ctx.author.id]
        except KeyError:
            reminders = []

        for task in reminders:
            task[2].cancel()

        self._clean_tasks(ctx.author.id)

        await ctx.send('All active reminders cancelled.')

    @remind.command(name='me', hidden=True)
    async def remind_me(self, ctx, future: Duration, *, to_remind: str):
        """Accessibility command to call the `remindme` command as
        `remind me`.
        """
        await ctx.invoke(self.remind, future=future, to_remind=to_remind)

    async def remind_task(self, ctx, delay, to_remind):
        await asyncio.sleep(delay.total_seconds())
        await ctx.send(
            f'Hey {ctx.author.mention}, I needed to remind you {to_remind}'
            )

    def _clean_tasks(self, id):
        reminders = self.reminders[id]
        self.reminders[id] = [task for task in reminders if not task[2].done()]
