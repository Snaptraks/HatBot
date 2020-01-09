import asyncio
import json
import os

import discord
from discord.ext import commands

from ..utils.cogs import FunCog


COG_PATH = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(COG_PATH, 'fish.json')) as f:
    FISH_SPECIES = json.load(f)


class Fish:
    """One fish instance."""
    pass


class FeeshCog(FunCog, name='Feesh'):
    pass
