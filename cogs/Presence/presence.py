import json
import random

import discord
from discord.ext import commands, tasks


class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        with open("cogs/Presence/presence.json", "r") as f:
            self.activities = json.load(f)

        self.change_presence.start()

    async def cog_unload(self):
        self.change_presence.cancel()
        await self.bot.change_presence(activity=None)

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @tasks.loop(hours=1)
    async def change_presence(self):
        """Change the Bot's presence periodically with a random activity."""

        activity_dict = random.choice(self.activities)
        activity_type = activity_dict["activitytype"]
        activity_name = activity_dict["name"]
        activity = discord.Activity(
            type=discord.ActivityType.try_value(activity_type),
            name=activity_name,
        )

        await self.bot.change_presence(activity=activity)

    @change_presence.before_loop
    async def change_presence_before(self):
        """Wait until the Bot is fully loaded."""
        await self.bot.wait_until_ready()
