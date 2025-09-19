from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from discord import (
    ButtonStyle,
    Color,
    Interaction,
    MediaGalleryItem,
    Member,
    Message,
    SelectOption,
    ui,
)
from rich import print

if TYPE_CHECKING:
    from snapcogs.bot import Bot

    from .base import BaseTreat, Inventory, TrickOrTreater
    from .halloween import Halloween

LOGGER = logging.getLogger(__name__)


class TreatButton(ui.Button["TrickOrTreaterView"]):
    def __init__(self) -> None:
        super().__init__(label="Give a treat!", emoji="🎃", style=ButtonStyle.green)
        self.view: TrickOrTreaterView

    async def callback(self, interaction: Interaction[Bot]) -> None:
        assert isinstance(interaction.user, Member)
        user_inventory = await self.view.cog._get_user_inventory(interaction.user)

        if len(user_inventory) > 0:
            await interaction.response.send_modal(TreatModal(self.view, user_inventory))
        else:
            LOGGER.debug(f"{interaction.user} inventory is empty.")
            await interaction.response.send_message(
                "You do not have any treats to give...\n"
                "You can gain some by talking with the community! "
                "Happy Halloween! 🎃",
                ephemeral=True,
            )

    async def interaction_check(self, interaction: Interaction[Bot]) -> bool:
        assert isinstance(interaction.user, Member)
        assert interaction.message is not None

        check = await self.view.cog._check_member_able_to_give(
            interaction.user,
            interaction.message,
        )
        if not check:
            LOGGER.debug(
                f"{interaction.user} not allowed to give to {interaction.message}."
            )
            await interaction.response.send_message(
                "You already gave a treat to this trick-or-treater, thank you though!",
                ephemeral=True,
            )
        LOGGER.debug(f"Allowing {interaction.user} to give to {interaction.message}.")
        return check


class TreatModal(ui.Modal, title="Select a treat!"):
    def __init__(self, view: TrickOrTreaterView, user_inventory: Inventory) -> None:
        super().__init__()
        self.view = view

        self.treat_select: ui.Label[TrickOrTreaterView] = ui.Label(
            text="Select a treat!",
            description="This will give one (1) treat to the trick-or-treater.",
            component=ui.Select(
                options=[
                    SelectOption(
                        label=f"{treat_count.name}",
                        value=treat_count.name,
                        description=f"You have {treat_count.amount}",
                        emoji=treat_count.emoji,
                    )
                    for treat_count in user_inventory
                ],
            ),
        )
        self.add_item(self.treat_select)

    async def on_submit(self, interaction: Interaction[Bot]) -> None:
        assert isinstance(interaction.user, Member)
        assert interaction.message is not None

        selected_treat: str = self.treat_select.component.values[0]  # type: ignore[reportAttributeAccessIssue]
        treat = self.view.cog._get_treat_by_name(selected_treat)

        LOGGER.debug(f"{interaction.user} giving 1 {treat} to {self.view.message}.")

        await self.view.cog._remove_treat_from_inventory(treat, interaction.user)
        await self.view.cog._mark_trick_or_treater_by_member(
            interaction.user,
            interaction.message,
        )

        if treat == self.view.requested_treat:
            LOGGER.debug(f"Giving requested treat to {interaction.message}.")
            content = f"Thank you for the {treat}!"
        else:
            LOGGER.debug(f"Giving NOT requested treat to {interaction.message}.")
            if random.random() < 0.5:
                reaction = "It's even better!"
            else:
                reaction = "And it tastes awful! Ew!"
            content = f"This is not what I asked for... {reaction}"

        await interaction.response.send_message(content, ephemeral=True)


class TrickOrTreaterView(ui.LayoutView):
    message: Message

    def __init__(
        self, bot: Bot, trick_or_treater: TrickOrTreater, requested_treat: BaseTreat
    ) -> None:
        super().__init__()
        self.bot = bot
        self.trick_or_treater = trick_or_treater
        self.requested_treat = requested_treat

        determinant = "A" if trick_or_treater["name"][0] not in "AEIOU" else "An"

        self.title = ui.TextDisplay(
            f"# {determinant} {trick_or_treater['name']} has stopped by!"
        )
        self.description = ui.TextDisplay(
            f"## They want one {requested_treat}, I hope you have some!"
        )
        self.gallery = ui.MediaGallery(MediaGalleryItem(trick_or_treater["image"]))
        self.bottom = ui.Section(
            ui.TextDisplay(f"Select a treat to give to the {trick_or_treater['name']}"),
            accessory=TreatButton(),
        )

        container = ui.Container(
            self.title,
            self.description,
            self.gallery,
            self.bottom,
            accent_color=Color.orange(),
        )
        self.add_item(container)

    @property
    def cog(self) -> Halloween:
        return self.bot.get_cog("Halloween")  # type: ignore[correct-type]

    async def on_timeout(self) -> None:
        LOGGER.debug(f"View on {self.message} has timed out, editing the message.")
        self.title.content = f"# {self.trick_or_treater['name']} is gone!"
        self.description.content = (
            f"## They thank everyone for the {self.requested_treat}s!"
        )
        self.bottom.children[0].content = "See you for the next trick-or-treater!"  # type: ignore[reportAttributeAccessIssue]
        self.bottom.accessory.disabled = True  # type: ignore[reportAttributeAccessIssue]

        await self.message.edit(view=self)
