import asyncio
import discord
from discord.ext import menus
from datetime import timedelta

from ..utils.formats import pretty_print_timedelta

HOURGLASS_EMOJI = '\U0000231B'  # :hourglass:
INVENTORY_EMOJI = '\U0001f9f0'  # :toolbox:
EXPERIENCE_EMOJI = '\U0001f4b5'  # :dollar:
SELL_ALL_EMOJI = '\U0001f4b0'  # :moneybag:
TRADE_EMOJI = '\U0001f501'  # :repeat:


class Middle(menus.Position):
    __slots__ = ()
    def __init__(self, number=0):
        super().__init__(number, bucket=1)


class _MenuUtils:
    """Base class for useful methods on Menus."""

    def should_add_reactions(self):
        """Always show buttons, even when there is only one page."""

        return True

    async def _delete_message(self, delay):
        await asyncio.sleep(delay)
        await self.ctx.message.delete()
        await self.message.delete()


class CooldownMenu(menus.Menu):
    """Menu to check the remaining cooldown time."""

    def __init__(self, message, error):
        super().__init__(timeout=10 * 60, delete_message_after=True,
                         message=message)
        self.error = error

    @menus.button(HOURGLASS_EMOJI)
    async def on_hourglass(self, payload):
        """Send the remaining time to the author."""

        retry_after = timedelta(seconds=self.error.retry_after)
        await self.ctx.author.send(
            f'You have already tried to fish recently, '
            f'wait for {pretty_print_timedelta(retry_after)}.'
            )

        self.stop()


class FishingConfirm(_MenuUtils, menus.Menu):
    """Menu for newly fished Fish."""

    def __init__(self, embed):
        super().__init__(timeout=60, clear_reactions_after=True)
        self.embed = embed
        self.keep = None

    async def send_initial_message(self, ctx, channel):
        self.embed.description = \
            f'You caught something!\n{self.embed.description}'
        self.embed.set_footer(
            text=(
                f'Do you want to keep it {INVENTORY_EMOJI} '
                f'or sell it {EXPERIENCE_EMOJI} for experience?'
                ),
            )
        return await channel.send(embed=self.embed)

    @menus.button(INVENTORY_EMOJI)
    async def on_keep(self, payload):
        """Keep the Fish in inventory."""

        self.keep = True
        self.stop()

    @menus.button(EXPERIENCE_EMOJI)
    async def on_experience(self, payload):
        """Sell the Fish for experience."""

        self.keep = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.keep if self.keep is not None else True

    async def finalize(self):
        if self.keep is None:
            new_footer = 'You did not answer quickly enough, I kept it for you.'

        elif self.keep:
            new_footer = 'You kept it in your inventory.'

        else:
            new_footer = 'You sold it for experience.'

        self.embed.set_footer(text=new_footer)
        await self.message.edit(embed=self.embed)

        asyncio.create_task(self._delete_message(5 * 60))


class InventoryMenu(_MenuUtils, menus.MenuPages):
    """Interactive menu to access Fish inventory."""

    @menus.button(EXPERIENCE_EMOJI, position=Middle(0))
    async def on_sell_one(self, payload):
        """Sell the Fish on the current_page."""

        self.source._to_sell.add(self.current_page)
        await self.show_page(self.current_page)

    @menus.button(SELL_ALL_EMOJI, position=Middle(1))
    async def on_sell_all(self, payload):
        """Sell all the Fish in the member's inventory."""

        self.source._to_sell = set(range(self.source.get_max_pages()))
        await self.show_page(self.current_page)

    async def prompt(self, ctx):
        """Start the menu and return the Fish to sell."""

        await self.start(ctx, wait=True)
        return self.source._to_sell

    async def finalize(self):
        asyncio.create_task(self._delete_message(10))


class InventorySource(menus.ListPageSource):
    """Page source to format the inventory menu."""

    def __init__(self, data):
        self._to_sell = set()
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        embed = entries.to_embed()
        embed.title = \
            f'Fish Inventory ({menu.current_page + 1}/{self.get_max_pages()})'

        if menu.current_page in self._to_sell:
            footer_text = 'Sold!'

        else:
            footer_text = (
                f'{EXPERIENCE_EMOJI} to sell current fish | '
                f'{SELL_ALL_EMOJI} to sell all'
                )

        embed.set_footer(text=footer_text)
        return embed


class TradeConfirm(_MenuUtils, menus.Menu):
    """Menu to get a confirmation from the other party."""

    def __init__(self, msg):
        super().__init__(timeout=30, clear_reactions_after=False)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result

    async def finalize(self):
        asyncio.create_task(self._delete_message(5 * 60))


class TradeMenu(_MenuUtils, menus.MenuPages):
    """Interactive menu to trade Fish."""

    @menus.button(TRADE_EMOJI, position=Middle(0))
    async def on_select_trade(self, payload):
        """Select the current Fish for trade."""

        self.source._to_trade = self.current_page
        await self.show_page(self.current_page)

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return (self.ctx.author, self.source._to_trade)

    async def finalize(self):
        asyncio.create_task(self._delete_message(5 * 60))


class TradeSource(menus.ListPageSource):
    """Page source to format the trade menu."""

    def __init__(self, data):
        self._to_trade = None
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        embed = entries.to_embed()
        embed.title = \
            f'Trade Menu ({menu.current_page + 1}/{self.get_max_pages()})'
        embed.set_author(
            name=menu.ctx.author.display_name,
            icon_url=menu.ctx.author.avatar_url,
            )

        if menu.current_page == self._to_trade:
            footer_text = 'Proposed for trade'

        else:
            footer_text = discord.Embed.Empty


        embed.set_footer(text=footer_text)

        return embed
