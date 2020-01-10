import asyncio
import json
import os

import discord
from discord.ext import commands
import numpy as np

from ..utils.cogs import FunCog


COG_PATH = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(COG_PATH, 'fish.json')) as f:
    FISH_SPECIES = json.load(f)


class Fish:
    """One fish instance."""
    def __init__(self, size, species, smell):
        self.size = size
        self.species = species
        self.smell = smell

    @classmethod
    def from_random(cls, size):
        species = np.random.choice(FISH_SPECIES[size])
        smell = 'bad'
        return cls(size, species, smell)

class FeeshCog(FunCog, name='Feesh'):
    pass
