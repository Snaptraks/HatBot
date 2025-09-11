from __future__ import annotations

import random
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from discord.ext.commands import Context
    from snapcogs.bot import Bot


PATH = Path(__file__).parent


def load_activities() -> list[discord.CustomActivity]:
    with (PATH / "activities.toml").open("rb") as f:
        data = tomllib.load(f)

    return [discord.CustomActivity(name=name) for name in data["activities"]]


class Presence(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.activities = load_activities()
        self.change_presence.start()

    async def cog_unload(self) -> None:
        self.change_presence.cancel()
        await self.bot.change_presence(activity=None)

    async def cog_check(self, ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @tasks.loop(hours=1)
    async def change_presence(self) -> None:
        """Change the Bot's presence periodically with a random activity."""

        await self.bot.change_presence(activity=random.choice(self.activities))

    @change_presence.before_loop
    async def change_presence_before(self) -> None:
        """Wait until the Bot is fully loaded."""
        await self.bot.wait_until_ready()
