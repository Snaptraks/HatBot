import asyncio

import discord
from discord.ext import commands

from ..utils.cog import FunCog
from .hangman import Hangman


class Minigames(FunCog):
    """Collection of minigames to play!"""

    def __init__(self, bot):
        super().__init__(bot)
        self.is_game_running = False

    def cog_check(self, ctx):
        """Checks if a game is currently running."""
        return super().cog_check(ctx) and not self.is_game_running

    async def cog_before_invoke(self, ctx):
        self.is_game_running = True

    async def cog_after_invoke(self, ctx):
        self.is_game_running = False

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            # silence `CheckFailure`s because they spam the console
            pass
        else:
            raise error

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