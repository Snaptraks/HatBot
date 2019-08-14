import asyncio
import json
import pickle
import re

import discord
from discord.ext import commands
from discord.utils import escape_markdown as escape
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from ..utils.datetime_modulo import datetime
from datetime import timedelta
from ..utils.cog import FunCog


FEESH_STATS = 'cogs/Feesh/feesh_stats.pkl'


class Feesh(FunCog):
    """Cog for the periodic feesh, and the stats."""

    def __init__(self, bot):
        super().__init__(bot)
        try:
            self.stats = pkl_load(FEESH_STATS)
        except FileNotFoundError:
            self.stats = {'members': {}, 'total': 0}

        # Tasks
        self.remove_tasks = {}

        # Init feesh emoji and messaging channel.
        self.bot.loop.create_task(self.load_data())

        # Background tasks
        self.bg_tasks = [
            self.bot.loop.create_task(self.periodic_feesh(timedelta(hours=4))),
            ]

    def cog_unload(self):
        super().cog_unload()
        for task in self.bg_tasks:
            task.cancel()  # Cancel background tasks

    async def load_data(self):
        """Loads data from the guild, such as channel and emoji"""
        await self.bot.wait_until_ready()
        guild = discord.utils.get(
            self.bot.guilds, name='Hatventures Community'
            )
        channel = discord.utils.find(
            lambda c: c.name.startswith('hatbot'),
            guild.channels
            )
        feesh = discord.utils.get(guild.emojis, name='feesh')

        self.guild = guild
        self.channel_msg = channel
        self.feesh_emoji = feesh

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Updates feesh stats when a new member joins."""
        try:
            # Cancel the removal of feesh task
            # This has no effect if the member rejoins after more than 24 hours
            self.remove_tasks[member.id].cancel()
            del self.remove_tasks[member.id]

        except KeyError:
            # The member has no removal tasks, check if he joined before
            try:
                # Mark member as in guild again
                self.stats['members'][member.id]['is_member'] = True
            except KeyError:
                # Create new stats entry
                ustats = {
                    'amount': 0,
                    'bot_given': 0,
                    'last_nickname': member.display_name,
                    'is_member': True,
                    }
                self.stats['members'][member.id] = ustats

                pkl_dump(self.stats, FEESH_STATS)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Clears the feesh of a member.
        Allows other people to collect it."""
        # py 3.7
        task = asyncio.create_task(self.wait_and_remove_feesh(member))
        self.remove_tasks[member.id] = task

    async def wait_and_remove_feesh(self, member):
        """Waits for 24 hours, then transfers the feesh to the bot."""
        try:
            print(f'{member} left. Waiting 24 hours.')
            await asyncio.sleep(24 * 3600)  # sleep for 24 hours

            amount = self.stats['members'][member.id]['amount']
            self.stats['members'][member.id]['is_member'] = False
            self.feesh_stats(self.bot.user, member, amount=amount)

        except KeyError:
            print('member did not have feesh entry.')

        except asyncio.CancelledError:
            print('member came back, did not lose their feesh.')

    async def periodic_feesh(self, period):
        """Sends a feesh to a random member every 'period'.

        Input
        -----
        period : timedelta
            Period of the message.
        """
        if not isinstance(period, timedelta):
            raise ValueError(f'period {period:f} is not timedelta')

        await self.bot.wait_until_ready()

        cog_level = self.bot.get_cog('Levels')

        while not self.bot.is_closed():

            t = datetime.now()
            wait = period - (t % period)
            await asyncio.sleep(wait.total_seconds())

            # members_list = [m for m in self.guild.members if is_not_offline(m)]
            # no need to be online if we use Levels
            members_list = self.guild.members

            won = []
            for m in members_list:
                try:
                    won.append(self.stats['members'][m.id]['bot_given'])
                except KeyError as e:
                    won.append(0)
            won = np.asarray(won)

            # PROGRESSIVE WEIGHTS - LINEAR
            # If the member got 0 feesh, the weight is maximal (1 before
            # normalization), if the member has the most feesh of the members
            # online, the weight is minimal (0.1 before normalization).
            # We solve the matrix system A * x = b.
            # PROGRESSIVE WEIGHTS - EXPONENTIAL
            # If the member has the less feesh, give weight of 1 before
            # normalization, with exponential decrease for each more feesh.
            # UNIFORM WEIGHTS - LEVELS
            # If the member has a (positive) non-zero amount of exp,
            # then they have a chance. It is the same for all members
            # with a valid amount of exp, normalized

            method = 'level'
            if method == 'linear':
                a = np.array([[0, 1], [won.max(), 1]])
                b = np.array([1, 0.1])
                x = np.linalg.solve(a, b)
                w = np.poly1d(x)  # function to give the weights
                weights = w(won)
            elif method == 'exponential':
                weights = np.exp(-(won - won.min()))
            elif method == 'level':
                weights = []
                for m in members_list:
                    try:
                        exp = cog_level.data[m.id].exp
                        # 1 if above 0, 0 if equal to 0, never under 0 anyway
                        weights.append(np.sign(exp))
                    except KeyError:
                        # if the member doesn't have a levels entry, it is 0
                        weights.append(0)
                weights = np.asarray(weights, dtype='float')

            if weights.sum() == 0:
                # if the sum of the weights is 0, don't use weights
                # to avoid a division by 0 below.
                weights = None
            else:
                # normalize the weights, np.rancom.choice expects the
                # sum to be 1
                weights /= weights.sum()

            if len(members_list) == 0:
                out_str = (
                    'No one is online, I guess I\'ll have a snack! '
                    ':sushi:'
                    )
                await self.channel_msg.send(out_str)
            else:
                winner = np.random.choice(members_list, p=weights)
                out_str = f'{winner.display_name} got a feesh !'
                out_str = (
                    f'{escape(winner.display_name)} got a '
                    f'{self.feesh_emoji} !'
                    )

                # 1337 feesh
                if self.stats['total'] == 1337 - 1:
                    out_str = (
                        f'{leet(winner.display_name)} '
                        f'({winner.display_name}) 607 4 '
                        f'{self.feesh_emoji}'
                        )

                await self.channel_msg.send(out_str)

                # statistics
                self.feesh_stats(member=winner, amount=1)

    @commands.group()
    async def feesh(self, ctx):
        """Gives statistics on the amount of feesh given."""
        if ctx.invoked_subcommand is None:

            member = ctx.author
            channel = ctx.channel

            total = self.stats['total']

            try:
                amount = self.stats['members'][member.id]['amount']
            except KeyError as e:
                amount = 0

            out_str = (
                f'{total} {self.feesh_emoji} were given in total, '
                f'{escape(member.display_name)} has {amount}.'
                )

            await channel.send(out_str)

    @feesh.command(name='give')
    async def _give(self, ctx, member: discord.Member, amount=1):
        """Give a feesh from your feesh to a member."""
        donor = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        # Checks to see if the member to receive a feesh is valid
        if donor == member:
            out_str = f'But... You can\'t give yourself a {self.feesh_emoji} !'

        elif member.bot:
            out_str = 'I\'m touched, but I cannot accept this :flushed:'

        else:  # It is valid:
            try:
                x = self.stats['members'][donor.id]['amount']

            except KeyError:
                x = 0

            if amount < 1:
                out_str = 'Nice try.'

            elif x - amount < 0:
                out_str = (
                    'That\'s very nice of you, but you don\'t '
                    f'have enough {self.feesh_emoji}!'
                    )

            else:
                self.feesh_stats(member=member, donor=donor, amount=amount)
                out_str = (
                    f'You gave {amount} {self.feesh_emoji} to '
                    f'{escape(member.display_name)}. Yay!'
                    )

        await channel.send(out_str)

    @feesh.command(name='bomb', hidden=True, aliases=['yeet'])
    async def _bomb(self, ctx):
        """Sends all your feesh to random online members (1 per member)."""

        bomb = '\U0001F4A3'  # bomb
        cancel = '\U000026D4'  # no_entry
        author = ctx.author
        channel = ctx.channel
        message = ctx.message

        if self.stats['members'][author.id]['amount'] == 0:
            out_str = f'You have no {self.feesh_emoji} though.'
            await channel.send(out_str)
            return

        await message.add_reaction(cancel)
        await message.add_reaction(bomb)

        def check(reaction, member):
            return member == author and \
                reaction.message == message and \
                reaction.emoji in (bomb, cancel)

        try:
            reaction, member = await self.bot.wait_for(
                'reaction_add', check=check, timeout=60)
        except asyncio.TimeoutError:
            out_str = 'You didn\'t confirm quickly enough, I must cancel.'
            await channel.send(out_str)
            return

        def isvalid(m):
            return is_not_offline(m) and m != author
        members_list = [m for m in self.guild.members if isvalid(m)]

        if reaction.emoji == cancel:
            out_str = 'Abort mission!'
            await channel.send(out_str)

        elif reaction.emoji == bomb:
            amount = self.stats['members'][author.id]['amount']
            amount = min(amount, len(members_list))
            targets = np.random.choice(
                members_list, size=amount, replace=False)

            out_str = ':tired_face:  :triumph:  :boom:\n'
            out_str += feesh_wall().format(self.feesh_emoji)

            pm_str = 'You sent a feesh to\n```\n' + \
                '\n'.join([m.display_name for m in targets]) + \
                '\n```'

            await author.send(pm_str)
            await channel.send(out_str)

            for member in targets:
                self.feesh_stats(member=member, donor=author, amount=1)

    @feesh.command(name='top')
    async def _top(self, ctx):
        """Displays the member(s) with the most feesh."""

        L = []
        for x in self.stats['members']:
            if x == 460499306223239188:
                continue  # Exclude HatBot
            L.append((x, self.stats['members'][x]['amount']))

        L = np.array(L, dtype=[('ID', '<i8'), ('amount', '<i8'), ])
        top_amount = L['amount'].max()
        temp = L[L['amount'] == top_amount]
        top_members = []

        for u in temp:
            member = discord.utils.get(ctx.message.guild.members, id=u['ID'])
            if member:
                top_members.append(member.display_name)
            else:
                top_members.append(
                    self.stats['members'][u['ID']]['last_nickname']
                    )

        plural = 's' if len(top_members) > 1 else ''
        out_str = (
            f'Member{plural} with the most {self.feesh_emoji} '
            f'(**{top_amount}**):\n'
            )
        out_str += '```\n' + '\n'.join(top_members) + '\n```'

        await ctx.channel.send(out_str)

    @commands.cooldown(1, 24 * 3600, commands.BucketType.member)
    @feesh.command(name='steal', hidden=True, aliases=['yoink'])
    async def _steal(self, ctx, target: discord.Member):
        """Attempts to steal a feesh from a given member.
        This is a secret command! Shhhhhhhhh..."""

        if ctx.invoked_with == 'yoink':
            _ing = 'yoinking'
            _ed = 'yoinked'
        else:
            _ing = 'stealing'
            _ed = 'stole'

        thief = ctx.author
        channel = ctx.channel

        if thief == target:
            out_str = f'You cannot {ctx.invoked_with} from yourself.'
            await channel.send(out_str)
            raise ValueError(f'Tried to steal from self')

        # elif target.bot:
            # out_str = 'Please, I have no {}!'.format(self.feesh_emoji)
            # await channel.send(out_str)
            # raise ValueError('Tried to steal from the bot')

        else:
            # random typing delay
            await channel.trigger_typing()
            r = np.random.rand()  # [0, 1)
            t = 2.5 * r + 0.5  # [0.5, 2)
            await asyncio.sleep(t)

            feesh_thief = self.stats['members'][thief.id]['amount']
            feesh_target = self.stats['members'][target.id]['amount']
            feesh_diff = feesh_target - feesh_thief

            if feesh_target == 0:
                out_str = (
                    f'That person has no {self.feesh_emoji}, '
                    f'you can\'t {ctx.invoked_with} from them.'
                    )
                await channel.send(out_str)
                raise ValueError('Target has no feesh')

            def odds(x):
                if x <= 0:
                    return 1
                else:
                    # x > 0
                    # 1 to 0.5
                    return (np.exp(-x / 2) + 1) / 2

            fail = odds(feesh_diff)

            drop = (1 - fail) / 2  # success = 1. - fail - drop

            if target.id == 460499306223239188:  # HatBot
                if feesh_target > 0:
                    fail = 1 / 4
                    drop = fail

            r = np.random.rand()
            if r < fail:
                # fail
                out_str = f'You failed at {_ing} a {self.feesh_emoji}.'
                await channel.send(out_str)
            elif r < fail + drop:
                # drop
                if feesh_thief != 0:
                    out_str = [
                        (f'In your haste, you dropped a {self.feesh_emoji} '
                         'of your own!\n'),
                        'Who will get it?'
                        ]
                    msg = await channel.send(''.join(out_str))
                    # reaction
                    await msg.add_reaction(self.feesh_emoji)

                    # wait for reaction from not thief
                    def check(reaction, member):
                        return member != thief and \
                            not member.bot and \
                            reaction.message.id == msg.id and \
                            reaction.emoji == self.feesh_emoji

                    reaction, member = await self.bot.wait_for(
                        'reaction_add', check=check)

                    # take a feesh from thief, give to member
                    out_str = out_str[0] + \
                        f'{escape(member.display_name)} took it!'
                    await msg.edit(content=out_str)
                    # edit stats
                    self.feesh_stats(member, donor=thief, amount=1)

                else:
                    out_str = (
                        f'You failed to {ctx.invoked_with} and '
                        'got caught! THIEF!'
                        )
                    await channel.send(out_str)
                    try:
                        # change nickname
                        old_display_name = thief.display_name
                        await thief.edit(
                            nick='THIEF',
                            reason='Got caught trying to steal a feesh!'
                            )
                        # wait for 24 hours
                        await asyncio.sleep(24 * 3600)
                        # change it back
                        await thief.edit(
                            nick=old_display_name,
                            reason='Revert back after 24h.'
                            )

                    except discord.Forbidden as e:
                        # if it fails, do not raise exception
                        print('Failed to change nickname of', thief)

            else:
                # steal
                out_str = (
                    f'You {_ed} a {self.feesh_emoji} from '
                    f'{escape(target.display_name)}! How could you...'
                    )
                await channel.send(out_str)
                # edit stats
                self.feesh_stats(thief, donor=target, amount=1)

    @feesh.command(name='stats')
    async def _stats(self, ctx, member: discord.Member = None):
        """Generates a plot of the feesh distribution."""
        await ctx.trigger_typing()

        if member is None:
            member = ctx.author

        fig, ax = plt.subplots()

        members = self.stats['members']
        won = []
        for u in members:
            if (members[u]['amount'] != 0 or
                    members[u]['bot_given'] != 0) and \
                    members[u]['is_member']:
                if u == 460499306223239188:
                    continue  # Exclude HatBot
                won.append(members[u]['amount'])
        won = np.asarray(won)
        total = self.stats['total']

        d = np.diff(np.unique(won)).min()
        l = won.min() - d / 2
        r = won.max() + d / 2
        bins = np.arange(l, r + d, d)

        # _, _, patches = ax.hist(won, bins, rwidth=0.9, ec='k')
        _, _, patches = ax.hist(won, bins)
        member_amount = members[member.id]['amount']
        for i in range(len(patches)):
            if bins[i] < member_amount and member_amount - 1 < bins[i]:
                if not member.bot:
                    patches[i].set_facecolor('C1')

        ax.set_xlabel('Number of feesh')
        ax.set_ylabel('Number of members')
        fig.suptitle(f'Total: {total} feesh')

        annotation = (
            f'Average: {np.mean(won):>5.2f}\n'
            f'Median: {np.median(won):>6.1f}\n'
            f'Mode: {max(set(won), key=list(won).count):>7d}\n'
            fr'$\sigma$: {np.std(won):>5.2f}'
            )

        ax.annotate(annotation, xy=(0.98, 0.97), xycoords='axes fraction',
                    size=14, ha='right', va='top',
                    bbox=dict(boxstyle='round', fc='w'))

        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        fig.savefig('cogs/Feesh/feesh_stats.png')
        plt.close(fig)
        out_str = (
            f'{escape(member.display_name)} has {member_amount} '
            f'{self.feesh_emoji}.'
            )
        img = discord.File('cogs/Feesh/feesh_stats.png')
        await ctx.send(out_str, file=img)

    @feesh.command(name='whohas')
    async def _whohas(self, ctx, amount: int):
        """Returns the member(s) with the amount of feesh asked."""
        await ctx.trigger_typing()
        if amount < 0:
            raise commands.BadArgument('amount needs to be positive.')

        members = self.stats['members']
        who = []
        for u in members:
            if members[u]['amount'] == amount:
                member = ctx.guild.get_member(u)
                try:
                    who.append(member.display_name)
                except AttributeError as e:
                    # if the member was not found, for some reason
                    pass

        out_str = f'Member(s) with {amount} {self.feesh_emoji}:\n'
        out_str += '```\n' + '\n'.join(sorted(who)) + '\n```'
        await ctx.send(out_str)

    @_give.error
    @_stats.error
    async def feesh_error(self, ctx, error):
        """Error handling for feesh subcommands."""
        if isinstance(error, commands.BadArgument):
            await ctx.send('Unknown member! :dizzy_face:')
        else:
            raise error

    @_whohas.error
    async def feesh_whohas_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send('The amount needs to be a positive whole number.')
        else:
            raise error

    @_steal.error
    async def feesh_steal_error(self, ctx, error):
        """Error handling for the feesh steal subcommand."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.add_reaction('\U0000231B')  # :hourglass:

            if error.retry_after < 60:
                # seconds
                retry_after = '{:.0f} second(s)'.format(error.retry_after)
            elif error.retry_after < 3600:
                # minutes
                retry_after = '{:.0f} minute(s)'.format(error.retry_after / 60)
            else:
                # hours
                retry_after = '{:.0f} hour(s)'.format(error.retry_after / 3600)

            out_str = (
                f'You have already tried to {ctx.invoked_with} today, '
                f'wait for {retry_after}.'
                )

            await ctx.author.send(out_str)

        else:
            if isinstance(error, commands.CommandInvokeError):
                print(error)

            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send('You need a target. :spy:')

            elif isinstance(error, commands.BadArgument):
                await ctx.send('Unknown member! :dizzy_face:')

            # if the arguments were invalid, do not count the cooldown
            # WARNING is okay only if the bucket is 1
            # ctx.command.reset_cooldown(ctx)

            # USE THIS for more flexability
            bucket = ctx.command._buckets.get_bucket(ctx)
            bucket._tokens += 1

    def feesh_stats(self, member, donor=None, amount=1):
        # TODO: change name to something better
        # Give feesh to member
        mid = member.id
        try:
            self.stats['members'][mid]['amount'] += amount
            self.stats['members'][mid]['last_nickname'] = member.display_name
        except KeyError as e:
            ustats = {
                'amount': amount,
                'bot_given': 0,
                'last_nickname': member.display_name,
                'is_member': True
                }
            self.stats['members'][mid] = ustats

        if donor is None:  # Bot gives a feesh
            self.stats['total'] += amount
            self.stats['members'][mid]['bot_given'] += amount

        else:  # Takes feesh from the donor (if it is not the Bot)
            did = donor.id
            self.stats['members'][did]['amount'] -= amount
            self.stats['members'][did]['last_nickname'] = donor.display_name

        pkl_dump(self.stats, FEESH_STATS)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def collect_feesh(self, ctx):
        """Give the feesh from members that left to the bot."""
        n = 0
        for id in self.stats['members'].keys():
            if self.stats['members'][id]['is_member']:
                member = discord.utils.get(self.guild.members, id=id)
                if member is None:
                    amount = self.stats['members'][id]['amount']
                    print(self.stats['members'][id]['last_nickname'], 'left',
                          amount, 'feesh.')
                    n += amount

                    self.stats['members'][self.bot.user.id]['amount'] += amount
                    self.stats['members'][id]['amount'] = 0
                    self.stats['members'][id]['is_member'] = False

        print(f'Collected {n} feesh.')

        pkl_dump(self.stats, FEESH_STATS)


def feesh_wall():
    # TODO: randomize the wall
    wall = '{0}               {0}          {0}\n' +\
           '              {0}                           {0}\n' +\
           '{0}                   {0}                      {0}'
    return wall


def is_not_offline(member):
    valid = not member.bot and \
        member.status != discord.Status.offline
    return valid


def leet(text):
    def getchar(c): return chars[c] if c in chars else c
    chars = {"a": "4", "e": "3", "g": "6",
             "l": "1", "o": "0", "s": "5", "t": "7"}
    return ''.join(getchar(c.lower()) for c in text)


def pkl_load(filename):
    with open(filename, 'rb') as f:
        pkl = pickle.load(f)
    return pkl


def pkl_dump(data, filename):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)

    with open(filename.replace('.pkl', '.json'), 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
