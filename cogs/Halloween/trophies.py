from __future__ import annotations

import logging
import random
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

from discord import Color, Embed, Interaction, Member, TextChannel, app_commands, ui
from discord.ext import commands
from rich import print
from snapcogs.database import Base
from sqlalchemy import select
from sqlalchemy.orm import Mapped  # noqa: TC002

from .models import Event, EventLog, Loot, TreatCount

if TYPE_CHECKING:
    from collections.abc import Mapping

    from snapcogs.bot import Bot

    from .halloween import Halloween


PATH = Path(__file__).parent
LOGGER = logging.getLogger(__name__)
MC_CONSOLE_CHANNEL = 588171779957063680  # Bot Testing Server


# Maybe add milestones if the event is very popular?
class Milestone(Enum):
    ALL_TREATS = auto()
    FIRST_LOOT = auto()
    TEN_LOOT = auto()
    TWENTY_LOOT = auto()
    FIRST_RARE = auto()
    FIVE_RARE = auto()
    TEN_RARE = auto()
    FIRST_CURSE = auto()
    TEN_CURSE = auto()
    TWENTY_CURSE = auto()


MILESTONE_DESCRIPTION = {
    Milestone.ALL_TREATS: "Collect all kinds of treats.",
    Milestone.FIRST_LOOT: "Receive your first loot.",
    Milestone.TEN_LOOT: "Receive 10 loot items.",
    Milestone.TWENTY_LOOT: "Receive 20 loot items.",
    Milestone.FIRST_RARE: "Receive your first Rare loot items.",
    Milestone.FIVE_RARE: "Receive 5 Rare loot items.",
    Milestone.TEN_RARE: "Receive 10 Rare loot items.",
    Milestone.FIRST_CURSE: "Get cursed for the first time.",
    Milestone.TEN_CURSE: "Get cursed 10 times.",
    Milestone.TWENTY_CURSE: "Get cursed 20 times.",
}


def fmt_milestones(milestones: Mapping[Milestone, bool]) -> str:
    return "\n".join(
        f"- {MILESTONE_DESCRIPTION[milestone]}"
        for milestone, reward in milestones.items()
        if reward
    )


class MilestoneLog(Base):
    __tablename__ = "halloween_milestone"
    guild_id: Mapped[int]
    user_id: Mapped[int]
    milestone: Mapped[Milestone]


class TrophiesModal(ui.Modal, title="Claim trophies on Minecraft"):
    """The modal that takes the Minecraft username of the member.

    There is a very obvious warning at the top, which states that they will not be
    able to claim trophies if they are not logged in at the time of claiming.
    """

    # warning = ui.TextDisplay(
    #     ":warning: **NOTE**: You need to be logged in on the "
    #     "Hatventures Community Minecraft server to receive your trophies.\n\n"
    #     "You can get trophies for reaching certain milestones, but can only claim "
    #     "one per milestone. Reaching more milestones after claiming your trophies "
    #     "will allow you to claim some more by running the command again."
    # )
    mc_username = ui.TextInput(label="Your Minecraft Username", max_length=16)

    async def on_submit(self, interaction: Interaction[Bot]) -> None:
        await interaction.response.defer()


