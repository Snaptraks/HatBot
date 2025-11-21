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

from .base import TRICK_OR_TREAT_CHANNEL, TRICK_OR_TREATER_LENGTH
from .models import Event

if TYPE_CHECKING:
    from typing import Self

    from discord import Message
    from snapcogs.bot import Bot

    from .base import BaseTreat, Inventory, TrickOrTreater
    from .halloween import Halloween
    from .models import Loot, Treat

LOGGER = logging.getLogger(__name__)


class FreeTreatsButton(ui.Button):
    """A button that gives free treats to who pressed it."""

    def __init__(self) -> None:
        super().__init__(
            label="Free Treats!",
            emoji="🪅",
            style=ButtonStyle.green,
            custom_id="halloween:free_treats",
        )
        self.view: HalloweenStartView

    async def callback(self, interaction: Interaction[Bot]) -> None:
        assert isinstance(interaction.user, Member)
        for treat in self.view.cog.treats:
            await self.view.cog._add_treat_to_inventory(treat, interaction.user)

        treats_str = " ".join(t.emoji for t in self.view.cog.treats)

        await interaction.response.send_message(
            f"Here are some free treats to get you started!\n# {treats_str}",
            ephemeral=True,
        )

        await self.view.cog._log_event(Event.CLAIM_FREE_TREATS, member=interaction.user)

    async def interaction_check(self, interaction: Interaction[Bot]) -> bool:
        assert isinstance(interaction.user, Member)
        check = await self.view.cog._check_free_treats(interaction.user)
        if not check:
            await interaction.response.send_message(
                "You already claimed your free treats!",
                ephemeral=True,
            )

        return check


class HalloweenStartView(ui.LayoutView):
    """The LayoutView (attached to a message) that starts the Halloween event.

    This has a lot of text to describe the event, a cute picture, and a button
    to give free treats to people to start the Halloween event!
    """

    def __init__(self, bot: Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        self.title = ui.TextDisplay("# 🎃 Happy Halloween!")
        self.description = ui.TextDisplay(
            "### It is time for Halloween! Starting today and for the following weeks, "
            "There will be **treats** popping up when chatting with the community! "
            "Make sure to collect them, as some **trick-or-treaters** will start "
            f"knocking in <#{TRICK_OR_TREAT_CHANNEL}> asking for them, and trading "
            "for unique **loot**! \n"
            "[Click Here for more information.](https://github.com/Snaptraks/HatBot/blob/master/cogs/Halloween/README.md)"
        )
        self.image = ui.MediaGallery(
            MediaGalleryItem(
                media="https://archives.snaptraks.phd/Halloween/Happy_Halloween.png"
            )
        )
        self.bottom = ui.Section(
            ui.TextDisplay("Claim your free treats here!"),
            accessory=FreeTreatsButton(),
        )

        container = ui.Container(
            self.title,
            self.description,
            self.image,
            self.bottom,
            accent_color=Color.orange(),
        )
        self.add_item(container)

    @property
    def cog(self) -> Halloween:
        return self.bot.get_cog("Halloween")  # type: ignore[correct-type]


class TreatButton(ui.Button["TrickOrTreaterView"]):
    """The button to give a treat to the trick-or-treater."""

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
    """The modal that asks which treat to give.

    The modal contains a dropdown select menu with the treats the member owns.
    """

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
                        description=f"You have {treat_count.amount}.",
                        emoji=treat_count.emoji,
                    )
                    for treat_count in user_inventory
                ],
            ),
        )
        self.add_item(self.treat_select)

    async def on_submit(self, interaction: Interaction[Bot]) -> None:
        """Handle the logic of giving a treat to the trick-or-treater.

        If the member provides the requested treat, select a loot item from the
        trick-or-treater with normal rarity rates. If the member already has it,
        do not give them another one.

        If the member does NOT provide the requested treat, there is a 50/50
        chance of a blessing or curse.
        A blessing rewards the member with a loot item of rarity Uncommon or Rare,
        with increased rarity rates, plus a random treat. If the member already has
        the loot item, give them two of the random treat instead.
        A curse gives the member a special Cursed role with the color visible,
        and give them a random Halloween themed nickname for CURSE_LENGTH minutes.
        """
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
            r = random.random()
            if r < 0.5:
                LOGGER.debug(f"Giving BLESSING to {interaction.user} ({r=}).")
                # Blessing: higher loot rarity or bonus treat
                success_message = await self.view.cog._give_blessing(
                    interaction.user, self.view.trick_or_treater
                )

                reaction = f"It's even better!\n{success_message}"
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
    """The LayoutView (attached to a message) that displays a trick-or-treater.

    This contains a bit of text with the requested treat, a nice picture of
    the trick-or-treater, and a button that opens the modal for selecting the
    treat to give out. It has a timeout of TRICK_OR_TREATER_LENGTH minutes.
    """

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
    """The View to display the treats in an exploded view.

    This view contains a single button, attached to the /halloween treats
    command output.
    """

    def __init__(self, treats: list[Treat]) -> None:
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
            "".join(batch)
            for batch in itertools.batched(treats_list, batch_size, strict=False)
        )

        await interaction.response.send_message(
            content=f"```\n{formatted_treats}\n```",
            ephemeral=True,
        )


class TradeModal(ui.Modal, title="Select items to trade for rarer ones!"):
    """The modal that asks which loot items to trade up.

    The modal contains a dropdown select menu with the loot items the member
    has enough of to trade for rarer ones from the trick-or-treater.
    """

    def __init__(self, tradeable_loot: list[Loot]) -> None:
        super().__init__()
        self.loot_select: ui.Label = ui.Label(
            text="Select items!",
            description=(
                "This will trade 10 of the selected items for 1 "
                "rarer item from the trick-or-treater."
            ),
            component=ui.Select(
                options=[
                    SelectOption(
                        label=f"{item.rarity.title()} {item.name}",
                        value=item.name,
                        description=f"You have {item.amount}.",
                    )
                    for item in tradeable_loot
                ],
                max_values=min(len(tradeable_loot), 25),
            ),
        )
        self.add_item(self.loot_select)

    async def on_submit(self, interaction: Interaction[Bot]) -> None:
        self.interaction = interaction
