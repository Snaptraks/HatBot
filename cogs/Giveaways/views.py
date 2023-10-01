import discord
from discord import ui


class GiveawayView(ui.View):
    def __init__(self):
        # do stuff here?
        super().__init__(timeout=None)

    @ui.button(
        label="Enter!", emoji="\N{WRAPPED PRESENT}", style=discord.ButtonStyle.green
    )
    async def on_enter(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        await interaction.response.send_message(
            "Thank you for entering the giveaway!", ephemeral=True
        )
