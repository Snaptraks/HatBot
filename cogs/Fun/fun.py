import asyncio
import json
from typing import Union

import discord
from discord.ext import commands
import numpy as np
from PIL import Image

from ..utils.cogs import FunCog
from ..utils.gifs import random_gif


class Fun(FunCog):
    """Collection of useless but fun commands."""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    async def ping(self, ctx):
        """Reply with Pong!"""

        await ctx.send(':ping_pong: Pong!')

    @commands.command()
    async def marco(self, ctx):
        """Play Marco Polo."""

        r = np.random.randint(100)
        if r == 0:  # tags xplio/polo
            await ctx.send(':water_polo: <@239215575576870914>!')
        else:
            await ctx.send(':water_polo: Polo!')

    @commands.command()
    async def roll(self, ctx, dice='1d6'):
        """Roll a dice in NdN format."""

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

                # Edit template with avatar
                img = await self.bot.loop.run_in_executor(
                    None, self._make_8ball_figure)

                await ctx.send(file=img)

    @commands.command()
    async def hug(self, ctx, *, huggie: Union[discord.Member, str] = None):
        gif_url = await random_gif(self.bot.http_session, 'hug')
        if huggie is None:
            description = (
                f'{self.bot.user.display_name} hugs '
                f'{ctx.author.display_name}! :heart:'
                )
        elif isinstance(huggie, discord.Member):
            description = (
                f'{ctx.author.display_name} hugs '
                f'{huggie.display_name}! :heart:'
                )
        else:  # is str
            description = (
                f'{ctx.author.display_name} hugs '
                f'{huggie}! :heart:'
                )

        embed = discord.Embed(
            title='Have a hug!',
            description=description,
            color=0xFF4CD5,
            )
        embed.set_image(url=gif_url)

        await ctx.send(embed=embed)

    def _make_8ball_figure(self):
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

        return img