class Trophies(commands.Cog):
    """Cog for trophies for the Halloween event."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        with (PATH / "trophies.txt").open() as f:
            # each line of the file is a Minecraft command
            self.trophy_commands = f.readlines()

        # Add the subcommands to the /halloween command group
        self.halloween_cog: Halloween = self.bot.get_cog("Halloween")  # type: ignore[]

        self.halloween_cog.halloween.add_command(
            app_commands.Command(
                name="trophies",
                description="Claim trophies on Minecraft!",
                callback=self.halloween_trophies,
            )
        )
        self.halloween_cog.halloween.add_command(
            app_commands.Command(
                name="milestones",
                description="View your milestones.",
                callback=self.halloween_milestones,
            )
        )

    async def halloween_trophies(self, interaction: Interaction[Bot]) -> None:
        """Claim the trophies for the newly reached milestones."""
        assert isinstance(interaction.user, Member)
        modal = TrophiesModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        mc_username = modal.mc_username.value

        milestones = await self.get_milestones(interaction.user)
        new_milestones: list[Milestone] = []

        for milestone, reward in milestones.items():
            if reward and await self._check_milestone(interaction.user, milestone):
                LOGGER.debug(
                    f"New milestone {milestone} attained for {interaction.user}."
                )
                new_milestones.append(milestone)
                trophy_command = random.choice(self.trophy_commands).replace(
                    "%MC_USERNAME", mc_username
                )
                mc_console_channel = self.bot.get_channel(MC_CONSOLE_CHANNEL)
                assert isinstance(mc_console_channel, TextChannel)
                await mc_console_channel.send(trophy_command)
                await self._mark_milestone(interaction.user, milestone)

        if all(milestones.values()) and len(new_milestones) == 0:
            content = "You reached all milestones!"
        elif new_milestones:
            milestones_str = fmt_milestones(dict.fromkeys(new_milestones, True))
            content = f"Trophies sent for the milestones:\n{milestones_str}"
        else:
            content = "No trophies ready to claim!"

        await interaction.followup.send(content, ephemeral=True)

    async def halloween_milestones(self, interaction: Interaction[Bot]) -> None:
        """List the milestones reached by the member."""
        assert isinstance(interaction.user, Member)
        milestones = await self.get_milestones(interaction.user)
        milestones_str = fmt_milestones(milestones)

        embed = Embed(
            title="Halloween Milestones",
            color=Color.orange(),
            description=(
                f"You have reached the following milestones:\n{milestones_str}"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def get_milestones(self, member: Member) -> dict[Milestone, bool]:
        """Get a dict of whether each milestone is reached or not.

        Parameters
        ----------
        member : Member
            The member to get the milestones from

        Returns
        -------
        dict[Milestone, bool]
            A dict of Milestone to bool, indicating if the milestone is reached.

        """
        milestones: dict[Milestone, bool] = {}
        get_milestone = {
            Milestone.ALL_TREATS: self._get_milestone_all_treats,
            Milestone.FIRST_LOOT: self._get_milestone_first_loot,
            Milestone.TEN_LOOT: self._get_milestone_ten_loot,
            Milestone.TWENTY_LOOT: self._get_milestone_twenty_loot,
            Milestone.FIRST_RARE: self._get_milestone_first_rare,
            Milestone.FIVE_RARE: self._get_milestone_five_rare,
            Milestone.TEN_RARE: self._get_milestone_ten_rare,
            Milestone.FIRST_CURSE: self._get_milestone_first_curse,
            Milestone.TEN_CURSE: self._get_milestone_ten_curse,
            Milestone.TWENTY_CURSE: self._get_milestone_twenty_curse,
        }
        for milestone, get_fn in get_milestone.items():
            milestones[milestone] = await get_fn(member)

        return milestones

    async def _mark_milestone(self, member: Member, milestone: Milestone) -> None:
        """Mark the milestone as reached for the member.

        Parameters
        ----------
        member : Member
            The member that reached the milestone.
        milestone : Milestone
            The milestone that was reached.

        """
        async with self.bot.db.session() as session, session.begin():
            session.add(
                MilestoneLog(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    milestone=milestone,
                )
            )
            await session.commit()

    async def _check_milestone(self, member: Member, milestone: Milestone) -> bool:
        """Check if the milestone was reached by the member.

        Parameters
        ----------
        member : Member
            The member to check if the milestone was reached
        milestone : Milestone
            The milestone to check.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        async with self.bot.db.session() as session:
            check = await session.scalar(
                select(MilestoneLog).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    milestone=milestone,
                )
            )
            # if it is not in the DB, it returns None,
            # the member has not claimed the milestone yet
            return check is None

    async def _get_milestone_all_treats(self, member: Member) -> bool:
        """Check if the milestone for collecting all kinds of treats is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        async with self.bot.db.session() as session:
            type_of_treats = await session.scalars(
                select(TreatCount).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )
            return len(list(type_of_treats)) == len(self.halloween_cog.treats)

    async def _get_milestone_n_loot(self, member: Member, amount: int) -> bool:
        """Check if the milestone for collecting `amount` loot items is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        async with self.bot.db.session() as session:
            loots = await session.scalars(
                select(Loot).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                )
            )

            return len(loots.all()) >= amount

    async def _get_milestone_first_loot(self, member: Member) -> bool:
        """Check if the milestone for collecting 1 loot item is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_loot(member, 1)

    async def _get_milestone_ten_loot(self, member: Member) -> bool:
        """Check if the milestone for collecting 10 loot items is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_loot(member, 10)

    async def _get_milestone_twenty_loot(self, member: Member) -> bool:
        """Check if the milestone for collecting 20 loot items is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_loot(member, 20)

    async def _get_milestone_n_rare(self, member: Member, amount: int) -> bool:
        """Check if the milestone for collecting `amount` rare loot items is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        async with self.bot.db.session() as session:
            loots = await session.scalars(
                select(Loot).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    rarity="rare",
                )
            )

            return len(loots.all()) >= amount

    async def _get_milestone_first_rare(self, member: Member) -> bool:
        """Check if the milestone for collecting 1 rare loot item is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_rare(member, 1)

    async def _get_milestone_five_rare(self, member: Member) -> bool:
        """Check if the milestone for collecting 5 rare loot items is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_rare(member, 5)

    async def _get_milestone_ten_rare(self, member: Member) -> bool:
        """Check if the milestone for collecting 10 rare loot items is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_rare(member, 10)

    async def _get_milestone_n_curse(self, member: Member, amount: int) -> bool:
        """Check if the milestone for getting cursed `amount` times is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        async with self.bot.db.session() as session:
            curses = await session.scalars(
                select(EventLog).filter_by(
                    guild_id=member.guild.id,
                    user_id=member.id,
                    event=Event.GET_CURSE,
                )
            )

            return len(curses.all()) >= amount

    async def _get_milestone_first_curse(self, member: Member) -> bool:
        """Check if the milestone for getting cursed once is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_curse(member, 1)

    async def _get_milestone_ten_curse(self, member: Member) -> bool:
        """Check if the milestone for getting cursed 10 times is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_curse(member, 10)

    async def _get_milestone_twenty_curse(self, member: Member) -> bool:
        """Check if the milestone for getting cursed 20 is reached.

        Parameters
        ----------
        member : Member
            The member to check the milestone from.

        Returns
        -------
        bool
            Whether the milestone was reached by the member or not.

        """
        return await self._get_milestone_n_curse(member, 20)
