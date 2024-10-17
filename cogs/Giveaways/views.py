from __future__ import annotations

import logging
from secrets import token_hex
from typing import TYPE_CHECKING

import discord
from discord import ui
from snapcogs.bot import Bot
from sqlalchemy.exc import IntegrityError

LOGGER = logging.getLogger(__name__)


if TYPE_CHECKING:
    from .giveaways import Giveaways
    from .models import Giveaway


class GiveawayView(ui.View):
    def __init__(
        self,
        bot: Bot,
        giveaway: Giveaway,
        *,
        components_id: dict[str, str] | None = None,
    ):
        # do stuff here?
        super().__init__(timeout=None)
        if components_id is None:
            components_id = {
                "button": token_hex(16),
            }
        self.bot = bot
        self.giveaway_id = giveaway.id
        self.components_id = components_id

        enter_button = ui.Button(
            label="Enter!",
            emoji="\N{WRAPPED PRESENT}",
            style=discord.ButtonStyle.green,
            custom_id=components_id["button"],
        )
        enter_button.callback = self.on_enter
        self.add_item(enter_button)

    @property
    def cog(self) -> Giveaways:
        cog = self.bot.get_cog("Giveaways")
        assert cog is not None
        return cog  # type: ignore

    async def on_enter(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            await self.cog._add_entry(interaction.user, self.giveaway_id)
        except IntegrityError:
            content = "You already entered this giveaway!"
        else:
            content = (
                "You're entered and all set! "
                "Good luck \N{HAND WITH INDEX AND MIDDLE FINGERS CROSSED}"
            )

        assert interaction.message is not None
        embed = interaction.message.embeds[0]
        entries = await self.cog._count_entries(self.giveaway_id)
        embed.set_footer(text=f"{entries} entries")

        await interaction.response.edit_message(embed=embed)
        await interaction.followup.send(content, ephemeral=True)
