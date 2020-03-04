import asyncio
from collections import Counter, defaultdict
import copy
import json
import os
import pickle

import discord
from discord.ext import commands, tasks
from discord.utils import escape_markdown
import numpy as np

from ..utils.cogs import FunCog
from ..utils.datetime_modulo import datetime
from datetime import timedelta
from ..utils.dicts import AttrDict
from ..utils.formats import pretty_print_timedelta
from . import menus


COG_PATH = os.path.dirname(__file__)

with open(os.path.join(COG_PATH, 'fish.json')) as f:
    FISH_SPECIES = AttrDict.from_nested_dict(json.load(f))

SMELLS = [
    'It smells delightful!',
    'It smells alright.',
    'It does not smell that bad.',
    'It does not smell good.',
    'It smells bad.',
    'It smells horrible!',
    'Oh no! What is that ungodly smell?!',
    ]

WEATHERS = [
    '\u2600\ufe0f',
    '\U0001f324\ufe0f',
    '\u26c5',
    '\U0001f325\ufe0f',
    '\u2601\ufe0f',
    '\U0001f326\ufe0f',
    '\U0001f327\ufe0f',
    '\u26c8\ufe0f',
    '\U0001f328\ufe0f',
    ]

EMBED_COLOR = discord.Color.blurple()


class FishTopNoEntriesError(commands.CommandError):
    """Exception raised when the fish_top command called but no best
    catches are set yet.
    """
    pass


class NoFishError(commands.CommandError):
    """Exception raised when one member in a trade has no Fish in
    their inventory.
    """
    pass


class IsStunnedError(commands.CheckFailure):
    """Exception raised when the check `is_not_stunned` has failed."""

    pass


class InTradeError(commands.CheckFailure):
    """Exception raised when the check `is_not_trading` has failed."""

    pass


def is_not_stunned():
    """Decorator that checks if the member is stunned and cannot fish."""

    def predicate(ctx):
        stunned_until = ctx.cog.stunned_until[ctx.author.id]

        stunned = datetime.utcnow() < stunned_until
        if stunned:
            stunned_for = stunned_until - datetime.utcnow()
            raise IsStunnedError('You are still stunned for '
                f'{pretty_print_timedelta(stunned_for)}!')

        return True

    return commands.check(predicate)


def is_not_trading():
    """Decorator that checks if the member is currently trading."""

    def predicate(ctx):
        if ctx.author.id in ctx.cog.in_trade:
            raise InTradeError('You are in a trade, you cannot do that yet.')

        return True

    return commands.check(predicate)


class Fish:
    """One fish instance."""

    def __init__(self, size, species, smell, weight, caught_by_id):
        self.size = size
        self.species = species
        self.smell = smell
        self.weight = weight
        self.caught_by_id = caught_by_id
        self.caught_on = datetime.utcnow()
        self.color = getattr(discord.Color, FISH_SPECIES[size].color,
                             discord.Color.default)()

    @classmethod
    def from_random(cls, exp, weather, caught_by_id):
        """Create a fish randomly based on the weather."""

        rates = [cls._catch_rate(exp, weather, *size.rates)
                 for size in FISH_SPECIES.values()]
        p = np.asarray(rates) / sum(rates)

        size = np.random.choice(list(FISH_SPECIES.keys()), p=p)
        species = np.random.choice(FISH_SPECIES[size].species)
        smell = np.random.choice(SMELLS)
        weight = np.random.uniform(*FISH_SPECIES[size].weight)

        return cls(size, species, smell, weight, caught_by_id)

    @staticmethod
    def _catch_rate(exp, weather, r_min, r_max):
        """Defines the rate of catching a fish with.
        exp: The member's experience. Higher exp means better rate.
        weather: The current weather. The higher the value, the
                 higher the rates.
        r_min: The minimal catch rate. Is the value returned if exp = 0.
        r_max: The maximal catch rate. Is the value returned if exp -> infinity.
        """
        return r_min + (r_max - r_min) * (1 - np.exp(- weather * exp / 5e4))

    def to_embed(self):
        """Return a discord.Embed object to send in a discord.Message."""
        embed = discord.Embed(
            color=self.color,
            description=self.smell,
        ).add_field(
            name='Fish',
            value=f'{self.size.title()} {self.species}',
        ).add_field(
            name='Weight',
            value=f'{self.weight:.3f} kg',
        ).add_field(
            name='Caught By',
            value=f'<@{self.caught_by_id}>',
        )

        return embed

    def __repr__(self):
        return f'{self.size.title()} {self.species} ({self.weight:.3f} kg)'

    def __lt__(self, other):
        """Less than operator. Compare instances on the weight attribute."""
        return self.weight < other.weight


