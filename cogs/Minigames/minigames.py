import asyncio

import discord
from discord.ext import commands

from ..utils.cog import FunCog
from .hangman import Hangman
from .connect4 import Connect4


class Minigames(FunCog):
    """Collection of minigames to play!"""

    def __init__(self, bot):
        super().__init__(bot)
        self._sessions = set()

    def cog_check(self, ctx):
        """Checks if a game is currently running in the channel."""
        return super().cog_check(ctx) and ctx.channel.id not in self._sessions

    async def cog_before_invoke(self, ctx):
        self._sessions.add(ctx.channel.id)

    async def cog_after_invoke(self, ctx):
        self._sessions.remove(ctx.channel.id)

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            # silence `CheckFailure`s because they spam the console
            pass
        else:
            raise error

    @commands.command(hidden=True)
    async def blackjack(self, ctx):
        # Proposed by Kootiepatra
        pass

    @commands.command(hidden=True)
    async def boogle(self, ctx):
        # Proposed by Kootiepatra
        pass

    @commands.command(hidden=True)
    async def connect4(self, ctx, other_player: discord.Member):
        """A game of Connect-4 with another member.
        Each player takes turn in placing a token on the board,
        the winner is the first to put four tokens in a row.
        """
        game = Connect4(ctx, self.bot, other_player)
        await game.play()

    @connect4.error
    async def connect4_error(self, ctx, error):
        """Error handling for connect4 command."""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('You need another player to play that game.')
        else:
            raise error

    @commands.command()
    async def hangman(self, ctx):
        """A game of Hangman with a random word.
        You guess letters by typing them in chat.
        """
        game = Hangman(ctx, self.bot)
        await game.play()

    @commands.command(hidden=True)
    async def higherlower(self, ctx):
        # Proposed by Outerwebs
        pass

    @commands.command(hidden=True)
    async def mancala(self, ctx):
        # Proposed by Princerbang
        pass

    @commands.command(hidden=True)
    async def tictactoe(self, ctx):
        # Proposed by Princerbang
        pass

    @commands.command(hidden=True)
    async def wordsearch(self, ctx):
        # Proposed by Tant
        pass
