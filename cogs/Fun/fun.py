import discord
import asyncio
from discord.ext import commands
import numpy as np
import json

from PIL import Image
import requests

from ..utils.cog import FunCog


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
        if r != 0:
            question = tuple(sorted(question))
            with open('cogs/Fun/8ball/8ball.json', 'r') as f:
                answers = json.load(f)['answers']
            if len(question) > 1:
                i = hash(question) % len(answers)
                out_ans = answers[i]
            else:
                out_ans = 'I\'m sorry, what is the question?'

            await ctx.send(':8ball: ' + out_ans)

        else:
            # sends a fun picture!
            member = ctx.author
            channel = ctx.channel

            avatar_url = member.avatar_url_as(format='png')

            Picture_request = requests.get(avatar_url)
            if Picture_request.status_code == 200:
                with open('cogs/Fun/8ball/avatar.png', 'wb') as f:
                    f.write(Picture_request.content)

            # needed files
            avatar = Image.open('cogs/Fun/8ball/avatar.png')
            template = Image.open('cogs/Fun/8ball/magic_8ball_filter.png')
            new = Image.new('RGBA', template.size)

            # big one
            big = avatar.resize((375, 375), Image.ANTIALIAS)
            new.paste(big, (349, 70))

            # small one
            small = avatar.resize((204, 204), Image.ANTIALIAS)
            new.paste(small, (105, 301))

            new.paste(template, mask=template)
            new.save('cogs/Fun/8ball/magic_8ball_avatar.png')
            img = discord.File('cogs/Fun/8ball/magic_8ball_avatar.png')
            await ctx.send(file=img)

    @commands.command()
    async def rps(self, ctx, player_choice):
        """Plays Rock Paper Scissors with you.
        Contributed by danjono#8310!"""
        options_text: List[str] = ['rock', 'paper', 'scissors']
        options_emoji: List[str] = [':full_moon:', ':newspaper:', ':scissors:']

        # Convert answer to lowercase
        player_choice = player_choice.lower()

        # If choice is not valid tell the user
        if player_choice not in options_text:
            await ctx.send('Wait, that\'s not a valid move!')
            return

        i = np.random.randint(3)
        bot_choice = options_text[i]
        await ctx.send('I choose ' + bot_choice + '! ' + options_emoji[i])

        # Now to work out who won"
        if player_choice == bot_choice:
            await ctx.send('It''s a draw!')

        player_win_message = 'You won! :cry:'
        bot_win_message = 'You lose! :stuck_out_tongue_closed_eyes:'

        if (player_choice == 'rock') and (bot_choice == 'scissors'):
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
