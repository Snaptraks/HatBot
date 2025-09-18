from __future__ import annotations

import random
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from rich import print
from sqlalchemy import select

from . import base
from .models import Treat
from .views import TrickOrTreaterView

if TYPE_CHECKING:
    from discord import Member
    from snapcogs.bot import Bot

    from .base import LootRates, TrickOrTreater


PATH = Path(__file__).parent


def random_loot(loot_rates: LootRates) -> str:
    rarity, weights = zip(*loot_rates.items(), strict=True)
    return random.choices(rarity, weights, k=1)[0]


class Halloween(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        with (PATH / "loot_table.toml").open("rb") as f:
            data = tomllib.load(f)
            self.loot_rates: LootRates = data["rates"]
            self.trick_or_treaters: list[TrickOrTreater] = data["loot"]

        self.send_trick_or_treater.start()

    async def cog_load(self) -> None:
        async with self.bot.db.session() as session, session.begin():
            for treat_emoji in ["🍬", "🍭", "🪅", "🍫", "🍿", "🍩"]:
                session.add(
                    Treat(
                        guild_id=588171715960635393,
                        user_id=337266376941240320,
                        name=treat_emoji,
                        emoji=treat_emoji,
                    )
                )

    @tasks.loop(count=1)
    async def send_trick_or_treater(self) -> None:
        trick_or_treater = random.choice(self.trick_or_treaters)
        channel = self.bot.get_channel(base.TRICK_OR_TREAT_CHANNEL)

        assert isinstance(channel, discord.TextChannel)

        await channel.send(view=TrickOrTreaterView(self.bot, trick_or_treater))

    @send_trick_or_treater.before_loop
    async def send_trick_or_treater_before(self) -> None:
        await self.bot.wait_until_ready()

    async def _get_user_inventory(self, member: Member) -> list[Treat]:
        async with self.bot.db.session() as session:
            inventory = await session.scalars(
                select(Treat)
                .filter_by(guild_id=member.guild.id)
                .filter_by(user_id=member.id)
            )
            return list(inventory)
