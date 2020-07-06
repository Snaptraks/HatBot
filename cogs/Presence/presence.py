import asyncio
import json

import discord
from discord.ext import tasks
import numpy as np

from ..utils.cogs import BasicCog


class Presence(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)

        with open('cogs/Presence/presence.json', 'r') as f:
            self.activities = json.load(f)

        self.change_presence.start()

    def cog_unload(self):
        super().cog_unload()

        self.change_presence.cancel()

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @tasks.loop(hours=1)
    async def change_presence(self):
        """Change the Bot's presence periodically with a random activity."""

        activity_dict = np.random.choice(self.activities)
        type = activity_dict['activitytype']
        name = activity_dict['name']
        activity = discord.Activity(
            type=discord.ActivityType.try_value(type),
            name=name,
            )

        await self.bot.change_presence(activity=activity)

    @change_presence.before_loop
    async def change_presence_before(self):
        """Wait until the Bot is fully loaded."""
        await self.bot.wait_until_ready()

    @change_presence.after_loop
    async def change_presence_after(self):
        """Remove the presence on the Bot."""
        await self.bot.change_presence(activity=None)
