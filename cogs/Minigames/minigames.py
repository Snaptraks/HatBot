import asyncio

import discord
from discord.ext import commands
import numpy as np

from ..utils.cogs import FunCog
from .blackjack import Blackjack
from .connect4 import Connect4
from .hangman import Hangman
from .highlow import HighLow
from .tictactoe import TicTacToe


class Minigames(FunCog):
    """Collection of minigames to play!"""

    def __init__(self, bot):
        super().__init__(bot)
        self._sessions = set()

    def cog_check(self, ctx):
        """Check if a game is currently running in the channel."""

        return super().cog_check(ctx) and ctx.channel.id not in self._sessions

    async def cog_before_invoke(self, ctx):
        self._sessions.add(ctx.channel.id)

    async def cog_after_invoke(self, ctx):
        self._sessions.remove(ctx.channel.id)

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            # silence `CheckFailure`s because they spam the console
            pass

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("You need another player to play that game.")

        elif isinstance(error, commands.BadArgument):
            await ctx.reply(error)

        else:
            raise error

    @commands.command()
    async def blackjack(self, ctx):
        """A single hand of Blackjack.
        The player plays against the dealer (bot) for one hand.
        Proposed by Kootiepatra.
        """
        game = Blackjack(ctx, self.bot)
        await game.play()

    @commands.command(hidden=True)
    async def boogle(self, ctx):
        # Proposed by Kootiepatra
        pass

    @commands.command()
    async def connect4(self, ctx, other_player: discord.Member):
        """A game of Connect-4 with another member.
        Each player takes turn in placing a token on the board,
        the winner is the first to put four tokens in a row.
        """
        if other_player.bot or other_player == ctx.author:
            raise commands.BadArgument(
                "Cannot play a game against that member.")

        game = Connect4(ctx, self.bot, other_player)
        await game.play()

    @commands.command()
    async def hangman(self, ctx):
        """A game of Hangman with a random word.
        You guess letters by typing them in chat.
        """
        game = Hangman(ctx, self.bot)
        await game.play()

    @commands.command(name="higherlower", aliases=["highlow", "hilo"])
    async def higher_lower(self, ctx):
        """A game of Higher-or-Lower.
        The player plays against the dealer (bot) for half a deck of cards.
        Proposed by Outerwebs.
        """
        game = HighLow(ctx, self.bot)
        await game.play()

    @commands.command(hidden=True)
    async def mancala(self, ctx):
        # Proposed by Princerbang
        pass

    @commands.command(name="tictactoe")
    async def tic_tac_toe(self, ctx, other_player: discord.Member = None):
        """A game of Tic-Tac-Toe with another member.
        Proposed by Princerbang.
        """
        if other_player.bot or other_player == ctx.author:
            raise commands.BadArgument(
                "Cannot play a game against that member.")

        game = TicTacToe(ctx, self.bot, other_player)
        await game.play()

    @commands.command(hidden=True)
    async def wordsearch(self, ctx):
        # Proposed by Tant
        pass

    @commands.command(name="rps", aliases=["rockpaperscissors"])
    async def rock_paper_scissors(self, ctx, player_choice=''):
        """Play a game of Rock Paper Scissors.
        Contributed by danjono#8310!
        """
        options_text = ["rock", "paper", "scissors"]
        options_emoji = [":full_moon:", ":newspaper:", ":scissors:"]

        # Convert answer to lowercase
        player_choice = player_choice.lower()

        # Give the bot a random choice
        i = np.random.randint(3)
        bot_choice = options_text[i]
        bot_choice_message = f"I choose {bot_choice}! {options_emoji[i]}"

        if player_choice in options_text:
            await ctx.reply(bot_choice_message)

        player_win_message = "You won! :cry:"
        bot_win_message = "You lose! :stuck_out_tongue_closed_eyes:"

        # Now to work out who won"
        if player_choice == bot_choice:
            await ctx.reply("It's a draw!")
        elif (player_choice == "rock") and (bot_choice == "scissors"):
            await ctx.reply(player_win_message)
        elif (player_choice == "rock") and (bot_choice == "paper"):
            await ctx.reply(bot_win_message)
        elif (player_choice == "paper") and (bot_choice == "rock"):
            await ctx.reply(player_win_message)
        elif (player_choice == "paper") and (bot_choice == "scissors"):
            await ctx.reply(bot_win_message)
        elif (player_choice == "scissors") and (bot_choice == "paper"):
            await ctx.reply(player_win_message)
        elif (player_choice == "scissors") and (bot_choice == "rock"):
            await ctx.reply(bot_win_message)
        # Easter eggs!
        elif player_choice == "spock":
            await ctx.reply("Live long and prosper :vulcan:")
        elif player_choice == "dynamite" or player_choice == "tnt":
            await ctx.reply(bot_choice_message)
            await ctx.reply("No wait that's cheati.. :fire: :fire: :fire:")
        elif player_choice == "lizard":
            await ctx.reply(":lizard:")
        else:
            await ctx.reply("Wait, that's not a valid move!")
