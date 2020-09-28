from datetime import datetime

import discord
from discord.ext import menus

from ..utils.menus import Middle, _MenuUtils
from ..utils.formats import pretty_print_timedelta


CANCEL_EMOJI = '\U0001f6ab'


class ReminderMenu(_MenuUtils, menus.MenuPages):
    """Menu to check your active reminders."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_cancel = set()

    @menus.button(CANCEL_EMOJI, position=Middle(0))
    async def on_cancel(self, payload):
        current_page_rowid = self.source.entries[self.current_page]['rowid']
        if current_page_rowid in self.to_cancel:
            self.to_cancel.remove(current_page_rowid)
        else:
            self.to_cancel.add(current_page_rowid)

        await self.show_page(self.current_page)

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.to_cancel


class ReminderSource(menus.ListPageSource):
    """Page source to format the reminder list menu."""

    def __init__(self, entries):
        return super().__init__(entries, per_page=1)

    async def format_page(self, menu, page):
        now = datetime.utcnow()
        since = now - page['created_at']
        until = page['future'] - now
        if page['rowid'] not in menu.to_cancel:
            remaining = pretty_print_timedelta(until)
        else:
            remaining = "Cancelled"

        embed = discord.Embed(
            color=discord.Color.blurple(),
            description=page['message'],
        ).set_author(
            name=f"Reminders for {menu.ctx.author.display_name}",
            icon_url=menu.ctx.author.avatar_url,
        ).add_field(
            name="Remaining",
            value=remaining,
        ).add_field(
            name="Created",
            value=(
                f"[{pretty_print_timedelta(since)} ago]"
                f"({page['jump_url']})"
            ),
        ).set_footer(
            text=(
                f"Reminder {menu.current_page + 1}/{self.get_max_pages()} "
                f"| {CANCEL_EMOJI} to toggle cancellation"
            ),
        )

        return embed
