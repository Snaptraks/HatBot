import asyncio
import copy

import discord
from discord.ext import menus


GREEN_CHECK_EMOJI = '\u2705'


class DidYouMeanMenu(menus.Menu):
    def __init__(self, *args, **kwargs):
        self.maybe_cmd = kwargs.pop('maybe_cmd')
        super().__init__(*args, **kwargs)

    async def send_initial_message(self, ctx, channel):
        return await ctx.send(
            f'Did you mean ``{self.ctx.prefix}{self.maybe_cmd.name}``?')

    @menus.button(GREEN_CHECK_EMOJI)
    async def on_confirm(self, payload):
        """Invoke the suggested command."""

        msg = copy.copy(self.ctx.message)
        msg.content = msg.content.replace(
            self.ctx.invoked_with, self.maybe_cmd.name, 1)
        new_ctx = await self.bot.get_context(msg, cls=type(self.ctx))
        await self.bot.invoke(new_ctx)

        self.stop()
