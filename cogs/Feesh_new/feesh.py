import asyncio
import json
import os

import discord
from discord.ext import commands
import numpy as np

from ..utils.cogs import FunCog
from ..utils.dicts import AttrDict


COG_PATH = os.path.dirname(os.path.abspath(__file__))

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


class Fish:
    """One fish instance."""
    def __init__(self, size, species, smell):
        self.size = size
        self.species = species
        self.smell = smell

    @classmethod
    def from_random(cls, weather):
        """Create a fish randomly based on the weather."""

        # need a better way to calculate probabilities (p)...
        p = [x.odds for x in FISH_SPECIES.values()]
        for i in range(1, 4):  # giant and above are more common
            p[-i] += weather.state
        p = np.asarray(p) / sum(p)
        print(p)

        size = np.random.choice(list(FISH_SPECIES.keys()), p=p)
        species = np.random.choice(FISH_SPECIES[size].species)
        smell = np.random.choice(SMELLS)

        return cls(size, species, smell)

    def __repr__(self):
        return f'{self.size.title()} {self.species} ({self.smell} smell)'


class FeeshCog(FunCog, name='Feesh'):
    pass
