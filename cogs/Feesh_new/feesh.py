import asyncio
import json
import os
import pickle

import discord
from discord.ext import commands, tasks
import numpy as np

from ..utils.cogs import FunCog
from ..utils.dicts import AttrDict


COG_PATH = os.path.dirname(__file__)

with open(os.path.join(COG_PATH, 'fish.json')) as f:
    FISH_SPECIES = AttrDict.from_nested_dict(json.load(f))

SMELLS = [
    'delightful',
    'alright',
    'not that bad',
    'not good',
    'bad',
    'horrible',
    'ungodly',
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


class Fish:
    """One fish instance."""
    def __init__(self, size, species, smell, weight):
        self.size = size
        self.species = species
        self.smell = smell
        self.weight = weight

    @classmethod
    def from_random(cls, weather):
        """Create a fish randomly based on the weather."""

        # need a better way to calculate probabilities (p)...
        p = [x.odds for x in FISH_SPECIES.values()]
        for i in range(1, 4):  # giant and above are more common
            p[-i] += weather.state
        p = np.asarray(p) / sum(p)

        size = np.random.choice(list(FISH_SPECIES.keys()), p=p)
        species = np.random.choice(FISH_SPECIES[size].species)
        smell = np.random.choice(SMELLS)
        weight = np.random.uniform(*FISH_SPECIES[size].weight)

        return cls(size, species, smell, weight)

    def __repr__(self):
        return f'{self.size.title()} {self.species} ({self.weight:.3f} kg)'

    def __lt__(self, other):
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
    def __init__(self, bot):
        super().__init__(bot)
        self.change_weather.start()

        try:
            with open(os.path.join(self._cog_path, 'fish_data.pkl'), 'rb') as f:
                self.data = pickle.load(f)
        except FileNotFoundError:
            self.data = AttrDict()

    def cog_unload(self):
        super().cog_unload()
        self.change_weather.cancel()

        with open(os.path.join(self._cog_path, 'fish_data.pkl'), 'wb') as f:
            pickle.dump(self.data, f)

    def cog_check(self, ctx):
        return bool(ctx.guild) and super().cog_check(ctx)

    @tasks.loop(hours=24)
    async def change_weather(self):
        """Change the weather randomly every day."""

        self.weather = Weather.from_random()

    @commands.group(aliases=['feesh', 'f'], invoke_without_command=True)
    async def fish(self, ctx):
        await ctx.send(Fish.from_random(self.weather))

    @commands.command()
    async def fishing(self, ctx):
        """Go fishing and get a random catch."""

        await ctx.send('\U0001f3a3')

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
