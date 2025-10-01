from __future__ import annotations

import itertools
import logging
import math
import random
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

from .base import TRICK_OR_TREATER_LENGTH
from .models import Event

if TYPE_CHECKING:
    from typing import Self

    from discord import Message
    from snapcogs.bot import Bot

    from .base import BaseTreat, Inventory, TrickOrTreater
    from .halloween import Halloween
    from .models import TreatCount

LOGGER = logging.getLogger(__name__)


class TreatButton(ui.Button["TrickOrTreaterView"]):
    def __init__(self) -> None:
        super().__init__(label="Give a treat!", emoji="🎃", style=ButtonStyle.green)
        self.view: TrickOrTreaterView

    async def callback(self, interaction: Interaction[Bot]) -> None:
        assert isinstance(interaction.user, Member)
        user_inventory = await self.view.cog._get_member_inventory(interaction.user)

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
        assert interaction.guild is not None

        selected_treat: str = self.treat_select.component.values[0]  # type: ignore[reportAttributeAccessIssue]
        treat = self.view.cog._get_treat_by_name(selected_treat)

        LOGGER.info(
            f"{interaction.user.display_name} giving 1 "
            f"{treat} to {self.view.message.jump_url}"
        )
        LOGGER.debug(f"{interaction.user} giving 1 {treat} to {self.view.message}.")

        await self.view.cog._remove_treat_from_inventory(treat, interaction.user)
        await self.view.cog._mark_trick_or_treater_by_member(
            interaction.user,
            interaction.message,
        )

        if treat == self.view.requested_treat:
            LOGGER.debug(f"Giving requested treat to {interaction.message}.")

            success_message = await self.view.cog._give_normal_loot(
                interaction.user, self.view.trick_or_treater
            )

            content = f"Thank you for the {treat}! {success_message}"

            await self.view.cog._log_event(
                Event.REQUESTED_TREAT, member=interaction.user
            )

        else:
            LOGGER.debug(f"Giving NOT requested treat to {interaction.message}.")
            r = random.random() < 0.5
            if r:
                LOGGER.debug(f"Giving BLESSING to {interaction.user} ({r=}).")
                # Blessing: higher loot rarity or bonus treat
                success_message = await self.view.cog._give_blessing(
                    interaction.user, self.view.trick_or_treater
                )

                reaction = f"It's even better! {success_message}"
            else:
                LOGGER.debug(f"Giving CURSE to {interaction.user} ({r=}).")
                # Curse: funny name and Cursed role
                cursed_name = await self.view.cog._give_curse(interaction.user)

                reaction = f"Ew!\nYou get a **curse** for that, __**{cursed_name}**__!"

            content = f"This is not what I asked for... {reaction}"

            await self.view.cog._log_event(
                Event.NOT_REQUESTED_TREAT, member=interaction.user
            )

        await interaction.response.send_message(content, ephemeral=True)


class TrickOrTreaterView(ui.LayoutView):
    message: Message

    def __init__(
        self, bot: Bot, trick_or_treater: TrickOrTreater, requested_treat: BaseTreat
    ) -> None:
        super().__init__(timeout=TRICK_OR_TREATER_LENGTH * 60)
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


class TreatsView(ui.View):
    def __init__(self, treats: list[TreatCount]) -> None:
        super().__init__()
        self.treats = treats

    @ui.button(label="See the Content", emoji="👀")
    async def see_content(
        self, interaction: Interaction[Bot], _: ui.Button[Self]
    ) -> None:
        assert isinstance(interaction.user, Member)

        treats_list = [
            emoji for treat in self.treats for emoji in (treat.emoji * treat.amount)
        ]
        if len(treats_list) == 0:
            await interaction.response.send_message(
                "No treats to show ☹️", ephemeral=True
            )
            return

        random.shuffle(treats_list)
        batch_size = math.ceil(len(treats_list) ** 0.5) + 1
        formatted_treats = "\n".join(
            "# " + "".join(batch)
            for batch in itertools.batched(treats_list, batch_size, strict=False)
        )

        await interaction.response.send_message(
            content=formatted_treats,
            ephemeral=True,
        )
