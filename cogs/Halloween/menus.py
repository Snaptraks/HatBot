import discord
from discord.ext import menus

from ..utils.menus import _MenuUtils, Middle


INCREASE_EMOJI = "\U0001f53c"
DECREASE_EMOJI = "\U0001f53d"
ZERO_EMOJI = "\u0030\u20e3"


class GiveCandyMenu(_MenuUtils, menus.MenuPages):
    """Interactive menu to select hoe many candy to give."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_give = {e[0]: 0 for e in self.source.entries}

    @menus.button(INCREASE_EMOJI, position=Middle(0))
    async def on_increase(self, payload):
        """Increase the number of candy on the page by one."""

        page = await self.source.get_page(self.current_page)
        candy = page[0]
        max_val = self.source.entries[self.current_page][1]

        if self.to_give[candy] < max_val:
            self.to_give[candy] += 1

        await self.show_page(self.current_page)

    @menus.button(DECREASE_EMOJI, position=Middle(1))
    async def on_decrease(self, payload):
        """Decrease the number of candy on the page by one."""

        page = await self.source.get_page(self.current_page)
        candy = page[0]

        if self.to_give[candy] > 0:
            self.to_give[candy] -= 1

        await self.show_page(self.current_page)

    @menus.button(ZERO_EMOJI, position=Middle(2))
    async def on_clear(self, payload):
        """Reset the amount of candy on the page to 0."""

        page = await self.source.get_page(self.current_page)
        candy = page[0]
        self.to_give[candy] = 0

        await self.show_page(self.current_page)

    async def prompt(self, ctx):
        """Start the menu and return the amount of candy to give."""

        await self.start(ctx, wait=True)
        return self.to_give


class GiveCandySource(menus.ListPageSource):
    """Page source to format the give candy menu."""

    def __init__(self, entries):
        super().__init__(entries, per_page=1)

    async def format_page(self, menu, page):
        embed = discord.Embed(
            color=0xEB6123,
            title=f"Candy to give to {menu.ctx.args[2].display_name}",
            description=f"How many {page[0]}?",
        ).add_field(
            name="Current Bag",
            value=self.format_field(self.entries),
        ).add_field(
            name="To Give",
            value=self.format_field(menu.to_give),
        )

        return embed

    def format_field(self, field):
        if isinstance(field, list):
            lines = [f"{line[1]} {line[0]}" for line in field]
        elif isinstance(field, dict):
            lines = [f"{value} {key}" for key, value in field.items()]
        return '\n'.join(lines)
