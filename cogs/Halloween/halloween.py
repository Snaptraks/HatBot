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
        super().__init__(bot)
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

        self.bot.loop.create_task(self.load_data())
        self.bg_tasks = [
            self.bot.loop.create_task(self.start_halloween_event()),
            self.bot.loop.create_task(self.halloweenify()),
            ]

    def cog_check(self, ctx):
        valid = super().cog_check(ctx) \
            # and (datetime.utcnow().date() == self.halloween_day.date())
        return valid

    def cog_unload(self):
        super().cog_unload()
        for task in self.bg_tasks:
            task.cancel()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.add_reaction('\U0000231B')  # :hourglass:

        else:
            raise

    async def load_data(self):
        await self.bot.wait_until_ready()
        guild = discord.utils.get(
            self.bot.guilds,
            # name='Hatventures Community',
            name='Bot Testing Server',
            )
        channel = discord.utils.get(
            guild.channels,
            # name='hatbot-land',
            name='bot-0',
            )

        self.guild = guild
        self.channel = channel

    async def halloweenify(self):
        """Change the Bot's profile picture and guild nickname a week before
        Halloween to something sp00py. Reset everything the day after
        Halloween.
        """
        await self.bot.wait_until_ready()
        week_before = self.halloween_day - timedelta(weeks=1)
        day_after = self.halloween_day + timedelta(days=1)
        bot_member = self.guild.get_member(self.bot.user.id)

        # change pfp and nickname
        delay = week_before - datetime.utcnow()
        avatar = discord.File('HVClogoHalloween3.png')
        await asyncio.sleep(delay.total_seconds())
        await self.bot.user.edit(avatar=avatar.fp.read())
        await bot_member.edit(nick='BatBot')

        # reset pfp and nickname to normal
        delay = day_after - datetime.utcnow()
        avatar = discord.File('HVClogo.png')
        await asyncio.sleep(delay.total_seconds())
        await self.bot.user.edit(avatar=avatar.fp.read())
        await bot_member.edit(nick=None)

    async def start_halloween_event(self):
        """Announce the beginning of the Halloween event, with some help
        about the new commands.
        """
        await self.bot.wait_until_ready()
        delay = self.halloween_day - datetime.utcnow()
        out_str = (
            'Happy Halloween @everyone! Today we have a special event where '
            'you can collect candy from `!trickortreat`ing or simply '
            'having discussions here on the Discord server. '
            'So if you see a candy popping up after one of your messages, '
            'be sure to pick it up!\n\n'
            'Be warned though, I am a playful being and might trick you '
            'while you are trick-or-treating! '
            'If you are the adventurous type, you can ask for a `!trick` '
            'directly and I will cast my magic upon you!\n\n'
            'Once you have collected many candies, you can check your `!bag` '
            'to see now many you collected! Happy trick-or-treating!'
            )
        await asyncio.sleep(delay.total_seconds())
        self.announcement_message = await self.channel.send(out_str)

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
        """Show the content of your Halloween bag."""

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

    @commands.cooldown(1, 15 * 60, commands.BucketType.member)
    @commands.command(name='trickortreat', aliases=['tot'])
    async def trick_or_treat(self, ctx):
        """Get a candy, or a trick!"""

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

    @commands.cooldown(1, 15 * 60, commands.BucketType.member)
    @commands.command()
    async def trick(self, ctx):
        """Change the author's nickname to a random one."""
        await ctx.trigger_typing()
        await asyncio.sleep(2)

        old_nickname = ctx.author.display_name
        new_nickname = await self.change_nickname(ctx.author)
        out_str = (
            'Oh, you want a trick? Well here you go!\n'
            f'Your name is now **{new_nickname}**! Happy Halloween! '
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
