import discord
import asyncio
from discord.ext import commands
import numpy as np
import json

from PIL import Image

from ..utils.cogs import FunCog


class Fun(FunCog):
    """Collection of useless but fun commands."""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    async def ping(self, ctx):
        """Replies with Pong!"""
        await ctx.send(':ping_pong: Pong!')

    @commands.command()
    async def marco(self, ctx):
        """Plays Marco Polo with you."""
        r = np.random.randint(100)
        if r == 0:  # tags xplio/polo
            await ctx.send(':water_polo: <@239215575576870914>!')
        else:
            await ctx.send(':water_polo: Polo!')

    @commands.command()
    async def roll(self, ctx, dice='1d6'):
        """Rolls a dice in NdN format."""
        try:
            rolls, limit = map(int, dice.lower().split('d'))
        except Exception:
            await ctx.send('Format has to be in NdN!')
            return
        results = np.random.randint(1, limit + 1, size=rolls)
        if rolls == 1 or rolls > 10:
            outstr = str(results.sum())
        else:
            outstr = ' + '.join(str(r) for r in results)
            outstr += ' = ' + str(results.sum())
        await ctx.send(':game_die: ' + outstr)

    @commands.command(name='8ball')
    async def _8ball(self, ctx, *question):
        """Fortune-telling or advice seeking."""
        r = np.random.randint(50)
        # r = 0  # Force the picture answer
        async with ctx.typing():
            if r != 0:
                question = tuple(sorted(question))
                with open('cogs/Fun/8ball/8ball.json', 'r') as f:
                    answers = json.load(f)['answers']
                if len(question) > 0:
                    i = hash(question) % len(answers)
                    out_ans = answers[i]
                else:
                    out_ans = 'I\'m sorry, what is the question?'

                await asyncio.sleep(1.5)
                await ctx.send(':8ball: ' + out_ans)

            else:
                # sends a fun picture!
                avatar_url = ctx.author.avatar_url_as(format='png')

                async with self.bot.http_session.get(str(avatar_url)) as resp:
                    if resp.status == 200:
                        with open('cogs/Fun/8ball/avatar.png', 'wb') as f:
                            f.write(await resp.content.read())

                # needed files
                avatar = Image.open('cogs/Fun/8ball/avatar.png')
                template = Image.open('cogs/Fun/8ball/magic_8ball_filter.png')
                new = Image.new('RGBA', template.size)

                # big profile picture
                big = avatar.resize((375, 375), Image.ANTIALIAS)
                new.paste(big, (349, 70))

                # small profile picture
                small = avatar.resize((204, 204), Image.ANTIALIAS)
                new.paste(small, (105, 301))

                new.paste(template, mask=template)
                new.save('cogs/Fun/8ball/magic_8ball_avatar.png')
                img = discord.File('cogs/Fun/8ball/magic_8ball_avatar.png')
                await ctx.send(file=img)

    @commands.command(aliases=['rockpaperscissors'])
    async def rps(self, ctx, player_choice=''):
        """Plays Rock Paper Scissors with you.
        Contributed by danjono#8310!"""
        options_text: List[str] = ['rock', 'paper', 'scissors']
        options_emoji: List[str] = [':full_moon:', ':newspaper:', ':scissors:']

        # Convert answer to lowercase
        player_choice = player_choice.lower()

        # Give the bot a random choice
        i = np.random.randint(3)
        bot_choice = options_text[i]
        bot_choice_message = 'I choose ' + bot_choice + '! ' + options_emoji[i]

        if player_choice in options_text:
            await ctx.send(bot_choice_message)

        player_win_message = 'You won! :cry:'
        bot_win_message = 'You lose! :stuck_out_tongue_closed_eyes:'

        # Now to work out who won"
        if player_choice == bot_choice:
            await ctx.send('It\'s a draw!')
        elif (player_choice == 'rock') and (bot_choice == 'scissors'):
            await ctx.send(player_win_message)
        elif (player_choice == 'rock') and (bot_choice == 'paper'):
            await ctx.send(bot_win_message)
        elif (player_choice == 'paper') and (bot_choice == 'rock'):
            await ctx.send(player_win_message)
        elif (player_choice == 'paper') and (bot_choice == 'scissors'):
            await ctx.send(bot_win_message)
        elif (player_choice == 'scissors') and (bot_choice == 'paper'):
            await ctx.send(player_win_message)
        elif (player_choice == 'scissors') and (bot_choice == 'rock'):
            await ctx.send(bot_win_message)
        # Easter eggs!
        elif player_choice == 'spock':
            await ctx.send('Live long and prosper :vulcan:')
        elif player_choice == 'dynamite' or player_choice == 'tnt':
            await ctx.send(bot_choice_message)
            await ctx.send('No wait that\'s cheati.. :fire: :fire: :fire:')
        elif player_choice == 'lizard':
            await ctx.send(':lizard:')
        else:
            await ctx.send('Wait, that\'s not a valid move!')
