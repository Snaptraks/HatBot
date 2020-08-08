from discord.ext import menus


class TurnipFirstTimeMenu(menus.Menu):
    """Menu to ask if it is the member's first time buying turnips."""

    def __init__(self):
        super().__init__(delete_message_after=True)
        self.first_time = None

    async def send_initial_message(self, ctx, channel):
        return await ctx.send('Is this your first time buying turnips?')

    @menus.button('\U0001F44D')
    async def on_confirm(self, payload):
        self.first_time = True
        self.stop()

    @menus.button('\U0001F44E')
    async def on_deny(self, payload):
        self.first_time = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.first_time


class TurnipPreviousPatternMenu(menus.Menu):
    """Menu to ask the member about their previous turnip pattern."""

    choices = [
        ('\u0031\u20e3', 'Fluctuating'),
        ('\u0032\u20e3', 'Large Spike'),
        ('\u0033\u20e3', 'Decreasing'),
        ('\u0034\u20e3', 'Small Spike'),
        ('\u0035\u20e3', 'I don\'t know'),
    ]

    def __init__(self):
        super().__init__(delete_message_after=True)
        self.previous_pattern = None

    async def send_initial_message(self, ctx, channel):
        choices_str = '\n'.join(f'{_[0]}  {_[1]}' for _ in self.choices)
        return await ctx.send((
            'What was your previous price pattern?\n'
            f'{choices_str}'
        ))

    @menus.button(choices[0][0])
    async def on_fluctuating(self, payload):
        self.previous_pattern = 0
        self.stop()

    @menus.button(choices[1][0])
    async def on_large_spike(self, payload):
        self.previous_pattern = 1
        self.stop()

    @menus.button(choices[2][0])
    async def on_decreasing(self, payload):
        self.previous_pattern = 2
        self.stop()

    @menus.button(choices[3][0])
    async def on_small_spike(self, payload):
        self.previous_pattern = 3
        self.stop()

    @menus.button(choices[4][0])
    async def on_unknown(self, payload):
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.previous_pattern


class TurnipResetConfirm(menus.Menu):
    """Menu to confirm the reset of prices for the current week."""

    def __init__(self, msg):
        super().__init__(delete_message_after=True)
        self.msg = msg
        self.reset = None

    async def send_initial_message(self, ctx, channel):
        return await ctx.send(self.msg)

    @menus.button('\U0001F44D')
    async def on_confirm(self, payload):
        self.reset = True
        self.stop()

    @menus.button('\U0001F44E')
    async def on_deny(self, payload):
        self.reset = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.reset
