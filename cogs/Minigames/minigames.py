import asyncio

import discord
from discord.ext import commands

from ..utils.cog import FunCog
from .hangman import Hangman

class Minigames(FunCog):
    """Collection of minigames to play!"""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    async def blackjack(self, ctx):
        # Proposed by Kootiepatra
        pass

    @commands.command()
    async def boogle(self, ctx):
        # Proposed by Kootiepatra
        pass

    @commands.command()
    async def connect4(self, ctx):
        pass

    @commands.command()
    async def hangman(self, ctx):
        game = Hangman(ctx, self.bot)
        await game.play()
        pass

    @commands.command()
    async def higherlower(self, ctx):
        # Proposed by Outerwebs
        pass

    @commands.command()
    async def mancala(self, ctx):
        # Proposed by Princerbang
        pass

    @commands.command()
    async def tictactoe(self, ctx):
        # Proposed by Princerbang
        pass

    @commands.command()
    async def wordsearch(self, ctx):
        # Proposed by Tant
        pass
