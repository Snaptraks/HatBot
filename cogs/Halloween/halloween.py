from __future__ import annotations

import logging
import random
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from rich import print
from sqlalchemy import select

from .base import TRICK_OR_TREAT_CHANNEL, BaseTreat
from .models import TreatCount, TrickOrTreaterLog
from .views import TrickOrTreaterView

if TYPE_CHECKING:
    from discord import Member, Message
    from snapcogs.bot import Bot

    from .base import Inventory, LootRates, TrickOrTreater


PATH = Path(__file__).parent
LOGGER = logging.getLogger(__name__)


def random_loot(loot_rates: LootRates) -> str:
    rarity, weights = zip(*loot_rates.items(), strict=True)
    return random.choices(rarity, weights, k=1)[0]


class Halloween(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        with (PATH / "loot_table.toml").open("rb") as f:
            data = tomllib.load(f)
            self.rarity: LootRates = data["rarity"]
            self.trick_or_treaters: list[TrickOrTreater] = data["trick_or_treaters"]
            self.treats: list[BaseTreat] = [
                BaseTreat(**treat) for treat in data["treats"]
            ]

        self.send_trick_or_treater.start()
        self.populate_database.start()

    @tasks.loop(count=1)
    async def populate_database(self) -> None:
        member = discord.Object(id=337266376941240320)
        member.guild = discord.Object(id=588171715960635393)  # pyright: ignore[reportAttributeAccessIssue]
        async with self.bot.db.session() as session, session.begin():
            for treat in self.treats * 2:
                await self._add_treat_to_inventory(treat, member)  # pyright: ignore[reportArgumentType]

    @populate_database.before_loop
    async def populate_database_before(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def send_trick_or_treater(self) -> None:
        trick_or_treater = random.choice(self.trick_or_treaters)
        requested_treat = random.choice(self.treats)
        channel = self.bot.get_channel(TRICK_OR_TREAT_CHANNEL)

        assert isinstance(channel, discord.TextChannel)

        view = TrickOrTreaterView(
            self.bot,
            trick_or_treater,
            requested_treat,
        )

        view.message = await channel.send(view=view)
        LOGGER.debug(f"Sent {trick_or_treater['name']} in {channel}.")

    @send_trick_or_treater.before_loop
    async def send_trick_or_treater_before(self) -> None:
        await self.bot.wait_until_ready()

    def _get_treat_by_name(self, treat_name: str) -> BaseTreat:
        for treat in self.treats:
            if treat.name == treat_name:
                return treat

        msg = f"Unknown treat {treat_name}"
        raise ValueError(msg)

    async def _add_treat_to_inventory(self, treat: BaseTreat, member: Member) -> None:
        async with self.bot.db.session() as session, session.begin():
            # check if the member has the treat already
            treat_count = await session.scalar(
                select(TreatCount).filter_by(
                    name=treat.name,
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )

            # if the member doesn't have it, create the entry
            if treat_count is None:
                treat_count = TreatCount(
                    name=treat.name,
                    emoji=treat.emoji,
                    guild_id=member.guild.id,
                    user_id=member.id,
                    amount=1,
                )
                session.add(treat_count)

            # if they do, increment by one
            else:
                treat_count.amount += 1
                await session.commit()

    async def _remove_treat_from_inventory(
        self, treat: BaseTreat, member: Member
    ) -> None:
        async with self.bot.db.session() as session, session.begin():
            treat_count = await session.scalar(
                select(TreatCount).filter_by(
                    name=treat.name,
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )
            if treat_count is not None:
                treat_count.amount -= 1

            await session.commit()

    async def _get_user_inventory(self, member: Member) -> Inventory:
        async with self.bot.db.session() as session:
            inventory = await session.scalars(
                select(TreatCount)
                .order_by(TreatCount.name)
                .filter_by(guild_id=member.guild.id)
                .filter_by(user_id=member.id)
                .where(TreatCount.amount > 0)
            )
            return list(inventory)

    async def _mark_trick_or_treater_by_member(
        self, member: Member, message: Message
    ) -> None:
        async with self.bot.db.session() as session, session.begin():
            log = TrickOrTreaterLog(
                guild_id=member.guild.id,
                user_id=member.id,
                message_id=message.id,
            )
            session.add(log)
            await session.commit()

    async def _check_member_able_to_give(
        self, member: Member, message: Message
    ) -> bool:
        async with self.bot.db.session() as session:
            check = await session.scalar(
                select(TrickOrTreaterLog).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    message_id=message.id,
                )
            )

            # If check is None, the member has not given a treat yet,
            # therefore are allowed. If check is an instance of TrickOrTreaterLog,
            # they have given a treat already, therefore are not allowed again.
            return check is None
