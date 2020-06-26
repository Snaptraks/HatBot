import asyncio
import datetime
import pickle

import discord
from discord.ext import commands, tasks

from ..utils.cogs import BasicCog
from . import menus


def get_next_birthday(date):
    """Return a date object for the next birthday."""

    now = datetime.date.today()
    bday = date.replace(year=now.year)

    if (bday - now).total_seconds() < 0:
        bday = bday.replace(year=bday.year + 1)

    return bday


def time_until_birthday(date):
    """Return the time until the date.
    Is always positive, if the current year's date is passed already,
    checks for next year.
    """
    time_until_bday = get_next_birthday(date) - datetime.date.today()
    return time_until_bday

class AlreadyRegistered(Exception):
    """Exception raised when a user already has a birthday registered."""

    def __init__(self, date):
        self.date = date


class Announcements(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

        self._create_tables.start()
        self.birthday_announcement.start()

    def cog_unload(self):
        super().cog_unload()
        self.birthday_announcement.cancel()

    @commands.Cog.listener(name='on_member_join')
    async def nth_member(self, member):
        """Announce when a new member is the nth member of the guild.
        Something like the (n * 50)th member sounds good.
        """
        each_n = 50
        member_count = len([m for m in member.guild.members if not m.bot])

        if member_count % each_n == 0:
            system_channel = member.guild.system_channel
            out_str = (
                f':tada: {member.display_name} is our {member_count}th '
                f'member! Welcome to the {member.guild.name} server!'
                )
            await system_channel.send(out_str)

    @commands.Cog.listener(name='on_message')
    async def birthday_confetti(self, message):
        """If a birthday is active, add birthday reactions to messages
        containing 'happy birthday'.
        """
        if message.guild is not None \
                and message.channel == message.guild.system_channel:
            if self.birthday_active:
                # Add a reaction to people wishing happy birthday
                trigger_words = [
                    'bday',
                    'birthday',
                    'birfday',  # because people are silly
                    'happy',
                    ]
                if any(word in message.content.lower() \
                        for word in trigger_words):
                    await message.add_reaction('\U0001F389')

    # DISCORD.PY > 1.3.0 ONLY
    # @tasks.loop(time=datetime.time(hour=0))
    @tasks.loop(hours=24)
    async def birthday_announcement(self):
        """Accounce the birthday of a member.
        Birthdays need to be registered by the member beforehand
        with the command `!birthday register <DD/MM/YYYY>`.
        """
        birthdays = await self._get_today_birthday()

        if len(birthdays) != 0:
            self.birthday_active = True

            for bday in birthdays:
                member = self.guild.get_member(bday['user_id'])
                asyncio.create_task(self.birthday_task(member))

        else:
            self.birthday_active = False

    async def birthday_task(self, member):
        msg = await self.guild.system_channel.send(
            f':birthday: It is the birthday of {member.mention} today! '
            "Let's all wish them a nice day!"
            )
        await msg.add_reaction('\U0001F389')
        await member.add_roles(self.birthday_role, reason='Birthday!')
        await asyncio.sleep(24 * 3600)  # 24 hours
        await member.remove_roles(self.birthday_role)

    @birthday_announcement.before_loop
    async def birthday_announcement_before(self):
        await self.bot.wait_until_ready()
        self.birthday_active = False
        # Hatventures Community
        self.guild = self.bot.get_guild(308049114187431936)
        # Bot Testing Server
        # self.guild = self.bot.get_guild(588171715960635393)

        self.birthday_role = discord.utils.get(
            self.guild.roles,
            name='Birthday Hat',
            )
        # ----temp fix until tasks rework comes out----
        t = datetime.datetime.utcnow().replace(hour=12, minute=0)
        if t < datetime.datetime.utcnow():
            t += datetime.timedelta(days=1)
        # await discord.utils.sleep_until(t)
        # --------------------------------------

    @commands.group(aliases=['bday'])
    async def birthday(self, ctx):
        """Command group to register a birthday.
        Check the current registered date, if any.
        """
        if ctx.invoked_subcommand is None:
            row = await self._get_member_birthday(ctx.author)

            if row is not None:
                bday = row['birthday']
                time_until_bday = time_until_birthday(bday)
                out_str = (
                    f'Your birthday is **{bday.strftime("%d of %B")}**. '
                    f'See you in {time_until_bday.days} day(s)!'
                    )

            else:
                out_str = (
                    'You can register your birthday with '
                    '`!birthday register <DD/MM/YYYY>` in a private '
                    'message with me.'
                    )

            await ctx.send(out_str)

    @birthday.command(name='register')
    @commands.dm_only()
    async def birthday_register(self, ctx, date):
        """Register your birthday.
        Format DD/MM/YYYY. Only works in Private Message with the bot.
        """
        already_registered = await self._is_already_registered(ctx.author)
        if already_registered:
            date = await self._get_member_birthday(ctx.author)
            raise AlreadyRegistered(date['birthday'])

        # will raise ValueError if there is a non-int
        date = [int(x) for x in date.split('/')]

        if len(date) != 3:
            raise ValueError

        bday = datetime.date(
            day=date[0],
            month=date[1],
            year=date[2],
            )

        confirm = await menus.ConfirmBirthday(
            f'Is your birthday **{bday.strftime("%d of %B")}**?').prompt(ctx)

        if confirm:  # yes
            await self._save_birthday(ctx.author, bday)

            time_until_bday = time_until_birthday(bday)
            out_str = (
                'I saved your birthday! See you in '
                f'{time_until_bday.days} day(s)!'
                )

        else:  # no
            out_str = 'To enter again, just send the command again!'

        await ctx.send(out_str)

    @birthday_register.error
    async def birthday_register_error(self, ctx, error):
        """In the case of an error, send a helpful message."""

        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.author.send('You can only register a birthday in DMs.')

        elif isinstance(error, commands.MissingRequiredArgument) \
                or isinstance(error.original, ValueError):

            await ctx.send(
                'Please enter your birthday in a '
                '`DD/MM/YYYY` format.'
                )

        elif isinstance(error.original, AlreadyRegistered):
            await ctx.send(
                'You already have a birthday registered '
                f'(**{error.original.date.strftime("%d of %B")}**)! '
                f'Contact {self.bot.owner.mention} to change it.'
                )

        else:
            raise error

    @birthday.command(name='celebrate')
    @commands.has_permissions(mention_everyone=True)
    async def birthday_celebrate(self, ctx, member: discord.Member):
        """Celebrate a member's birthday!"""

        self.birthday_active = True
        asyncio.create_task(self.birthday_task(member))

        already_registered = await self._is_already_registered(member)

        if not already_registered:
            # send a message to member to ask if they would like to register
            today = datetime.date.today().strftime('%d/%m/%Y')
            out_str = (
                'It seems it is your birthday today! Sadly I did not know '
                'and someone just told me. If you would like me to remember '
                'for next time please enter the command '
                f'`!birthday register {today}`! And happy birthday!'
                )
            await member.send(out_str)

    @birthday.command(name='delete')
    @commands.is_owner()
    async def birthday_delete(self, ctx, user: discord.User):
        """Delete a registered birthday.
        Only use it if someone entered the wrong date even after
        the confirmation message.
        """
        await self._delete_birthday(user)
        await ctx.send(f'Successfully removed birthday for {user}')

    @tasks.loop(count=1)
    async def _create_tables(self):
        """Create the necessary DB tables if they do not exist."""

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS announcements_birthday(
                user_id  INTEGER PRIMARY KEY,
                birthday DATE
                )
            """
            )

        await self.bot.db.commit()

    async def _get_member_birthday(self, member):
        """Get a member's birthday."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM announcements_birthday
                 WHERE user_id = :user_id
                """,
                {'user_id': member.id}
                ) as c:
            row = await c.fetchone()

        return row

    async def _get_today_birthday(self):
        """Return a list of today's birthdays.
        The list is empty is there is none.
        """
        async with self.bot.db.execute(
                """
                SELECT *
                  FROM announcements_birthday
                """
                ) as c:
            rows = await c.fetchall()

        birthdays = []
        today = datetime.date.today()
        for row in rows:
            date = row['birthday']
            if (date.day, date.month) == (today.day, today.month):
                birthdays.append(row)

        return birthdays

    async def _is_already_registered(self, member):
        """Verify if a member has registered a birthday already."""

        async with self.bot.db.execute(
                """
                SELECT EXISTS (SELECT 1
                                 FROM announcements_birthday
                                WHERE user_id = :user_id)
                """,
                {'user_id': member.id}
                ) as c:
            row = await c.fetchone()

        return bool(row[0])

    async def _save_birthday(self, member, birthday):
        """Save the birthday to the database."""

        await self.bot.db.execute(
            """
            INSERT INTO announcements_birthday
            VALUES (:user_id, :birthday)
            """,
            {'user_id': member.id, 'birthday': birthday}
            )
        await self.bot.db.commit()

    async def _delete_birthday(self, member):
        """Remove the member's birthday from the database."""

        await self.bot.db.execute(
            """
            DELETE FROM announcements_birthday
             WHERE user_id = :user_id
            """,
            {'user_id': member.id}
            )
        await self.bot.db.commit()
