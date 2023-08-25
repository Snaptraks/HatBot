from pathlib import Path
import random
import tomllib

import discord
from discord.ext import commands, tasks


PATH = Path(__file__).parent


def load_activities() -> list[discord.CustomActivity]:
    with open(PATH / "activities.toml", "rb") as f:
        data = tomllib.load(f)

    activities = [discord.CustomActivity(name=name) for name in data["activities"]]

    return activities


class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activities = load_activities()
        self.change_presence.start()

    async def cog_unload(self):
        self.change_presence.cancel()
        await self.bot.change_presence(activity=None)

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @tasks.loop(hours=1)
    async def change_presence(self):
        """Change the Bot's presence periodically with a random activity."""

        await self.bot.change_presence(activity=random.choice(self.activities))

    @change_presence.before_loop
    async def change_presence_before(self):
        """Wait until the Bot is fully loaded."""
        await self.bot.wait_until_ready()
