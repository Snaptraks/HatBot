import asyncio
import datetime
import pickle

import discord
from discord.ext import commands, tasks

from ..utils.cogs import BasicCog


def get_next_birthday(birthday_date):
    """Return a date object for the next birthday."""

    now = datetime.date.today()
    bday = birthday_date.replace(year=now.year)

    if (bday - now).total_seconds() < 0:
        bday = bday.replace(year=bday.year + 1)

    return bday


class Announcements(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

        try:
            with open('cogs/Announcements/birthday_dates.pkl', 'rb') as f:
                self.birthday_dates = pickle.load(f)

        except FileNotFoundError:
            self.birthday_dates = {}

    def cog_unload(self):
        super().cog_unload()

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
        pass


    @commands.group(aliases=['bday'])
    async def birthday(self, ctx):
        """Command group to register a birthday, and check the current
        registered date, if any.
        """
        if ctx.invoked_subcommand is None:
            try:
                bday = self.birthday_dates[ctx.author.id]

            except KeyError:
                bday = None

            if bday is not None:
                out_str = (
                    f'Your birthday is **{bday.strftime("%d of %B")}**. '
                    'If it is not correct, you can change it with '
                    )

            else:
                out_str = 'You can register your birthday with '

            out_str += (
                '`!birthday register <DD/MM/YYYY>` in a private '
                'message with me.'
                )

            await ctx.send(out_str)

    @birthday.command(name='register')
    async def birthday_register(self, ctx, date):
        """Register your birthday.
        Format DD/MM/YYYY. Only works in Private Message with the bot.
        """
        if ctx.author.id in self.birthday_dates:
            raise AlreadyRegistered(self.birthday_dates[ctx.author.id])

        yes_no = ('\U0001F44D', '\U0001F44E')  # thumbsup/down

        # will raise ValueError if there is a non-int
        date = [int(x) for x in date.split('/')]

        if len(date) != 3:
            raise ValueError

        bday = datetime.date(
            day=date[0],
            month=date[1],
            year=date[2],
            )

        msg = await ctx.send(
            f'Is your birthday **{bday.strftime("%d of %B")}**?'
            )
        for emoji in yes_no:
            await msg.add_reaction(emoji)

        def check(reaction, user):
            valid = user == ctx.author \
                and reaction.emoji in yes_no
            return valid

        reaction, user = await self.bot.wait_for(
            'reaction_add', check=check)

        if reaction.emoji == yes_no[0]:  # yes
            self.birthday_dates[ctx.author.id] = bday
            with open('cogs/Announcements/birthday_dates.pkl', 'wb') as f:
                pickle.dump(self.birthday_dates, f)

            time_until_bday = get_next_birthday(bday) - datetime.date.today()
            out_str = (
                'I saved your birthday! See you in '
                f'{time_until_bday.days} day(s)!'
                )

        elif reaction.emoji == yes_no[1]:  # no
            out_str = 'To enter again, just send the command again!'

        await ctx.send(out_str)

    @birthday.command(name='celebrate')
    @commands.has_permissions(mention_everyone=True)
    async def birthday_celebrate(self, ctx, member: discord.Member):
        """Celebrate a member's birthday!"""
        pass

    @birthday.command(name='delete')
    @commands.is_owner()
    async def birthday_delete(self, ctx, user: discord.User):
        """Delete a registered birthday.
        Only use it if someone entered the wrong date even after
        the confirmation message.
        """
        try:
            del self.birthday_dates[user.id]

        except KeyError:
            await ctx.send(f'User {user} ({user.id}) has not registered.')

        finally:
            await ctx.send(f'Successfully removed birthday for {user}')

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
            app_info = await self.bot.application_info()
            await ctx.send(
                'You already have a birthday registered '
                f'(**{error.original.date.strftime("%d of %B")}**)! '
                f'Contact {app_info.owner.mention} to change it.'
                )

        else:
            raise
