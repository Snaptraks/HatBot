import asyncio
import discord
from discord.ext import commands, menus


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
        try:
            await self.ctx.message.delete()
        except discord.NotFound:
            # sometimes the command message is already deleted
            pass
        await self.message.delete()


class ShellOutputSource(menus.ListPageSource):
    def __init__(self, entries):
        super().__init__(entries, per_page=1)

    def format_page(self, menu, page):
        return f"{page}Page {menu.current_page + 1}/{self.get_max_pages()}"


def format_shell_output(stdout, stderr):
    """Nicely format shell output into a Paginator."""
    # max_size to allow space for page indicators
    paginator = commands.Paginator(max_size=1900)

    paginator.add_line("STDOUT:")
    for line in stdout.split("\n"):
        paginator.add_line(line)
    paginator.close_page()
    paginator.add_line("STDERR:")
    for line in stderr.split('\n'):
        paginator.add_line(line)

    return paginator