class Weather:
    """Define the weather for the day."""

    def __init__(self, state):
        state = min(state, len(WEATHERS) - 1)  # not above the limit
        state = max(state, 0)  # is above 0
        self.state = state

    @classmethod
    def from_random(cls):
        state = np.random.randint(len(WEATHERS))
        return cls(state)

    def __repr__(self):
        return WEATHERS[self.state]


class Fishing(FunCog):
    """Collection of fish-related commands."""

    def __init__(self, bot):
        super().__init__(bot)
        self.stunned_until = defaultdict(lambda: datetime.min)
        self.in_trade = set()
        self.change_weather.start()
        self.interest_experience.start()

        try:
            with open(os.path.join(self._cog_path, 'fish_data.pkl'), 'rb') as f:
                self.data = pickle.load(f)

        except FileNotFoundError:
            self.data = AttrDict()

    def cog_unload(self):
        super().cog_unload()
        self.change_weather.cancel()
        self.interest_experience.cancel()
        self._save_data()

    def cog_check(self, ctx):
        """Check if is in a guild, and if in appropriate channel."""

        return ctx.guild is not None and super().cog_check(ctx)

    @property
    def cog_levels(self):
        return self.bot.get_cog('Levels')

    @tasks.loop(hours=24)
    async def change_weather(self):
        """Change the weather randomly every day."""

        self.weather = Weather.from_random()

    @tasks.loop(hours=12)
    async def interest_experience(self):
        """Give some experience to a random active member."""

        active_members = []
        for m in self.guild.members:
            try:
                if self.data[m.id].total_caught > 0:
                    active_members.append(m)
            except KeyError:
                pass

        winner = np.random.choice(active_members)
        # bonus_experience = np.random.normal(10, 3)  # can be negative
        bonus_experience = np.random.triangular(3, 5, 15)
        out_str = (
            f':moneybag: {escape_markdown(winner.display_name)} got a little '
            f'bit of experience! ({bonus_experience:.3f} xp)'
            )

        self._give_experience(winner, bonus_experience)

        await self.channel_msg.send(out_str)

    @interest_experience.before_loop
    async def interest_experience_before(self):
        """Wait until time mod 12h and fetch the channel."""

        await self.bot.wait_until_ready()

        # self.channel_msg = self.bot.get_channel(588171779957063680)  # bot-0
        self.channel_msg = self.bot.get_channel(548606793656303625)  # hatbot-land
        # self.channel_msg = self.bot.get_channel(680866127546679307)  # hatbot-beta
        if self.channel_msg is None:
            self.interest_experience.cancel()
            return

        self.guild = self.channel_msg.guild

        now = datetime.utcnow()
        _12h = timedelta(hours=12)
        next = now // _12h + _12h  # get next 00 or 12
        await discord.utils.sleep_until(next)  # wait until then

    @commands.group(aliases=['feesh'], invoke_without_command=True,
                    cooldown_after_parsing=True)
    @commands.cooldown(1, 20 * 60, commands.BucketType.member)  # 1 every 20 mins
    @is_not_stunned()
    @is_not_trading()
    async def fish(self, ctx):
        """Command group for the fishing commands.
        If invoked without subcommand, catches a random fish.
        """
        entry = self._get_member_entry(ctx.author)

        catch = Fish.from_random(entry.exp, self.weather.state, ctx.author.id)

        # add to journal
        self._add_to_journal(ctx.author, catch)

        # save best catch
        self._set_best_catch(ctx.author, catch)

        embed = catch.to_embed()

        keep = await menus.FishingConfirm(embed).prompt(ctx)

        if keep:
            self._add_to_inventory(ctx.author, catch)

        else:
            self._give_experience(ctx.author, catch.weight)

    @fish.command(name='card')
    async def fish_card(self, ctx, *, member: discord.Member = None):
        """Show some statistics about a member's fishing experience."""

        if member is None:
            member = ctx.author

        embed = discord.Embed(
            title=f'Fishing Card of {escape_markdown(member.display_name)}',
            color=EMBED_COLOR,
        ).set_thumbnail(
            url=member.avatar_url,
        )

        entry = self._get_member_entry(member)
        try:
            date_str = entry.best_catch.caught_on.strftime('%b %d %Y')

        except AttributeError:
            date_str = None

        embed.add_field(
            name='Best Catch',
            value=entry.best_catch,
        ).add_field(
            name='Caught on',
            value=date_str,
        ).add_field(
            name='Experience',
            value=f'{entry.exp:.3f} xp',
        )

        await ctx.send(embed=embed)

    @fish.command(name='create')
    @commands.is_owner()
    async def fish_create(self, ctx, size: str, species: str, weight: float):
        """Create a Fish and display it.
        For testing purposes only.
        """
        fish = Fish(size, species, 'It smells cheated...', weight,
                    ctx.author.id)
        await ctx.send(embed=fish.to_embed())

    @fish.command(name='exptop')
    async def fish_exptop(self, ctx):
        """Display the users who have the most experience."""

        sorted_experience = self._get_sorted_experience()
        sorted_experience.reverse()

        if len(sorted_experience) == 0:
            raise FishTopNoEntriesError('No one with experience yet.')

        top_menu = menus.TopMenu(
            source=menus.TopExperienceSource(sorted_experience),
            clear_reactions_after=True,
            )

        await top_menu.start(ctx)

    @fish.command(name='inventory', aliases=['inv', 'bag', 'sell'])
    async def fish_inventory(self, ctx):
        """Look at your fishing inventory.
        Also allows you to sell the fish you previously saved.
        """
        entry = self._get_member_entry(ctx.author)
        if len(entry.inventory) == 0:
            embed = discord.Embed(
                title='Fish Inventory',
                description='No fish in inventory.',
                color=EMBED_COLOR,
                )
            await ctx.send(embed=embed, delete_after=3 * 60)
            return

        inventory = menus.InventoryMenu(
            source=menus.InventorySource(entry.inventory),
            clear_reactions_after=True,
            )
        to_sell = await inventory.prompt(ctx)

        if len(to_sell) != 0:
            catches = []
            for i in to_sell:
                catches.append(entry.inventory[i])

            for catch in catches:
                self._sell_from_inventory(ctx.author, catch)

    @fish.command(name='journal', aliases=['log'])
    async def fish_journal(self, ctx):
        """Fishing log of the amount of fish caught and different stats."""

        entry = self._get_member_entry(ctx.author)

        total_species = {key: len(value['species'])
                         for key, value in FISH_SPECIES.items()}
        species_caught = {key: len(value)
                          for key, value in entry.journal.items()}
        species_caught_str = '\n'.join(
            f'{size.title()}: **{species_caught[size]}/{total_species[size]}**'
            for size in FISH_SPECIES.keys()
            )

        most_caught = {key: value.most_common(1)[0][0]
                       for key, value in entry.journal.items()
                       if len(value) > 0}
        most_caught_str = '\n'.join(
            f'{size.title()} **{most_caught[size]}**'
            for size in most_caught.keys()
            )

        totals_str = (
            'Species Caught: '
            f'**{sum(species_caught.values())}'
            f'/{sum(total_species.values())}**\n'
            f'Catches: **{entry.total_caught}**'
            )

        embed = discord.Embed(
            title=('Fishing Journal of '
                   f'{escape_markdown(ctx.author.display_name)}'),
            color=EMBED_COLOR,
        ).set_thumbnail(
            url=ctx.author.avatar_url,
        ).add_field(
            name='Species Caught',
            value=species_caught_str if species_caught_str else None,
        ).add_field(
            name='Most Caught',
            value=most_caught_str if most_caught_str else None,
        ).add_field(
            name='Totals',
            value=totals_str,
        )

        await ctx.send(embed=embed)

    @fish.command(name='slap', cooldown_after_parsing=True)
    @commands.cooldown(1, 30, commands.BucketType.member)
    @is_not_trading()
    async def fish_slap(self, ctx, *, member: discord.Member):
        """Slap another member with one of your fish.
        Slapping someone prevents them from fishing for a given amount
        of time. The fish used to slap the member is destroyed upon
        use, so think wisely.
        """
        entry = self._get_member_entry(ctx.author)

        if len(entry.inventory) == 0:
            raise NoFishError('You do not have any fish to slap with.')

        slapping_fish = np.random.choice(entry.inventory)
        self._remove_from_inventory(ctx.author, slapping_fish)

        # get stunned for the sqrt of the weight of the fish, in hours
        stunned_time = timedelta(hours=np.sqrt(slapping_fish.weight))
        beginning = max(datetime.utcnow(), self.stunned_until[member.id])
        self.stunned_until[member.id] = until = beginning + stunned_time
        stunned_time = until - datetime.utcnow()

        out_str = (
            f'{escape_markdown(member.display_name)} got slapped by '
            f'{escape_markdown(ctx.author.display_name)} with a '
            f'{slapping_fish}!\n'
            f'They are stunned for {pretty_print_timedelta(stunned_time)} '
            'and cannot go fishing!'
            )

        await ctx.send(out_str)

    @fish.command(name='top')
    async def fish_top(self, ctx):
        """Display the best catches server-wide."""

        sorted_best_catches = self._get_sorted_best_catches()
        sorted_best_catches.reverse()

        if len(sorted_best_catches) == 0:
            raise FishTopNoEntriesError('No best catches yet.')

        top_menu = menus.TopMenu(
            source=menus.TopCatchesSource(sorted_best_catches),
            clear_reactions_after=True,
            )

        await top_menu.start(ctx)

    @fish.command(name='trade')
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def fish_trade(self, ctx, *, other_member: discord.Member):
        """Trade fish with another member."""

        if other_member == ctx.author:
            raise commands.BadArgument('You cannot trade with yourself!')

        author_entry = self._get_member_entry(ctx.author)
        other_entry = self._get_member_entry(other_member)
        other_str = escape_markdown(other_member.display_name)

        if len(author_entry.inventory) == 0:
            raise NoFishError('You have no fish to trade!')

        elif len(other_entry.inventory) == 0:
            raise NoFishError(f'{other_str} has no fish to trade!')

        if not other_member.mentioned_in(ctx.message):
            other_str = other_member.mention

        msg = copy.copy(ctx.message)
        msg.author = other_member
        other_ctx = await self.bot.get_context(msg, cls=type(ctx))

        confirm_msg = (
            f'Hey {other_str}, '
            f'{escape_markdown(ctx.author.display_name)} '
            'wants to trade with you! Do you accept?'
            )

        confirm = await menus.TradeConfirm(confirm_msg).prompt(other_ctx)

        if confirm:
            await ctx.send('Trade accepted.', delete_after=5 * 60)
            # start both menus and then transfer the fish
            author_menu = menus.TradeMenu(
                source=menus.TradeSource(
                    author_entry.inventory,
                    ),
                clear_reactions_after=True,
                )
            other_menu = menus.TradeMenu(
                source=menus.TradeSource(
                    other_entry.inventory,
                    ),
                clear_reactions_after=True,
                )

            tasks = [
                asyncio.create_task(author_menu.prompt(ctx)),
                asyncio.create_task(other_menu.prompt(other_ctx)),
                ]

            # done is a set of tasks, in the order they were COMPLETED
            # (not in the order of `tasks`!!!)
            # or not I can't seem to figure it out
            done, pending = await asyncio.wait(tasks)

            to_trade = [t.result() for t in done]
            to_trade = {t[0].id: t[1] for t in to_trade}
            if None in to_trade.values():
                await ctx.send('Trade cancelled.', delete_after=5 * 60)
                return

            # proceed to trade
            author_trade = author_entry.inventory[to_trade[ctx.author.id]]
            other_trade = other_entry.inventory[to_trade[other_member.id]]

            self._remove_from_inventory(ctx.author, author_trade)
            self._remove_from_inventory(other_member, other_trade)

            self._add_to_inventory(ctx.author, other_trade)
            self._add_to_inventory(other_member, author_trade)

            await ctx.send('Trade successful!', delete_after=5 * 60)

        else:
            await ctx.send('Trade denied.', delete_after=5 * 60)

    @fish_trade.before_invoke
    async def fish_trade_before(self, ctx):
        """Register the two members as currently in trade."""

        other_member = ctx.kwargs['other_member']
        self.in_trade.add(ctx.author.id)
        self.in_trade.add(other_member.id)

    @fish_trade.after_invoke
    async def fish_trade_after(self, ctx):
        """Remove the two members from being currently in trade."""

        other_member = ctx.kwargs['other_member']
        self.in_trade.remove(ctx.author.id)
        self.in_trade.remove(other_member.id)

    @fish.error
    async def fish_error(self, ctx, error):
        """Error handling for the fish command.
        In case of CommandOnCooldown error, allow user to check how much
        time is left.
        """
        if isinstance(error, commands.CommandOnCooldown):
            await menus.CooldownMenu(ctx.message, error).start(ctx)

        elif isinstance(error, IsStunnedError):
            await ctx.send(error)

        elif isinstance(error, InTradeError):
            await ctx.send(error)

        else:
            raise error

    @fish_slap.error
    async def fish_slap_error(self, ctx, error):
        """Error handling for the fish_slap command."""

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need to specify someone to slap.')

        elif isinstance(error, commands.BadArgument):
            await ctx.send(error)

        elif isinstance(error, NoFishError):
            await ctx.send(error)

        elif isinstance(error, InTradeError):
            await ctx.send(error)

        else:
            raise error

    @fish_top.error
    async def fish_top_error(self, ctx, error):
        """Error handling for the fish_top command."""

        if isinstance(error, FishTopNoCatchesError):
            await ctx.send(error)

        else:
            raise error

    @fish_trade.error
    async def fish_trade_error(self, ctx, error):
        """Error handling for the fish_trade command."""

        if isinstance(error, commands.MaxConcurrencyReached):
            name = error.per.name
            suffix = f'for this {name}' if name != 'default' else 'globally'
            await ctx.send(f'This command is already running {suffix}.')

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need to specify a member to trade with.')

        elif isinstance(error, NoFishError):
            await ctx.send(error)

        elif isinstance(error, commands.BadArgument):
            await ctx.send(error)

        else:
            raise error

    @commands.group(invoke_without_command=True)
    async def weather(self, ctx):
        """Check today's weather."""

        await ctx.send(f'The weather currently is {self.weather}')

    @weather.command(name='set')
    @commands.is_owner()
    async def weather_set(self, ctx, state: int):
        """Set the weather to the given state (positive integer)."""

        self.weather = Weather(state)
        await ctx.send(f'Weather set to {self.weather}')

    def _init_member_entry(self, *, best_catch=None, exp=0, inventory=None):
        """Return an empty entry for member data."""

        if inventory is None:
            inventory = []

        return AttrDict.from_nested_dict(dict(
            best_catch=best_catch,
            exp=exp,
            inventory=inventory,
            journal={size: Counter() for size in FISH_SPECIES.keys()},
            total_caught=0,
            ))

    def _get_member_entry(self, member: discord.Member):
        """Return the member entry, or create one if it does not exist yet."""

        try:
            entry = self.data[member.id]

        except KeyError:
            entry = self._init_member_entry()
            self.data[member.id] = entry

        return entry

    def _add_to_journal(self, member: discord.Member, catch: Fish):
        """Helper function to add a catch to a member's fishing journal."""

        entry = self._get_member_entry(member)

        entry.total_caught += 1
        entry.journal[catch.size][catch.species] += 1

        self._save_data()

    def _give_experience(self, member: discord.Member, amount: float):
        """Helper function to give experience, and handle KeyErrors."""

        try:
            self.data[member.id].exp += amount

        except KeyError:
            self.data[member.id] = self._init_member_entry(exp=amount)

        self._save_data()

    def _set_best_catch(self, member: discord.Member, catch: Fish):
        """Helper function to save the best catch of a member."""

        entry = self._get_member_entry(member)

        try:
            entry.best_catch = max(entry.best_catch, catch)

        except TypeError:
            entry.best_catch = catch

        self._save_data()

    def _add_to_inventory(self, member: discord.Member, catch: Fish):
        """Helper function to add a catch to a member's inventory."""

        entry = self._get_member_entry(member)
        entry.inventory.append(catch)
        entry.inventory.sort()

        self._save_data()

    def _remove_from_inventory(self, member: discord.Member, catch: Fish):
        """Helper function to remove a catch from a member's inventory."""

        entry = self._get_member_entry(member)
        entry.inventory.remove(catch)

        self._save_data()

    def _sell_from_inventory(self, member: discord.Member, catch: Fish):
        """Helper function to sell a catch from a member's inventory."""

        self._remove_from_inventory(member, catch)
        self._give_experience(member, catch.weight)  # saves data here

    def _get_sorted_best_catches(self):
        """Return the list of catches, sorted by weight."""

        entries = list(self.data.values())
        best_catches = [e.best_catch for e in entries if e.best_catch is not None]

        return sorted(best_catches)

    def _get_sorted_experience(self):
        """Return the list of member entries, sorted by experience."""

        entries = list(self.data.items())
        entries = [e for e in entries if e[1].exp > 0]

        return sorted(entries, key=lambda e: e[1].exp)

    def _save_data(self):
        """Save the data to disk (keep it in memory also)."""

        with open(os.path.join(self._cog_path, 'fish_data.pkl'), 'wb') as f:
            pickle.dump(self.data, f)
