from __future__ import annotations

import asyncio
import itertools
import logging
import random
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from discord import (
    Color,
    Embed,
    Forbidden,
    Member,
    TextChannel,
    app_commands,
    utils,
)
from discord.ext import commands, tasks
from rich import print
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from tabulate import tabulate

from .base import (
    CURSE_LENGTH,
    RARITY,
    TREAT_SPAWN_RATE,
    TRICK_OR_TREAT_CHANNEL,
    TRICK_OR_TREATER_LENGTH,
    TRICK_OR_TREATER_SPAWN_RATE,
    BaseTreat,
    DuplicateLootError,
    fmt_loot,
    random_integer,
)
from .models import (
    Event,
    EventLog,
    Loot,
    OriginalName,
    TreatCount,
    TrickOrTreaterMessage,
)
from .views import TreatsView, TrickOrTreaterView

if TYPE_CHECKING:
    from collections.abc import Sequence

    from discord import Guild, Interaction, Message, Reaction
    from snapcogs.bot import Bot

    from .base import BaseLoot, CursedNames, Inventory, Rarity, TrickOrTreater


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

        with (PATH / "assets.toml").open("rb") as f:
            data = tomllib.load(f)
            self.rarity: Rarity = data["rarity"]
            self.blessed_rarity: Rarity = data["blessed_rarity"]
            self.trick_or_treaters: list[TrickOrTreater] = data["trick_or_treaters"]
            self.treats: list[BaseTreat] = [
                BaseTreat(**treat) for treat in data["treats"]
            ]
            self.cursed_names: CursedNames = data["cursed_names"]

        self.trick_or_treater_spawner.start()

        self.curse_tasks: set[asyncio.Task] = set()

        self.trick_or_treater_timer: int = 0

    @tasks.loop(minutes=1)
    async def trick_or_treater_spawner(self) -> None:
        self.trick_or_treater_timer += 1

    @commands.Cog.listener(name="on_message")
    async def send_trick_or_treater(self, message: Message) -> None:
        if (
            message.channel.id != TRICK_OR_TREAT_CHANNEL
            or message.author.bot
            or message.interaction_metadata is not None
        ):
            return

        r = random_integer(TRICK_OR_TREATER_SPAWN_RATE)
        if r < self.trick_or_treater_timer:
            LOGGER.debug(
                f"Spawned Trick-or-treater at {utils.utcnow()} "
                f"({r=}, {self.trick_or_treater_timer=})"
            )
            self.trick_or_treater_timer = -TRICK_OR_TREATER_LENGTH
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

            await self._log_event(Event.SPAWN_TRICK_OR_TREATER, guild=channel.guild)

        else:
            LOGGER.debug(f"No spawn. {r=} {self.trick_or_treater_timer=}")

    @commands.Cog.listener(name="on_message")
    async def random_treat_drop(self, message: Message) -> None:
        if (
            message.author.bot
            or message.interaction_metadata is not None
            or message.channel.guild is None
        ):
            return

        assert isinstance(message.author, Member)

        r = random.random()
        if r <= TREAT_SPAWN_RATE:
            LOGGER.debug(f"Setting treat drop to {message}")
            treat = self._get_random_treat()

            def check(reaction: Reaction, member: Member) -> bool:
                return (
                    member == message.author
                    and reaction.message.id == message.id
                    and reaction.emoji == treat.emoji
                )

            await message.add_reaction(treat.emoji)
            await self.bot.wait_for("reaction_add", check=check)

            await self._add_treat_to_inventory(treat, message.author)
            await message.clear_reactions()

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
            table_data or loot_list,  # prevent error when there's no loot
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

    @halloween.command(name="treats")
    async def halloween_treats(self, interaction: Interaction[Bot]) -> None:
        """Show your treats."""
        assert isinstance(interaction.user, Member)

        treats = await self._get_member_inventory(interaction.user)

        embed = Embed(
            title="Treats Inventory",
            description="\n".join(
                f"{treat.emoji} {treat.name} ({treat.amount})"
                for treat in treats
                if treat.amount > 0
            ),
            color=Color.orange(),
        ).add_field(
            name="Total:",
            value=f"{sum(treat.amount for treat in treats)} Treats",
        )

        await interaction.response.send_message(
            embed=embed,
            view=TreatsView(treats),
            ephemeral=True,
        )

    @halloween.command(name="scoreboard")
    async def halloween_scoreboard(self, interaction: Interaction[Bot]) -> None:
        """Display the members with the highest number of loot items."""
        assert interaction.guild is not None

        scores = await self._get_guild_score(interaction.guild)

        table_data: list[tuple[int, int, str]] = []
        for rank, (user_id, amount) in enumerate(scores):
            member = interaction.guild.get_member(user_id)
            table_data.append(
                (
                    rank + 1,
                    amount,
                    member.display_name if member is not None else "Unknown member",
                )
            )

        table = tabulate(
            table_data,
            headers=["Rank", "Loots", "Member"],
            tablefmt="presto",
        )

        embed = Embed(
            title=f"Halloween Scoreboard • {interaction.guild.name}",
            description=f"```rst\n{table}\n```",
            color=Color.orange(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _get_treat_by_name(self, treat_name: str) -> BaseTreat:
        for treat in self.treats:
            if treat.name == treat_name:
                return treat

        msg = f"Unknown treat {treat_name}"
        raise ValueError(msg)

    def _get_random_treat(self) -> BaseTreat:
        return random.choice(self.treats)

    def _get_random_loot(
        self, trick_or_treater: TrickOrTreater, *, blessed: bool = False
    ) -> BaseLoot:
        rates = self.rarity if not blessed else self.blessed_rarity
        rarity = random_rarity(rates)
        name = trick_or_treater[rarity]

        return {"name": name, "rarity": rarity}

    def _get_random_cursed_name(self) -> str:
        first_name = random.choice(self.cursed_names["first_names"])
        last_name = random.choice(self.cursed_names["last_names"])
        emoji = random.choice(self.cursed_names["emojis"])
        return f"{first_name} {last_name} {emoji}"

    async def _give_normal_loot(
        self, member: Member, trick_or_treater: TrickOrTreater
    ) -> str:
        """Give a normal loot item."""

        loot = self._get_random_loot(trick_or_treater)
        try:
            await self._add_loot_to_member(loot, member)

        except DuplicateLootError:
            success_message = (
                f"You already had a {fmt_loot(loot)}, you don't get another one."
            )
        else:
            success_message = f"Here's a {fmt_loot(loot)} as a gift!"

        return success_message

    async def _give_blessing(
        self, member: Member, trick_or_treater: TrickOrTreater
    ) -> str:
        """Give a blessed loot to the member.

        Give a higher rarity loot to the member and a treat, or two treats if
        they already have the loot item.
        """
        loot = self._get_random_loot(trick_or_treater, blessed=True)
        treat = self._get_random_treat()
        await self._add_treat_to_inventory(treat, member)

        try:
            await self._add_loot_to_member(loot, member)

        except DuplicateLootError:
            success_message = (
                f"You already had a {fmt_loot(loot)}, so you get two {treat}s!"
            )
            await self._add_treat_to_inventory(treat, member)

        else:
            success_message = f"You can have my {fmt_loot(loot)} and {treat} as a gift!"

        return success_message

    async def _give_curse(self, member: Member) -> str:
        """Curse the member.

        Change the nickname of the member to something funny,
        and give them the Cursed role for 15 minutes.
        """
        cursed_name = self._get_random_cursed_name()
        task = asyncio.create_task(
            self._curse_task(
                member,
                cursed_name,
            )
        )
        self.curse_tasks.add(task)
        task.add_done_callback(self.curse_tasks.discard)

        await self._log_event(Event.GET_CURSE, member=member)

        return cursed_name

    async def _curse_task(self, member: Member, cursed_name: str) -> None:
        LOGGER.debug(f"Cursing {member} for {CURSE_LENGTH} minutes with {cursed_name}.")
        cursed_role = utils.get(member.guild.roles, name="Cursed")
        await self._save_member_display_name(member)
        try:
            await member.edit(nick=cursed_name)
        except Forbidden:
            LOGGER.warning(f"Could not change nickname of {member}, returning early")
            return

        if cursed_role:
            await member.add_roles(cursed_role, reason="Halloween Curse!")

        await asyncio.sleep(CURSE_LENGTH * 60)  # 15 minutes

        LOGGER.debug(f"Resetting {member} to original nickname.")
        original_name = await self._get_member_display_name(member)
        await member.edit(nick=original_name)
        if cursed_role:
            await member.remove_roles(cursed_role)

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

        await self._log_event(Event.COLLECT_TREAT, member=member)

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

        await self._log_event(Event.GIVE_TREAT, member=member)

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
            log = TrickOrTreaterMessage(
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
                select(TrickOrTreaterMessage).filter_by(
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

        await self._log_event(Event.COLLECT_LOOT, member=member)

    async def _get_member_loot(self, member: Member) -> list[Loot]:
        async with self.bot.db.session() as session:
            loot = await session.scalars(
                select(Loot).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )

        return list(loot)

    async def _save_member_display_name(self, member: Member) -> None:
        async with self.bot.db.session() as session, session.begin():
            session.add(
                OriginalName(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    display_name=member.display_name,
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                LOGGER.debug("Member has their display_name saved already, ignoring.")

    async def _get_member_display_name(self, member: Member) -> str:
        async with self.bot.db.session() as session:
            original_name = await session.scalar(
                select(OriginalName.display_name).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )

        # return the member's display_name in case it is not saved in the database
        return original_name or member.display_name

    async def _get_guild_score(self, guild: Guild) -> list[tuple[int, int]]:
        async with self.bot.db.session() as session, session.begin():
            scores = await session.execute(
                select(Loot.user_id, func.count(Loot.user_id).label("amount"))
                .filter_by(guild_id=guild.id)
                .group_by(Loot.user_id)
                .order_by(desc("amount"))
            )

        return list(scores)  # type: ignore[reportReturnType]

    async def _log_event(
        self,
        event_type: Event,
        *,
        member: Member | None = None,
        guild: Guild | None = None,
    ) -> None:
        if member is not None and guild is not None:
            msg = "member and guild cannot both be set."
            raise ValueError(msg)

        if member is None and guild is None:
            msg = "Please set either member or guild."
            raise ValueError(msg)

        if member is not None:
            guild = member.guild

        guild_id = member.guild.id if member is not None else guild.id  # type: ignore[not-none]

        async with self.bot.db.session() as session, session.begin():
            event_log = EventLog(
                event=event_type,
                guild_id=guild_id,
                user_id=member.id if member else None,
                created_at=utils.utcnow(),
            )
            session.add(event_log)
            await session.commit()
        LOGGER.debug(f"Logging event {event_type} at {event_log.created_at}.")
