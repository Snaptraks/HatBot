from __future__ import annotations

from typing import TYPE_CHECKING

from discord import (
    ButtonStyle,
    Color,
    Interaction,
    MediaGalleryItem,
    Member,
    SelectOption,
    ui,
)
from rich import print

if TYPE_CHECKING:
    from snapcogs.bot import Bot

    from .base import TrickOrTreater
    from .halloween import Halloween
    from .models import Treat


class TreatButton(ui.Button["TrickOrTreaterView"]):
    def __init__(self) -> None:
        super().__init__(
            label="Give a treat!", emoji="\U0001f36c", style=ButtonStyle.green
        )
        self.view: TrickOrTreaterView

    async def callback(self, interaction: Interaction[Bot]) -> None:
        assert isinstance(interaction.user, Member)
        user_inventory = await self.view.cog._get_user_inventory(interaction.user)
        await interaction.response.send_modal(TreatModal(user_inventory))


class TreatModal(ui.Modal, title="Select a treat!"):
    def __init__(self, user_inventory: list[Treat]) -> None:
        super().__init__()
        print(user_inventory)

        self.treat_select: ui.Label[TrickOrTreaterView] = ui.Label(
            text="Select a treat!",
            description="yum",
            component=ui.Select(
                options=[
                    SelectOption(label=item.name, emoji=item.emoji)
                    for item in user_inventory
                ],
            ),
        )
        self.add_item(self.treat_select)

    async def on_submit(self, interaction: Interaction[Bot]) -> None:
        treat: SelectOption = self.treat_select.component.values[0]  # type: ignore[reportAttributeAccessIssue]
        await interaction.response.send_message(f"happy halloween {treat}")


class TrickOrTreaterView(ui.LayoutView):
    def __init__(self, bot: Bot, trick_or_treater: TrickOrTreater) -> None:
        super().__init__()
        self.bot = bot

        determinant = "A" if trick_or_treater["name"][0] not in "AEIOU" else "An"

        self.title = ui.TextDisplay(
            f"# {determinant} {trick_or_treater['name']} has stopped by!"
        )
        self.description = ui.TextDisplay(
            "## They want one :emoji:, I hope you have some!"
        )
        self.gallery = ui.MediaGallery(MediaGalleryItem(trick_or_treater["image"]))

        container = ui.Container(
            self.title,
            self.description,
            self.gallery,
            accent_color=Color.orange(),
        )
        container.add_item(
            ui.Section(
                ui.TextDisplay(
                    f"Select a treat to give to the {trick_or_treater['name']}"
                ),
                accessory=TreatButton(),
            )
        )
        self.add_item(container)

    @property
    def cog(self) -> Halloween:
        return self.bot.get_cog("Halloween")  # type: ignore[correct-type]
