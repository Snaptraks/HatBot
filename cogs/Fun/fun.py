import asyncio
import io
import json
import os
from typing import Union

import discord
from discord.ext import commands
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..utils.cogs import BasicCog
from ..utils.gifs import random_gif


class Fun(BasicCog):
    """Collection of useless but fun commands."""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    async def ping(self, ctx):
        """Reply with Pong!"""

        await ctx.send(":ping_pong: Pong!")

    @commands.command()
    async def marco(self, ctx):
        """Play Marco Polo."""

        r = np.random.randint(100)
        if r == 0:  # tags xplio/polo
            await ctx.send(":water_polo: <@239215575576870914>!")
        else:
            await ctx.send(":water_polo: Polo!")

    @commands.command()
    async def roll(self, ctx, dice="1d6"):
        """Roll a dice in NdN format."""

        try:
            rolls, limit = map(int, dice.lower().split('d'))
        except Exception:
            await ctx.send("Format has to be in NdN!")
            return
        results = np.random.randint(1, limit + 1, size=rolls)
        if rolls == 1 or rolls > 10:
            outstr = str(results.sum())
        else:
            outstr = " + ".join(str(r) for r in results)
            outstr += " = " + str(results.sum())
        await ctx.send(f":game_die: {outstr}")

    @commands.command(name='8ball')
    async def _8ball(self, ctx, *question):
        """Fortune-telling or advice seeking."""

        r = np.random.randint(50)
        # r = 0  # Force the picture answer
        async with ctx.typing():
            if r != 0:
                question = tuple(sorted(question))
                with open("cogs/Fun/8ball/8ball.json", 'r') as f:
                    answers = json.load(f)['answers']
                if len(question) > 0:
                    i = hash(question) % len(answers)
                    out_ans = answers[i]
                else:
                    out_ans = "I'm sorry, what is the question?"

                await asyncio.sleep(1.5)
                await ctx.send(f":8ball: {out_ans}")

            else:
                # sends a fun picture!
                avatar_url = ctx.author.avatar_url_as(format="png")

                async with self.bot.http_session.get(str(avatar_url)) as resp:
                    if resp.status == 200:
                        with open("cogs/Fun/8ball/avatar.png", 'wb') as f:
                            f.write(await resp.content.read())

                # Edit template with avatar
                img = await self.bot.loop.run_in_executor(
                    None, self._make_8ball_figure)

                await ctx.send(file=img)

    @commands.command(aliases=["hugs"])
    async def hug(self, ctx, *, huggie: Union[discord.Member, str] = None):
        """Send a hug to someone or get one yourself!"""

        embed = await self._action_embed('hug', ctx.author, huggie)

        await ctx.send(embed=embed)

    @commands.command()
    async def slap(self, ctx, *, slappie: Union[discord.Member, str] = None):
        """Slap someone! Or get slapped yourself!"""

        embed = await self._action_embed('slap', ctx.author, slappie)

        await ctx.send(embed=embed)

    @commands.command(aliases=["votekick"])
    async def kick(self, ctx, *, kickie: Union[discord.Member, str] = None):
        """Kick someone (not really)! Or get kicked yourself!"""

        embed = await self._action_embed('kick', ctx.author, kickie)

        await ctx.send(embed=embed)

    async def _action_embed(self, action: str, author: discord.Member,
                            destination: Union[discord.Member, str]):
        """Helper function to create the embed for one of the
        action commands.
        """
        gif_url = await random_gif(self.bot.http_session, action)
        description = "{1} {0}s {2}!"
        if destination is None:
            description = description.format(
                action,
                self.bot.user.mention,
                author.mention,
            )
        elif isinstance(destination, discord.Member):
            description = description.format(
                action,
                author.mention,
                destination.mention,
            )
        else:  # is str
            description = description.format(
                action,
                author.mention,
                destination,
            )

        color = {
            'hug': 0xFF4CD5,
            'slap': 0xFFCC4D,
            'kick': 0xFFCC4D,
        }

        emoji = {
            'hug': ":heart:",
            'slap': ":hand_splayed:",
            'kick': ":foot:",
        }

        embed = discord.Embed(
            title=f"Have a {action}!",
            description=f"{description} {emoji[action]}",
            color=color[action],
        )
        embed.set_image(url=gif_url)

        return embed

    @commands.command(name="frenchwalrus", aliases=["fw"])
    async def french_walrus(self, ctx):
        """Send the French Walrus emoji from 2020's April Fools."""

        emoji = self.bot.get_emoji(694918585486671962)
        await ctx.send(emoji)

    def _make_8ball_figure(self):
        # needed files
        avatar = Image.open("cogs/Fun/8ball/avatar.png")
        template = Image.open("cogs/Fun/8ball/magic_8ball_filter.png")
        new = Image.new('RGBA', template.size)

        # big profile picture
        big = avatar.resize((375, 375), Image.ANTIALIAS)
        new.paste(big, (349, 70))

        # small profile picture
        small = avatar.resize((204, 204), Image.ANTIALIAS)
        new.paste(small, (105, 301))

        new.paste(template, mask=template)
        new.save("cogs/Fun/8ball/magic_8ball_avatar.png")
        img = discord.File("cogs/Fun/8ball/magic_8ball_avatar.png")

        return img

    @commands.command(hidden=True)
    @commands.cooldown(1, 3600, commands.BucketType.guild)
    async def play(self, ctx):
        await ctx.send(
            f"This ain't fucking Twitch, {ctx.author.display_name}."
        )

    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("I do not know of a command like that...")

    @commands.command()
    async def bonk(self, ctx, member: discord.Member, *, text=None):
        """Bonk a member, and add a message!
        Due to the member argument not being last, you will have to
        use a mention (@User Here) or quote "User Here" their name
        if it contains spaces.
        """

        avatar_url = str(member.avatar_url_as(format="png"))
        async with self.bot.http_session.get(avatar_url) as resp:
            if resp.status == 200:
                avatar = io.BytesIO(await resp.content.read())
                avatar.seek(0)

        out = await self.bot.loop.run_in_executor(
            None, self.bonkify, avatar, text)

        await ctx.send(file=discord.File(out, filename="bonk.png"))

    @bonk.error
    async def bonk_error(self, ctx, error):
        "Error handler for the bonk command."""

        if isinstance(error, (commands.MemberNotFound,
                              commands.MissingRequiredArgument)):

        else:
            raise error

    def bonkify(self, avatar_bytes, text=None):
        avatar = Image.open(avatar_bytes)
        template = Image.open(os.path.join(
            self._cog_path, "bonk_template.png"))

        new = Image.new("RGBA", template.size)

        # under the bat
        head = avatar.resize((200, 200), Image.ANTIALIAS)
        new.paste(head, (425, 235))

        new.paste(template, mask=template)

        if text is not None:
            # add text
            draw = ImageDraw.Draw(new)
            font = ImageFont.truetype("impact.ttf", 38)
            stroke_width = 2
            w, h = font.getsize(text, stroke_width=stroke_width)
            mx, my = (380, 60)  # middle
            x, y = mx - w // 2, my - h // 2

            draw.text(
                (x, y),
                text,
                font=font,
                fill=(255, 255, 255),
                stroke_width=stroke_width,
                stroke_fill=(0, 0, 0),
            )

        edited = io.BytesIO()
        new.save(edited, format="png")
        edited.seek(0)

        return edited
