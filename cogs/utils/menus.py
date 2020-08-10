import asyncio
import discord
from discord.ext import menus


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
