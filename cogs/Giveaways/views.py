import logging
from secrets import token_hex

import discord
from discord import ui
from snapcogs.bot import Bot
from sqlalchemy.exc import IntegrityError

from .models import Entry, Giveaway

LOGGER = logging.getLogger(__name__)


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

    async def on_enter(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            await self._add_entry(interaction.user)
        except IntegrityError:
            content = "You already entered this giveaway!"
        else:
            content = (
                "You're entered and all set! "
                "Good luck \N{HAND WITH INDEX AND MIDDLE FINGERS CROSSED}"
            )

        await interaction.response.send_message(content, ephemeral=True)

    async def _add_entry(self, user: discord.User | discord.Member) -> None:
        """Add the entry to the DB."""

        LOGGER.debug(f"Saving entry for Giveaway {self.giveaway_id} for {user}.")
        async with self.bot.db.session() as session:
            async with session.begin():
                session.add(
                    Entry(
                        user_id=user.id,
                        giveaway_id=self.giveaway_id,
                    )
                )
