from __future__ import annotations

import itertools
import logging
import random
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from discord import Color, Embed, Interaction, Member, Object, TextChannel, app_commands
from discord.ext import commands, tasks
from rich import print
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from tabulate import tabulate

from .base import (
    RARITY,
    TRICK_OR_TREAT_CHANNEL,
    BaseTreat,
    DuplicateLootError,
)
from .models import Loot, TreatCount, TrickOrTreaterLog
from .views import TrickOrTreaterView

if TYPE_CHECKING:
    from collections.abc import Sequence

    from discord import Message
    from snapcogs.bot import Bot

    from .base import BaseLoot, Inventory, Rarity, TrickOrTreater


PATH = Path(__file__).parent
LOGGER = logging.getLogger(__name__)


def random_rarity(loot_rates: Rarity) -> Literal["common", "uncommon", "rare"]:
    rarity, weights = zip(*loot_rates.items(), strict=True)
    return random.choices(rarity, weights, k=1)[0]


def sort_loot(loot: Sequence[Loot]) -> list[Loot]:
    return sorted(loot, key=lambda x: (RARITY.index(x.rarity), x.name))


class Halloween(commands.Cog):
    """Cog for the Halloween event."""

    halloween = app_commands.Group(
        name="halloween",
        description="Halloween Event commands!",
    )

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        with (PATH / "loot_table.toml").open("rb") as f:
            data = tomllib.load(f)
            self.rarity: Rarity = data["rarity"]
            self.blessed_rarity: Rarity = data["blessed_rarity"]
            self.trick_or_treaters: list[TrickOrTreater] = data["trick_or_treaters"]
            self.treats: list[BaseTreat] = [
                BaseTreat(**treat) for treat in data["treats"]
            ]

        self.send_trick_or_treater.start()
        self.populate_database.start()

    @tasks.loop(count=1)
    async def populate_database(self) -> None:
        LOGGER.debug("Populating database with test data.")
        member = Object(id=337266376941240320)
        member.guild = Object(id=588171715960635393)  # pyright: ignore[reportAttributeAccessIssue]
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

        assert isinstance(channel, TextChannel)

        view = TrickOrTreaterView(
            self.bot,
            trick_or_treater,
            requested_treat,
        )

        view.message = await channel.send(view=view)
        LOGGER.info(f"Sent {trick_or_treater['name']} in {channel}.")

    @send_trick_or_treater.before_loop
    async def send_trick_or_treater_before(self) -> None:
        await self.bot.wait_until_ready()

    @halloween.command(name="loot")
    async def halloween_loot(self, interaction: Interaction[Bot]) -> None:
        """Show the loot you gained."""
        assert isinstance(interaction.user, Member)

        loot = await self._get_member_loot(interaction.user)
        loot_list = [
            sorted(item.name for item in loot if item.rarity == rarity)
            for rarity in RARITY
        ]

        table_data: list[Sequence[str]] = list(
            itertools.zip_longest(
                *loot_list,
                fillvalue="",
            )
        )
        table = tabulate(
            table_data,
            headers=[rarity.title() for rarity in RARITY],
            maxcolwidths=16,
            tablefmt="presto",
        )

        embed = Embed(
            title="Halloween Loot Inventory",
            description=f"```rst\n{table!s}\n```",
            color=Color.orange(),
        ).add_field(
            name="Completion",
            value=(
                "You have:\n"
                f"- {len(loot_list[0])}/{len(self.trick_or_treaters)} Commons\n"
                f"- {len(loot_list[1])}/{len(self.trick_or_treaters)} Uncommons\n"
                f"- {len(loot_list[2])}/{len(self.trick_or_treaters)} Rares\n"
                f"- {len(loot)}/{3 * len(self.trick_or_treaters)} Total!"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    def _get_random_treat(self) -> BaseTreat:
        return random.choice(self.treats)

    def _get_treat_by_name(self, treat_name: str) -> BaseTreat:
        for treat in self.treats:
            if treat.name == treat_name:
                return treat

        msg = f"Unknown treat {treat_name}"
        raise ValueError(msg)

    def _get_random_loot(
        self, trick_or_treater: TrickOrTreater, *, blessed: bool = False
    ) -> BaseLoot:
        rates = self.rarity if not blessed else self.blessed_rarity
        rarity = random_rarity(rates)
        name = trick_or_treater[rarity]

        return {"name": name, "rarity": rarity}

    async def _add_treat_to_inventory(self, treat: BaseTreat, member: Member) -> None:
        LOGGER.debug(f"Added 1 {treat} to {member}.")
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
        LOGGER.debug(f"Removed 1 {treat} from {member}.")
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

    async def _get_member_inventory(self, member: Member) -> Inventory:
        LOGGER.debug(f"Getting inventory of {member}.")
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
        LOGGER.debug(f"Marking {message} responded by {member}.")
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
        LOGGER.debug(f"Checking if allowed to give treat to {message} by {member}.")
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

    async def _add_loot_to_member(self, loot: BaseLoot, member: Member) -> None:
        async with self.bot.db.session() as session, session.begin():
            session.add(
                Loot(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    name=loot["name"],
                    rarity=loot["rarity"],
                )
            )
            try:
                await session.commit()
            except IntegrityError as e:
                raise DuplicateLootError from e

    async def _get_member_loot(self, member: Member) -> list[Loot]:
        async with self.bot.db.session() as session:
            loot = await session.scalars(
                select(Loot).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )

        return list(loot)

    async def _bless(self, member: Member) -> None:
        """Bless the member.
        Gives a loot item as well as an extra treat.
        """

    async def _curse(self, member: Member) -> None:
        """Curse the member.
        Change the nickname of the member to something funny,
        and give them the Cursed role for 15 minutes.
        """
