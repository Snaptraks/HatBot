from discord.ext import menus


class ConfirmBirthday(menus.Menu):
    """Menu to allow the User to confirm their birthday when registering."""

    def __init__(self, msg):
        super().__init__(timeout=30.0)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await ctx.reply(self.msg)

    @menus.button('\U0001F44D')
    async def on_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\U0001F44E')
    async def on_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result
