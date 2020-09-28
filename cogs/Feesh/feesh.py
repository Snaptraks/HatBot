import asyncio
import copy
import json
import pickle
import re
import typing

import discord
from discord.ext import commands
from discord.utils import escape_markdown as escape
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from ..utils.datetime_modulo import datetime
from datetime import timedelta
from ..utils.cogs import FunCog


FEESH_DATA_FILE = 'cogs/Feesh/feesh_data.pkl'


class Feesh(FunCog):
    """Cog for the periodic feesh, and the general trading of feesh."""

    def __init__(self, bot):
        super().__init__(bot)
        try:
            self.data = pkl_load(FEESH_DATA_FILE)
        except FileNotFoundError:
            self.data = {'members': {}, 'total': 0}

        # Tasks
        self.remove_tasks = {}

        # Init feesh emoji and messaging channel.
        self.bot.loop.create_task(self.load_data())

        # Background tasks
        self.bg_tasks = [
            self.bot.loop.create_task(self.periodic_feesh(timedelta(hours=4))),
        ]

    @property
    def cog_levels(self):
        return self.bot.get_cog('Levels')

    def cog_unload(self):
        super().cog_unload()
        for task in self.bg_tasks:
            task.cancel()  # Cancel background tasks

    async def load_data(self):
        """Load data from the guild, such as channel and emoji"""

        await self.bot.wait_until_ready()
        guild = discord.utils.get(
            self.bot.guilds, name='Hatventures Community'
        )

        if guild is not None:
            channel = discord.utils.find(
                lambda c: c.name.startswith('hatbot'),
                guild.channels
            )
            feesh = discord.utils.get(guild.emojis, name='feesh')

            self.guild = guild
            self.channel_msg = channel
            self.feesh_emoji = feesh

        else:
            self.guild = None
            self.channel_msg = None
            self.feesh_emoji = ':fish:'

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Update feesh stats when a new member joins."""

        try:
            # Cancel the removal of feesh task
            # This has no effect if the member rejoins after more than 24 hours
            self.remove_tasks[member.id].cancel()
            del self.remove_tasks[member.id]

        except KeyError:
            # The member has no removal tasks, check if he joined before
            try:
                # Mark member as in guild again
                self.data['members'][member.id]['is_member'] = True
            except KeyError:
                # Create new stats entry
                ustats = {
                    'amount': 0,
                    'bot_given': 0,
                    'last_nickname': member.display_name,
                    'is_member': True,
                }
                self.data['members'][member.id] = ustats

                pkl_dump(self.data, FEESH_DATA_FILE)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Clear the feesh of a member.
        Allow other people to collect it.
        """
        # py 3.7
        task = asyncio.create_task(self.wait_and_remove_feesh(member))
        self.remove_tasks[member.id] = task

    async def wait_and_remove_feesh(self, member):
        """Wait for 24 hours, then transfers the feesh to the bot."""

        try:
            print(f'{member} left. Waiting 24 hours.')
            await asyncio.sleep(24 * 3600)  # sleep for 24 hours

            amount = self.data['members'][member.id]['amount']
            self.data['members'][member.id]['is_member'] = False
            self.transfer_feesh(self.bot.user, member, amount=amount)

        except KeyError:
            print('member did not have feesh entry.')

        except asyncio.CancelledError:
            print('member came back, did not lose their feesh.')

    async def periodic_feesh(self, period):
        """Send a feesh to a random member every 'period'.

        Input
        -----
        period : timedelta
            Period of the message.
        """
        if not isinstance(period, timedelta):
            raise ValueError(f'period {period:f} is not timedelta')

        await self.bot.wait_until_ready()

        while not self.bot.is_closed():

            t = datetime.utcnow()
            wait = period - (t % period)
            await asyncio.sleep(wait.total_seconds())

            # no need to be online if we use Levels
            members_list = self.guild.members

            won = []
            for m in members_list:
                try:
                    won.append(self.data['members'][m.id]['bot_given'])
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
                        exp = self.cog_levels.data[m.id].exp
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
                content = (
                    'No one is online, I guess I\'ll have a snack! '
                    ':sushi:'
                )
                await self.channel_msg.send(content)
            else:
                winner = np.random.choice(members_list, p=weights)
                content = f'{winner.display_name} got a feesh !'
                content = (
                    f'{escape(winner.display_name)} got a '
                    f'{self.feesh_emoji} !'
                )

                # 1337 feesh
                if self.data['total'] == 1337 - 1:
                    content = (
                        f'{leet(winner.display_name)} '
                        f'({winner.display_name}) 607 4 '
                        f'{self.feesh_emoji}'
                    )

                await self.channel_msg.send(content)

                # statistics
                self.transfer_feesh(member=winner, amount=1)

    @commands.group(aliases=['<:feesh:427018890137174016>'],
                    invoke_without_command=True)
    async def feesh(self, ctx, *, member: discord.Member = None):
        """Give statistics on the amount of feesh given."""

        if member is None:
            member = ctx.author

        total = self.data['total']

        try:
            amount = self.data['members'][member.id]['amount']
        except KeyError as e:
            amount = 0

        content = (
            f'{total} {self.feesh_emoji} were given in total, '
            f'{escape(member.display_name)} has {amount}.'
        )

        await ctx.send(content)

    @feesh.group(name='give', aliases=['kobe'], invoke_without_command=True)
    async def feesh_give(self, ctx, amount: typing.Optional[int] = 1, *,
                         member: discord.Member):
        """Give a feesh from your feesh to a member."""

        donor = ctx.author

        # Checks to see if the member to receive a feesh is valid
        if donor == member:
            content = f'But... You can\'t give yourself a {self.feesh_emoji} !'

        elif member.bot:
            content = 'I\'m touched, but I cannot accept this :flushed:'

        else:  # It is valid:
            try:
                x = self.data['members'][donor.id]['amount']

            except KeyError:
                x = 0

            if amount < 1:
                content = 'Nice try.'

            elif x - amount < 0:
                content = (
                    'That\'s very nice of you, but you don\'t '
                    f'have enough {self.feesh_emoji}!'
                )

            else:
                self.transfer_feesh(member=member, donor=donor, amount=amount)
                content = (
                    f'You gave {amount} {self.feesh_emoji} to '
                    f'{escape(member.display_name)}. Yay!'
                )

        await ctx.send(content)

    @feesh_give.command(name='random')
    async def feesh_give_random(self, ctx):
        """Give a feesh to a random member."""
        member = np.random.choice([
            m for m in ctx.guild.members if not m.bot and m != ctx.author
        ])
        await self._feesh_command_random(ctx, member)

    @feesh.command(name='bomb', hidden=True, aliases=['yeet'])
    async def feesh_bomb(self, ctx):
        """Send all your feesh to random online members (1 per member)."""

        bomb = '\U0001F4A3'  # bomb
        cancel = '\U000026D4'  # no_entry
        author = ctx.author
        channel = ctx.channel
        message = ctx.message

        if self.data['members'][author.id]['amount'] == 0:
            content = f'You have no {self.feesh_emoji} though.'
            await channel.send(content)
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
            content = 'You didn\'t confirm quickly enough, I must cancel.'
            await channel.send(content)
            return

        def isvalid(m):
            try:
                return (self.cog_levels.data[m.id].exp > 0
                        and m != ctx.author)
            except KeyError:
                return False

        members_list = [m for m in self.guild.members if isvalid(m)]

        if reaction.emoji == cancel:
            content = 'Abort mission!'
            await channel.send(content)

        elif reaction.emoji == bomb:
            amount = self.data['members'][author.id]['amount']
            amount = min(amount, len(members_list))
            targets = np.random.choice(
                members_list, size=amount, replace=False)

            content = ':tired_face:  :triumph:  :boom:\n'
            content += feesh_wall().format(self.feesh_emoji)

            pm_str = 'You sent a feesh to\n```\n' + \
                '\n'.join([m.display_name for m in targets]) + \
                '\n```'

            await author.send(pm_str)
            await channel.send(content)

            for member in targets:
                self.transfer_feesh(member=member, donor=author, amount=1)

    @feesh.command(name='top')
    async def feesh_top(self, ctx):
        """Display the member(s) with the most feesh."""

        L = []
        for x in self.data['members']:
            if x == ctx.me.id:
                continue  # Exclude HatBot
            L.append((x, self.data['members'][x]['amount']))

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
                    self.data['members'][u['ID']]['last_nickname']
                )

        plural = 's' if len(top_members) > 1 else ''
        content = (
            f'Member{plural} with the most {self.feesh_emoji} '
            f'(**{top_amount}**):\n'
        )
        content += '```\n' + '\n'.join(top_members) + '\n```'

        await ctx.channel.send(content)

    @commands.cooldown(1, 24 * 3600, commands.BucketType.user)
    @feesh.group(name='steal', hidden=True, aliases=['yoink'],
                 invoke_without_command=True)
    async def feesh_steal(self, ctx, *, target: discord.Member):
        """Attempt to steal a feesh from a given member.
        This is a secret command! Shhhhhhhhh...
        """
        if ctx.invoked_with == 'yoink':
            _ing = 'yoinking'
            _ed = 'yoinked'
        else:
            _ing = 'stealing'
            _ed = 'stole'

        thief = ctx.author
        channel = ctx.channel

        if thief == target:
            content = f'You cannot {ctx.invoked_with} from yourself.'
            await channel.send(content)
            raise ValueError(f'Tried to steal from self')

        # elif target.bot:
            # content = 'Please, I have no {}!'.format(self.feesh_emoji)
            # await channel.send(content)
            # raise ValueError('Tried to steal from the bot')

        else:
            # random typing delay
            await channel.trigger_typing()
            r = np.random.rand()  # [0, 1)
            t = 2.5 * r + 0.5  # [0.5, 2)
            await asyncio.sleep(t)

            feesh_thief = self.data['members'][thief.id]['amount']
            feesh_target = self.data['members'][target.id]['amount']
            feesh_diff = feesh_target - feesh_thief

            if feesh_target == 0:
                content = (
                    f'{escape(target.display_name)} has no {self.feesh_emoji}, '
                    f'you can\'t {ctx.invoked_with} from them.')
                await channel.send(content)
                raise ValueError('Target has no feesh')

            def odds(y):
                L = []
                for x in self.data['members']:
                    if x == 460499306223239188:
                        continue  # Exclude HatBot
                    L.append((x, self.data['members'][x]['amount']))

                L = np.array(L, dtype=[('ID', '<i8'), ('amount', '<i8'), ])
                top_amount = L['amount'].max()

                if y <= 0:
                    return 0
                else:
                    # y > 0
                    # 0 to 0.4ish
                    return (
                        np.tanh((y - (1.2 * top_amount)) / top_amount) / 2 + 0.5)

            drop = (1 - odds(feesh_diff)) / 3
            fail = 2 * drop  # success = 1. - fail - drop

            if target.id == 460499306223239188:  # HatBot
                if feesh_target > 0:
                    fail = 1 / 4
                    drop = fail

            r = np.random.rand()
            if r < fail:
                # fail
                content = (
                    f'You failed at {_ing} a {self.feesh_emoji} '
                    f'from {escape(target.display_name)}.'
                )
                await channel.send(content)
            elif r < fail + drop:
                # drop
                if feesh_thief != 0:
                    content = [
                        (f'In your haste, you dropped a {self.feesh_emoji} '
                         'of your own!\n'),
                        'Who will get it?'
                    ]
                    msg = await channel.send(''.join(content))
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
                    content = content[0] + \
                        f'{escape(member.display_name)} took it!'
                    await msg.edit(content=content)
                    # edit stats
                    self.transfer_feesh(member, donor=thief, amount=1)

                else:
                    content = (
                        f'You failed to {ctx.invoked_with} and '
                        'got caught! THIEF!'
                    )
                    await channel.send(content)
                    try:
                        # change nickname
                        old_display_name = thief.display_name
                        await thief.edit(
                            nick=f'{old_display_name} the THIEF',
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
                content = (
                    f'You {_ed} a {self.feesh_emoji} from '
                    f'{escape(target.display_name)}! How could you...'
                )
                await channel.send(content)
                # edit stats
                self.transfer_feesh(thief, donor=target, amount=1)

    @feesh_steal.command(name='random')
    async def feesh_steal_random(self, ctx):
        """Attempt to steal a feesh from a random member with more feesh
        than the author.
        """
        max_amount = max([m['amount'] for m in self.data['members'].values()])
        thief_amount = self.data['members'][ctx.author.id]['amount']

        if thief_amount == max_amount:
            # cannot steal, already have the top amount
            await ctx.send('You have the most feesh, you cannot steal!')

        else:
            potential_targets = []
            for id, data in self.data['members'].items():
                if data['amount'] > thief_amount:
                    potential_targets.append(ctx.guild.get_member(id))

            potential_targets = [m for m in potential_targets if m is not None]
            target = np.random.choice(potential_targets)
            await self._feesh_command_random(ctx, target)

    @feesh.command(name='stats')
    async def feesh_stats(self, ctx, *, member: discord.Member = None):
        """Generate a plot of the feesh distribution."""

        await ctx.trigger_typing()

        if member is None:
            member = ctx.author

        img = await self.bot.loop.run_in_executor(
            None, self._make_feesh_stats_figure, member)

        member_amount = self.data['members'][member.id]['amount']

        content = (
            f'{escape(member.display_name)} has {member_amount} '
            f'{self.feesh_emoji}.'
        )
        await ctx.send(content, file=img)

    @feesh.command(name='whohas')
    async def feesh_whohas(self, ctx, amount: int):
        """Return the member(s) with the amount of feesh asked."""

        await ctx.trigger_typing()
        if amount < 0:
            raise commands.BadArgument('amount needs to be positive.')

        members = self.data['members']
        who = []
        for u in members:
            if members[u]['amount'] == amount:
                member = ctx.guild.get_member(u)
                try:
                    who.append(member.display_name)
                except AttributeError as e:
                    # if the member was not found, for some reason
                    pass

        content = f'Member(s) with {amount} {self.feesh_emoji}:\n'
        content += '```\n' + '\n'.join(sorted(who)) + '\n```'
        await ctx.send(content)

    @feesh.command(name='random')
    async def feesh_random(self, ctx, subcommand):
        """Deprecated command. Return a command hint."""
        command_hint = ' '.join([
            ctx.command.full_parent_name,
            subcommand,
            'random',
        ])
        await ctx.send(f'Did you mean: `{ctx.prefix}{command_hint}`?')

    @feesh_give.error
    @feesh_stats.error
    async def feesh_error(self, ctx, error):
        """Error handling for the feesh give and stats subcommands."""

        if isinstance(error, commands.BadArgument):
            await ctx.send('Unknown member! :dizzy_face:')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need to target someone!')
        else:
            raise error

    @feesh_whohas.error
    async def feesh_whohas_error(self, ctx, error):
        """Error handling for the feesh whohas subcommand."""

        if isinstance(error, commands.BadArgument):
            await ctx.send('The amount needs to be a positive whole number.')
        else:
            raise error

    @feesh_steal.error
    async def feesh_steal_error(self, ctx, error):
        """Error handling for the feesh steal subcommand.
        In case of an error in the command's invocation, do not
        count it towards the cooldown.
        """
        if isinstance(error, commands.CommandOnCooldown):
            hourglass_emoji = '\U0000231B'  # :hourglass:
            await ctx.message.add_reaction(hourglass_emoji)

            def check(reaction, member):
                return (member == ctx.author
                        and reaction.message.id == ctx.message.id
                        and reaction.emoji == hourglass_emoji)

            try:
                reaction, member = await self.bot.wait_for(
                    'reaction_add', check=check, timeout=10 * 60)
            except asyncio.TimeoutError:
                pass
            else:
                if error.retry_after < 60:
                    # seconds
                    retry_after = '{:.0f} second(s)'.format(error.retry_after)
                elif error.retry_after < 3600:
                    # minutes
                    retry_after = '{:.0f} minute(s)'.format(
                        error.retry_after / 60)
                else:
                    # hours
                    retry_after = '{:.0f} hour(s)'.format(
                        error.retry_after / 3600)

                content = (
                    f'You have already tried to {ctx.invoked_with} today, '
                    f'wait for {retry_after}.'
                )
                await ctx.author.send(content)

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

    def transfer_feesh(self, member, donor=None, amount=1):
        """Transfer feesh from donor to member, or give a new one
        if donor is None.
        """
        mid = member.id
        try:
            self.data['members'][mid]['amount'] += amount
            self.data['members'][mid]['last_nickname'] = member.display_name
        except KeyError as e:
            ustats = {
                'amount': amount,
                'bot_given': 0,
                'last_nickname': member.display_name,
                'is_member': True
            }
            self.data['members'][mid] = ustats

        if donor is None:  # Bot gives a feesh
            self.data['total'] += amount
            self.data['members'][mid]['bot_given'] += amount

        else:  # Takes feesh from the donor (if it is not the Bot)
            did = donor.id
            self.data['members'][did]['amount'] -= amount
            self.data['members'][did]['last_nickname'] = donor.display_name

        pkl_dump(self.data, FEESH_DATA_FILE)

    @commands.command()
    @commands.is_owner()
    async def collect_feesh(self, ctx):
        """Give the feesh from members that left to the bot."""

        n = 0
        for id in self.data['members'].keys():
            if self.data['members'][id]['is_member']:
                member = discord.utils.get(self.guild.members, id=id)
                if member is None:
                    amount = self.data['members'][id]['amount']
                    print(self.data['members'][id]['last_nickname'], 'left',
                          amount, 'feesh.')
                    n += amount

                    self.data['members'][self.bot.user.id]['amount'] += amount
                    self.data['members'][id]['amount'] = 0
                    self.data['members'][id]['is_member'] = False

        print(f'Collected {n} feesh.')

        pkl_dump(self.data, FEESH_DATA_FILE)

    async def _feesh_command_random(self, ctx, member):
        """Helper function to execute the command with the given member."""

        member_str = f'{member.mention}'
        msg = copy.copy(ctx.message)
        arguments = ' '.join([ctx.command.full_parent_name, member_str])
        msg.content = ctx.prefix + arguments
        new_ctx = await self.bot.get_context(msg, cls=type(ctx))
        await self.bot.invoke(new_ctx)

    def _make_feesh_stats_figure(self, member):
        fig, ax = plt.subplots()

        members = self.data['members']
        won = []
        for u in members:
            if (members[u]['amount'] != 0 or
                    members[u]['bot_given'] != 0) and \
                    members[u]['is_member']:
                if u == 460499306223239188:
                    continue  # Exclude HatBot
                won.append(members[u]['amount'])
        won = np.asarray(won)
        total = self.data['total']

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
        img = discord.File('cogs/Feesh/feesh_stats.png')

        return img


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
