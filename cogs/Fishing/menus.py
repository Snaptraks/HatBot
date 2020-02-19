import discord
from discord.ext import menus

INVENTORY_EMOJI = '\U0001f9f0'  # :toolbox:
EXPERIENCE_EMOJI = '\U0001f4b5'  # :dollar:
SELL_ALL_EMOJI = '\U0001f4b0'  # :moneybag:
TRADE_EMOJI = '\U0001f501'  # :repeat:

EMBED_COLOR = discord.Color.blurple()


class Middle(menus.Position):
    __slots__ = ()
    def __init__(self, number=0):
        super().__init__(number, bucket=1)


class FishingMenu(menus.Menu):
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


class InventoryPages(menus.MenuPages):
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

    def should_add_reactions(self):
        """Always show buttons, even when there is only one page."""
        return True

    async def prompt(self, ctx):
        """Start the menu and return the Fish to sell."""

        await self.start(ctx, wait=True)
        return self.source._to_sell


class InventorySource(menus.ListPageSource):
    """Page source to format the inventory menu."""

    def __init__(self, data):
        self._to_sell = set()
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        embed = entries.to_embed()
        embed.title = 'Fish Inventory'
        embed.color = EMBED_COLOR

        if menu.current_page in self._to_sell:
            footer_text = 'Sold!'

        else:
            footer_text = (
                f'{EXPERIENCE_EMOJI} to sell current fish | '
                f'{SELL_ALL_EMOJI} to sell all'
                )

        embed.set_footer(text=footer_text)
        return embed


class TradeConfirm(menus.Menu):
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


class TradePages(menus.MenuPages):
    """Interactive menu to trade Fish."""

    @menus.button(TRADE_EMOJI, position=Middle(0))
    async def on_select_trade(self, payload):
        """Select the current Fish for trade."""

        self.source._to_trade = self.current_page
        await self.show_page(self.current_page)

    def should_add_reactions(self):
        """Always show buttons, even when there is only one page."""
        return True

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return (self.ctx.author, self.source._to_trade)


class TradeSource(menus.ListPageSource):
    """Page source to format the trade menu."""

    def __init__(self, data):
        self._to_trade = None
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        embed = entries.to_embed()
        embed.title = 'Trade Menu'
        embed.color = EMBED_COLOR
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
