import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from ..utils.cogs import BasicCog
from ..utils.converters import Duration
from ..utils.formats import pretty_print_timedelta
from . import menus


def make_reminder_embed(reminder, member):
    """Make the Embed when a reminder is saved or sent."""

    now = datetime.utcnow()
    since = now - reminder['created_at']
    until = reminder['future'] - now
    # fix rounding issues
    until += timedelta(milliseconds=200)

    if until > timedelta(seconds=1):
        remaining = pretty_print_timedelta(until)
    else:
        remaining = "Now!"

    if since > timedelta(seconds=1):
        created = (
            f"[{pretty_print_timedelta(since)} ago]"
            f"({reminder['jump_url']})"
        )
    else:
        created = f"[Here]({reminder['jump_url']})"

    embed = discord.Embed(
        color=discord.Color.blurple(),
        description=reminder['message']
    ).set_author(
        name=f"Reminder for {member.display_name}",
        icon_url=member.avatar_url,
    ).add_field(
        name="Remaining",
        value=remaining,
    ).add_field(
        name="Created",
        value=created,
    )

    return embed


class Reminders(BasicCog):
    """Cog to create reminders."""

    def __init__(self, bot):
        super().__init__(bot)

        self._have_reminder = asyncio.Event()
        self._next_reminder = None
        self._create_tables.start()
        self._reminders_task = bot.loop.create_task(self.start_reminders())

    def cog_unload(self):
        super().cog_unload()
        self._reminders_task.cancel()

    @commands.group(aliases=["remindme", "reminder", "reminders", "r"],
                    invoke_without_command=True)
    async def remind(self, ctx, future: Duration, *, to_remind: str):
        """Send a reminder in the future about something.
        Syntax: `!remind 1h30m to take out the trash`. The future argument
        has to either be in one word, or in "quotes".
        """

        reminder = await self._save_reminder(ctx)

        await ctx.reply(
            "Ok! Here is your reminder:",
            embed=make_reminder_embed(reminder, ctx.author),
        )

        if self._next_reminder and future < self._next_reminder['future']:
            # stop the task and run it again to get the latest reminder
            self._restart_reminders()

    @remind.error
    async def remind_error(self, ctx, error):
        """Error handling for the remind command.
        Does not handle for subcommands.
        """
        if isinstance(error, commands.BadArgument):
            await ctx.reply(error)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"You are missing argument {error.param.name}")

        elif isinstance(error, commands.ConversionError):
            await ctx.reply(
                "I am sorry, there was an error. "
                "Maybe try a shorter amount of time?"
            )
        else:
            raise error

    @remind.command(name="active", aliases=["a"])
    @commands.is_owner()
    async def remind_active(self, ctx):
        if self._reminders_task.done():
            await ctx.reply(
                "Task is done with exception: "
                f"{self._reminders_task.exception()}"
            )
            self._reminders_task.print_stack()
        else:
            await ctx.reply(self._reminders_task)

    @remind.command(name="next", aliases=["n"])
    @commands.is_owner()
    async def remind_next(self, ctx):
        await ctx.reply(dict(self._next_reminder))

    @remind.command(name="list")
    async def remind_list(self, ctx):
        """Print a list of active reminders."""

        reminders = await self._get_reminders(ctx.author)

        if len(reminders) == 0:
            embed = discord.Embed(
                color=discord.Color.blurple(),
                title=f"Reminders for {ctx.author.display_name}",
                description="No active reminders",
            )
            await ctx.reply(embed=embed)
            return

        menu = menus.ReminderMenu(
            source=menus.ReminderSource(reminders),
            clear_reactions_after=True,
        )
        to_cancel = await menu.prompt(ctx)

        await self._delete_reminders(to_cancel)

        if self._next_reminder['rowid'] in to_cancel:
            # stop the task and run it again to get the latest reminder
            self._restart_reminders()

    @remind.command(name="me", hidden=True)
    async def remind_me(self, ctx, future: Duration, *, to_remind: str):
        """Accessibility command to call the `remindme` command as
        `remind me`.
        """
        await ctx.invoke(self.remind, future=future, to_remind=to_remind)

    async def start_reminders(self):
        """Task to start the reminders. Only wait for one at a time."""

        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            reminder = await self._get_next_reminder()

            if reminder is not None:
                self._have_reminder.set()
                self._next_reminder = reminder
                await self.send_reminder(reminder)

            else:
                self._have_reminder.clear()
                await self._have_reminder.wait()

    async def send_reminder(self, reminder):
        """Send the reminder to the channel after deleting it
        from the DB.
        """
        await discord.utils.sleep_until(reminder['future'])
        channel = await self.bot.fetch_channel(reminder['channel_id'])
        user = self.bot.get_user(reminder['user_id'])
        await channel.send(
            f"Hey {user.mention}! Here is your reminder:",
            embed=make_reminder_embed(reminder, user),
        )

        await self._delete_single_reminder(reminder)

    def _restart_reminders(self):
        """Helper function to restart the reminders task."""

        self._reminders_task.cancel()
        self._reminders_task = asyncio.create_task(self.start_reminders())

    @tasks.loop(count=1)
    async def _create_tables(self):
        """Create the necessary DB tables if they do not exist."""

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders_reminder(
                channel_id INTEGER   NOT NULL,
                created_at TIMESTAMP NOT NULL,
                future     TIMESTAMP NOT NULL,
                jump_url   TEXT      NOT NULL,
                message    TEXT      NOT NULL,
                user_id    INTEGER   NOT NULL
            )
            """
        )

        await self.bot.db.commit()

    async def _delete_single_reminder(self, reminder):
        """Delete one reminder."""

        await self._delete_reminders([reminder['rowid']])

    async def _delete_reminders(self, rowids):
        """Delete the reminders."""

        await self.bot.db.executemany(
            """
            DELETE FROM reminders_reminder
             WHERE rowid = :rowid
            """,
            [{'rowid': rowid} for rowid in rowids]
        )

        await self.bot.db.commit()

    async def _get_reminders(self, member):
        """Get the reminders of the given member."""

        async with self.bot.db.execute(
                """
                SELECT rowid, *
                  FROM reminders_reminder
                 WHERE user_id = :user_id
                 ORDER BY future
                """,
                {'user_id': member.id}
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_next_reminder(self):
        """Get the reminder that needs to happen first."""

        async with self.bot.db.execute(
                """
                SELECT rowid, *
                  FROM reminders_reminder
                 ORDER BY future
                 LIMIT 1
                """
                # WHERE future < STRFTIME('%Y-%m-%d %H:%M:%f')
        ) as c:
            row = await c.fetchone()

        return row

    async def _save_reminder(self, ctx):
        """Save the provided reminder to the DB."""

        channel_id = ctx.channel.id
        created_at = ctx.message.created_at
        future = ctx.args[2]
        jump_url = ctx.message.jump_url
        message = discord.utils.escape_mentions(ctx.kwargs['to_remind'])
        user_id = ctx.author.id

        async with self.bot.db.execute(
                """
                INSERT INTO reminders_reminder
                VALUES (:channel_id,
                        :created_at,
                        :future,
                        :jump_url,
                        :message,
                        :user_id)
                """,
                {
                    'channel_id': channel_id,
                    'created_at': created_at,
                    'future': future,
                    'jump_url': jump_url,
                    'message': message,
                    'user_id': user_id,
                }
        ) as c:
            lastrowid = c.lastrowid
        await self.bot.db.commit()

        async with self.bot.db.execute(
                """
                SELECT rowid, *
                  FROM reminders_reminder
                 WHERE rowid = :lastrowid
                """,
                {'lastrowid': lastrowid}
        ) as c:
            row = await c.fetchone()

        self._have_reminder.set()
        return row
