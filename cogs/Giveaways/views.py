from __future__ import annotations

import logging
from secrets import token_hex
from typing import TYPE_CHECKING

import discord
from discord import ui
from sqlalchemy.exc import IntegrityError

from .base import MAX_PENDING_GIVEAWAYS

LOGGER = logging.getLogger(__name__)


if TYPE_CHECKING:
    from snapcogs.bot import Bot

    from .giveaways import Giveaways
    from .models import Giveaway


class GiveawayView(ui.View):
    def __init__(
        self,
        bot: Bot,
        giveaway: Giveaway,
        *,
        components_id: dict[str, str] | None = None,
    ) -> None:
        # do stuff here?
        super().__init__(timeout=None)
        if components_id is None:
            components_id = {
                "enter": token_hex(16),
                "retract": token_hex(16),
            }
        self.bot = bot
        self.giveaway_id = giveaway.id
        self.components_id = components_id

        enter_button = ui.Button(
            label="Enter!",
            emoji="\N{WRAPPED PRESENT}",
            style=discord.ButtonStyle.green,
            custom_id=components_id["enter"],
        )
        enter_button.callback = self.on_enter
        self.add_item(enter_button)

        retract_button = ui.Button(
            label="Retract",
            emoji="\N{WASTEBASKET}",
            style=discord.ButtonStyle.gray,
            custom_id=components_id["retract"],
        )
        retract_button.callback = self.on_retract
        self.add_item(retract_button)

    @property
    def cog(self) -> Giveaways:
        return self.bot.get_cog("Giveaways")  # type: ignore[correct-type]

    async def update_embed(self, interaction: discord.Interaction) -> None:
        embed = interaction.message.embeds[0]  # type: ignore[not-none]
        entries = await self.cog._count_giveaway_entries(self.giveaway_id)
        embed.set_footer(text=f"{entries} entries")

        await interaction.response.edit_message(embed=embed)

    async def on_enter(self, interaction: discord.Interaction) -> None:
        n_entries = await self.cog._count_user_pending_entries(interaction.user)
        LOGGER.debug(f"{interaction.user} has {n_entries} pending entries.")

        if n_entries >= MAX_PENDING_GIVEAWAYS:
            content = (
                f"You have already reached the maximum of {MAX_PENDING_GIVEAWAYS}"
                " pending entries across the giveaways. You need to wait until one ends"
                " or retract your entry of another giveaway, and enter again."
            )
        else:
            try:
                await self.cog._add_entry(interaction.user, self.giveaway_id)
            except IntegrityError:
                content = "You already entered this giveaway!"
            else:
                content = (
                    "You're entered and all set! "
                    "Good luck \N{HAND WITH INDEX AND MIDDLE FINGERS CROSSED}"
                )
        await self.update_embed(interaction)
        await interaction.followup.send(content, ephemeral=True)

    async def on_retract(self, interaction: discord.Interaction) -> None:
        LOGGER.debug(f"{interaction.user} has retracted an entry.")
        removed = await self.cog._remove_entry(interaction.user, self.giveaway_id)
        if removed:
            content = "You have retracted your entry to this Giveaway!"
        else:
            content = "You have not entered this Giveaway yet."

        await self.update_embed(interaction)
        await interaction.followup.send(content, ephemeral=True)
