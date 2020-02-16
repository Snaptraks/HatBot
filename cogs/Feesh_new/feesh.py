import asyncio
import json
import os
import pickle

import discord
from discord.ext import commands, tasks
from discord.utils import escape_markdown as escape
import numpy as np

from ..utils.cogs import FunCog
from ..utils.datetime_modulo import datetime
from datetime import timedelta
from ..utils.dicts import AttrDict
from ..utils.formats import pretty_print_timedelta


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

INVENTORY_EMOJI = '\U0001f9f0'  # :toolbox:
EXPERIENCE_EMOJI = '\U0001f4b5'  # :dollar:
SELL_ALL_EMOJI = '\U0001f4b0'  # :moneybag:


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
        return r_min + (r_max - r_min) * (1 - np.exp(- weather * exp / 5e3))

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


class FeeshCog(FunCog, name='Feesh'):
    """Collection of fish-related commands."""

    def __init__(self, bot):
        super().__init__(bot)
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
                exp = self.cog_levels.data[m.id].exp

            except KeyError:
                exp = 0

            except AttributeError:
                # often if cog_levels is None
                # assume everyone is active
                exp = 1

            if exp > 0:
                active_members.append(m)

        winner = np.random.choice(active_members)
        # bonus_experience = np.random.normal(10, 3)  # can be negative
        bonus_experience = np.random.triangular(3, 5, 15)
        out_str = (
            f':moneybag: {escape(winner.display_name)} got a little '
            f'bit of experience! ({bonus_experience:.2f} xp)'
            )

        self._give_experience(winner, bonus_experience)

        await self.channel_msg.send(out_str)

    @interest_experience.before_loop
    async def interest_experience_before(self):
        """Wait until time mod 12h and fetch the channel."""

        await self.bot.wait_until_ready()
        self.guild = discord.utils.get(
            # self.bot.guilds, name='Hatventures Community')
            self.bot.guilds, name='Bot Testing Server')
        self.channel_msg = discord.utils.get(
            # self.guild.channels, name='hatbot-land')
            self.guild.channels, name='bot-0')

        now = datetime.utcnow()
        _12h = timedelta(hours=12)
        next = now // _12h + _12h  # get next 00 or 12
        await discord.utils.sleep_until(next)  # wait until then

    @commands.group(aliases=['feesh', 'f'], invoke_without_command=True)
    @commands.cooldown(2, 3600, commands.BucketType.member)  # twice per hour
    async def fish(self, ctx):
        """Command group for the fishing commands.
        If invoked without subcommand, catches a random fish.
        """
        entry = self._get_member_entry(ctx.author)

        catch = Fish.from_random(entry.exp, self.weather.state, ctx.author.id)

        # save best catch
        self._set_best_catch(ctx.author, catch)

        embed = catch.to_embed()
        embed.description = 'You caught something!\n' + embed.description
        embed.set_footer(
            text=(
                f'Do you want to keep it {INVENTORY_EMOJI} '
                f'or sell it {EXPERIENCE_EMOJI} for experience?'
                ),
            )

        message = await ctx.send(embed=embed)

        for emoji in (INVENTORY_EMOJI, EXPERIENCE_EMOJI):
            await message.add_reaction(emoji)

        def check(reaction, member):
            return (member == ctx.author
                    and reaction.message.id == message.id
                    and reaction.emoji in (INVENTORY_EMOJI, EXPERIENCE_EMOJI))

        try:
            reaction, member = await self.bot.wait_for(
                'reaction_add', check=check, timeout=60)

        except asyncio.TimeoutError:
            new_footer = 'You did not answer quickly enough, I kept it for you.'
            # add to inventory
            self._add_to_inventory(ctx.author, catch)

        else:
            if reaction.emoji == INVENTORY_EMOJI:
                new_footer = 'You kept it in your inventory.'
                # add to inventory
                self._add_to_inventory(ctx.author, catch)

            elif reaction.emoji == EXPERIENCE_EMOJI:
                new_footer = 'You sold it for experience.'
                # add experience
                self._give_experience(ctx.author, catch.weight)

        embed.set_footer(text=new_footer)
        await message.edit(embed=embed)
        await message.clear_reactions()

    @fish.command(name='card')
    async def fish_card(self, ctx, member: discord.Member = None):
        """Show some statistics about a member's fishing experience."""

        if member is None:
            member = ctx.author

        embed = discord.Embed(
            title=f'Fishing Card of {escape(member.display_name)}',
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

    @fish.command(name='inventory', aliases=['inv', 'bag', 'sell'])
    async def fish_inventory(self, ctx):
        """Look at your fishing inventory.
        Also allows you to sell the fish you previously saved.
        """
        entry = self._get_member_entry(ctx.author)
        fishes = '\n'.join(
            [str(fish) for fish in sorted(entry.inventory)]
            )
        embed = discord.Embed(
            color=EMBED_COLOR,
            description=fishes,
            title='Fish Inventory (WIP)',
            )
        await ctx.send(embed=embed)

    @fish.command(name='top')
    async def fish_top(self, ctx, n: int = 1):
        """Display the n-th best catch guild-wide."""

        sorted_entries = self._get_sorted_best_catch()

        if n < 1:
            raise commands.BadArgument(
                f'Cannot use a negative or zero value (n={n})')

        try:
            top_catch = sorted_entries[-n].best_catch

        except IndexError:
            raise commands.BadArgument(
                f'Not enough entries (n={n} is too big)')

        member = ctx.guild.get_member(top_catch.caught_by_id)
        date_str = top_catch.caught_on.strftime('%b %d %Y')

        embed = discord.Embed(
            title=f'#{n} Top Catch of the Server',
            color=EMBED_COLOR,
        ).set_thumbnail(
            url=member.avatar_url,
        ).add_field(
            name='Top Catch',
            value=top_catch,
        ).add_field(
            name='Caught by',
            value=member.mention,
        ).add_field(
            name='Caught on',
            value=date_str,
        )
        embed.timestamp = datetime.utcnow()

        await ctx.send(embed=embed)

    @fish.error
    async def fish_error(self, ctx, error):
        """Error handling for the fish command.
        In case of CommandOnCooldown error, allow user to check how much
        time is left.
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
                await ctx.message.clear_reaction(hourglass_emoji)

            else:
                retry_after = timedelta(seconds=error.retry_after)

                out_str = (
                    f'You have already tried to fish today, '
                    f'wait for {pretty_print_timedelta(retry_after)}.'
                    )
                # await ctx.author.send(out_str)
                await ctx.send(out_str)

        else:
            raise error

    @fish_top.error
    async def fish_top_error(self, ctx, error):
        """Error handling for the fish_top command."""

        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

        else:
            raise error

    @commands.group(invoke_without_command=True)
    async def weather(self, ctx):
        """Check today's weather."""

        await ctx.send(f'The weather currently is {self.weather}')

    @commands.is_owner()
    @weather.command(name='set')
    async def weather_set(self, ctx, state: int):
        """Set the weather to the given state (positive integer)."""

        self.weather = Weather(state)
        await ctx.send(f'Weather set to {self.weather}')

    def _init_member_entry(self, *, best_catch=None, exp=0, inventory=[]):
        """Return an empty entry for member data."""

        return AttrDict(
            best_catch=best_catch,
            exp=exp,
            inventory=inventory,
            )

    def _get_member_entry(self, member: discord.Member):
        """Return the member entry, or create one if it does not exist yet."""

        try:
            entry = self.data[member.id]

        except KeyError:
            entry = self._init_member_entry()
            self.data[member.id] = entry

        return entry

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

    def _sell_from_inventory(self, member: discord.Member, catch: Fish):
        """Helper function to sell a catch from a member's inventory."""

        entry = self._get_member_entry(member)

        entry.inventory.remove(catch)
        self._give_experience(member, catch.weight)  # saves data here

    def _get_sorted_best_catch(self):
        """Return the list of catches, sorted by weight."""

        entries = list(self.data.values())
        entries = [e for e in entries if e.best_catch is not None]

        return sorted(entries, key=lambda x: x.best_catch)

    def _save_data(self):
        """Save the data to disk (keep it in memory also)."""

        with open(os.path.join(self._cog_path, 'fish_data.pkl'), 'wb') as f:
            pickle.dump(self.data, f)
