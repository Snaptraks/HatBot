import asyncio
import json

import discord
from discord.ext import tasks
import numpy as np

from ..utils.cogs import BasicCog


class Presence(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

        self.change_presence.start()

    def cog_unload(self):
        super().cog_unload()

        self.change_presence.cancel()

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @tasks.loop(hours=1)
    async def change_presence(self):
        """Change the Bot's presence periodically with a random activity."""

        with open('games.json', 'r') as f:
            games = json.load(f)['games']
        game_name = np.random.choice(games)
        await self.bot.change_presence(activity=discord.Game(name=game_name))

    @change_presence.before_loop
    async def change_presence_before(self):
        """Wait until the Bot is fully loaded."""
        await self.bot.wait_until_ready()

    @change_presence.after_loop
    async def change_presence_after(self):
        """Remove the presence on the Bot."""
        await self.bot.change_presence(activity=None)
