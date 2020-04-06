import asyncio
import json
import os

import discord
from discord.ext import commands, tasks
import numpy as np

from ..utils.cogs import BasicCog


class ACNH(BasicCog):
    """Module for actions related to Animal Crossing: New Horizons."""

    def __init__(self, bot):
        super().__init__(bot)
        self.presence_task.start()

        with open(os.path.join(self._cog_path, 'quotes.json'), 'r') as f:
            self.quotes = json.load(f)

    @tasks.loop(hours=1)
    async def presence_task(self):
        """Change the presence of the bot once fully loaded."""

        game = discord.Game(name='Animal Crossing: New Horizons')
        await self.bot.change_presence(activity=game)

    @presence_task.before_loop
    async def presence_task_before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener(name='on_message')
    async def on_mention(self, message):
        """Send a funny reply when the bot is mentionned."""

        ctx = await self.bot.get_context(message)

        if ctx.me.mentioned_in(message) \
                and not message.author.bot \
                and not message.mention_everyone \
                and not message.content.startswith(self.bot.command_prefix):

            out_str = np.random.choice(self.quotes)
            await self.send_typing_delay(ctx.channel)
            await ctx.send(out_str)

    async def send_typing_delay(self, channel):
        r = np.random.rand()  # [0, 1)
        t = 1.5 * r + 0.5  # [0.5, 2)
        await channel.trigger_typing()
        await asyncio.sleep(t)
