import asyncio
from datetime import datetime, timedelta
import json
import pickle

import numpy as np
import discord
from discord.ext import commands

from ..utils.cog import FunCog


def get_next_halloween():
    """Return the next Halloween day (Oct. 31).
    If Halloween in the current year is already passed, return
    the day for next year.
    """
    now = datetime.utcnow()
    halloween = datetime(year=now.year, month=10, day=31)

    if (halloween - now).total_seconds() < 0:
        halloween = datetime(
            year=halloween.year + 1,
            month=halloween.month,
            day=halloween.day,
            )

    return halloween


class Bag:
    """Class to represent the bad of a trick-or-treater."""

    def __init__(self):
        self.content = {}

    def __str__(self):
        candy_list = []
        for candy in self.content:
            candy_list += [candy] * self.content[candy]

        np.random.shuffle(candy_list)
        n_candy = len(candy_list)
        side = int(np.sqrt(n_candy))
        candy_array = np.array_split(candy_list, side)

        return '\n'.join(' '.join(row) for row in candy_array)

    def add(self, candy):
        try:
            self.content[candy] += 1

        except KeyError:
            self.content[candy] = 1


class Halloween(FunCog):
    """Cog for Halloween day!
    Enables trick-or-treating, with candy and a special trick!
    """

    def __init__(self, bot):
        self.bot = bot
        self.halloween_day = get_next_halloween()

        self.candies = [
            '\U0001F36B',  # :chocolate_bar:
            '\U0001F36C',  # :candy:
            '\U0001F36D',  # :lollipop:
            ]

        with open('cogs/Halloween/halloween_names.json', 'r') as f:
            names = json.load(f)
        first_names = names['first_names']
        names['first_names'] = first_names[0] + first_names[1]
        self.names = names

        try:
            with open('cogs/Halloween/halloween_data.pkl', 'rb') as f:
                self.data = pickle.load(f)

        except FileNotFoundError:
            self.data = {}

    def cog_check(self, ctx):
        valid = super().cog_check(ctx) \
            # and (datetime.utcnow().date() == self.halloween_day.date())
        return valid

    @commands.Cog.listener()
    async def on_message(self, message):
        """React with a random candy to some messages. The author can then
        collect the candy and add it to their Bag.
        """
        r = np.random.randint(20)
        # technically we should pass a `Context` object, so let's hope it's ok
        if self.cog_check(message) \
                and not message.content.startswith(self.bot.command_prefix) \
                and not message.author.bot:

            if r == 0:
                # for some reason numpy.str_ objects aren't picklable
                candy = str(np.random.choice(self.candies))

                def check(reaction, member):
                    valid = member == message.author \
                        and reaction.message.id == message.id \
                        and reaction.emoji == candy

                    return valid

                await message.add_reaction(candy)
                reaction, member = await self.bot.wait_for(
                    'reaction_add', check=check)

                self.add_to_bag(message.author, candy)

                async for member in reaction.users():
                    await reaction.remove(member)

    @commands.command()
    async def bag(self, ctx):
        try:
            bag = self.data[ctx.author.id]

        except KeyError:
            bag = None

        embed = discord.Embed(
            title=None,
            type='rich',
            color=0xEB6123,
            ).set_author(
                name=ctx.author.display_name,
                icon_url=ctx.author.avatar_url_as(static_format='png'),
            ).add_field(
                name='Content of your Halloween bag',
                value=bag,
            ).set_footer(
                text='Happy Halloween!'
            )

        # print(bag)
        await ctx.send(embed=embed)

    # @commands.cooldown(1, 15 * 60, commands.BucketType.member)
    @commands.command(name='trickortreat', aliases=['tot'])
    async def trick_or_treat(self, ctx):
        await ctx.trigger_typing()
        await asyncio.sleep(2)

        r = np.random.randint(10)
        if r == 0:
            # TRICK
            old_nickname = ctx.author.display_name
            new_nickname = await self.change_nickname(ctx.author)
            out_str = (
                "Aw, aren't you a cute one with your costume! "
                "I will see what I have for you...\n"
                "IT'S A TRICK! Hahaha! Poof your name is now "
                f'**{new_nickname}**! Happy Halloween! :jack_o_lantern:'
                )

            await ctx.send(out_str)
            await self.wait_and_revert(ctx.author, old_nickname)

        else:
            # TREAT
            candy = str(np.random.choice(self.candies))
            out_str = (
                "Aw, aren't you a cute one with your costume! "
                "I will see what I have for you...\n"
                f'I have some candy! Happy Halloween! {candy}'
                )

            await ctx.send(out_str)
            self.add_to_bag(ctx.author, candy)

    @commands.command()
    async def trick(self, ctx):
        """Change the author's nickname to a random one."""
        old_nickname = ctx.author.display_name
        new_nickname = await self.change_nickname(ctx.author)
        out_str = (
            'Oh, you want a trick? Well here you go!\n'
            f'Your name is now {new_nickname}! Happy Halloween! '
            ':jack_o_lantern:'
            )

        await ctx.send(out_str)
        await self.wait_and_revert(ctx.author, old_nickname)

    async def change_nickname(self, member):
        first = np.random.choice(self.names['first_names'])
        last = np.random.choice(self.names['last_names'])
        new_nickname = f'{first} {last}'

        try:
            await member.edit(nick=new_nickname, reason='Halloween Trick')

        except discord.Forbidden:
            # we don't have permissions, just ignore it
            pass

        return new_nickname

    async def wait_and_revert(self, member, old_nickname):
        """Wait 15 minutes and revert the member's display_name to
        what it was before the trick.
        """
        await asyncio.sleep(15 * 60)  # 15 minutes
        try:
            await member.edit(
                nick=old_nickname,
                reason='Revert Halloween Trick'
                )

        except discord.Forbidden:
            # we don't have permissions, just ignore it
            pass

    def add_to_bag(self, member, candy):
        try:
            self.data[member.id].add(candy)

        except KeyError:
            self.data[member.id] = Bag()
            self.data[member.id].add(candy)

        self._save_data()

    def _save_data(self):
        with open('cogs/Halloween/halloween_data.pkl', 'wb') as f:
            pickle.dump(self.data, f)
