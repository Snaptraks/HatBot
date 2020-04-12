import asyncio
from datetime import datetime
from collections import defaultdict
import io
import json
import os
import pickle
import typing

import discord
from discord.ext import commands, tasks
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..utils.cogs import BasicCog


matplotlib.use('Agg')

EMBED_COLOR = 0xF3F5E8


class WeekDay(commands.Converter):
    """Convert to a day of the week.
    Able to convert in English or French.
    0 is Monday and 6 is Sunday, to be consistent with datetime.weekday().
    """

    weekdays = (
        ('monday', 'mon', 'lundi', 'lu'),
        ('tuesday', 'tue', 'mardi', 'ma'),
        ('wednesday', 'wed', 'mercredi', 'me'),
        ('thursday', 'thu', 'jeudi', 'je'),
        ('friday', 'fri', 'vendredi', 've'),
        ('saturday', 'sat', 'samedi', 'sa'),
        ('sunday', 'sun', 'dimanche', 'di'),
        )

    async def convert(self, ctx, argument):
        for d in range(len(self.weekdays)):
            if argument.lower() in self.weekdays[d]:
                return d

        # if we can't find the day
        raise commands.BadArgument(f'Day "{argument}" not recognized.')


class AmPm(commands.Converter):
    """Convert to AM or PM.
    0 is AM and 1 is PM.
    """

    am_pm = ('am', 'pm')

    async def convert(self, ctx, argument):
        try:
            return self.am_pm.index(argument.lower())

        except ValueError:
            raise commands.BadArgument(
                f'Argument "{argument}" not recognized as AM or PM.')


def empty_series():
    return pd.Series(np.nan, index=range(13))


class ACNH(BasicCog):
    """Module for actions related to Animal Crossing: New Horizons."""

    def __init__(self, bot):
        super().__init__(bot)
        self.presence_task.start()

        with open(os.path.join(self._cog_path, 'quotes.json'), 'r') as f:
            self.quotes = json.load(f)

        try:
            with open(os.path.join(self._cog_path, 'data.pkl'), 'rb') as f:
                self.data = pickle.load(f)

        except FileNotFoundError:
            self.data = defaultdict(empty_series)

    def cog_unload(self):
        super().cog_unload()
        self.presence_task.cancel()

        with open(os.path.join(self._cog_path, 'data.pkl'), 'wb') as f:
            pickle.dump(self.data, f)

    @tasks.loop(hours=1)
    async def presence_task(self):
        """Change the presence of the bot once fully loaded."""

        game = discord.Game(name='Animal Crossing: New Horizons')
        await self.bot.change_presence(activity=game)

    @presence_task.before_loop
    async def presence_task_before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener(name='on_message')
    async def on_mention(self, message):
        """Send a funny reply when the bot is mentionned."""

        ctx = await self.bot.get_context(message)

        if ctx.me.mentioned_in(message) \
                and not message.author.bot \
                and not message.mention_everyone \
                and not message.content.startswith(self.bot.command_prefix):

            out_str = np.random.choice(self.quotes)
            await self.send_typing_delay(ctx.channel)
            await ctx.send(out_str)

    @commands.group(aliases=['turnips', 'navet', 'navets', 't'],
                    invoke_without_command=True)
    async def turnip(self, ctx):
        """Command group to manage and check the turnip prices."""

        data = self.data[ctx.author.id]
        sell_prices = data[:12]
        bought_price = data[12]

        turnip_emoji = self.bot.get_emoji(697120729476497489)  # turnip_badge

        if not pd.isnull(bought_price):
            bought_str = (
                f'You bought turnips for {bought_price:.0f} bells this week.'
                )

        else:
            bought_str = (
                'You did not buy turnips this week, '
                'or did not save the price.'
                )

        description = (
            f'{bought_str}\n'
            f'The maximum sell price was {sell_prices.max():.0f} bells.\n'
            f'The lowest sell price was {sell_prices.min():.0f} bells.'
            )

        graph = await self.bot.loop.run_in_executor(
            None, self._turnip_plot, ctx.author)
        graph_file = discord.File(graph, filename='graph.png')

        embed = discord.Embed(
            # title='Turnip Tracker',
            description=description,
            color=EMBED_COLOR,
        ).set_image(
            url=f'attachment://{graph_file.filename}',
        ).set_author(
            name='Turnip Tracker',
            icon_url=turnip_emoji.url,
        )

        await ctx.send(embed=embed, file=graph_file)

    @turnip.command(name='pattern', aliases=['patterns'])
    async def turnip_pattern(self, ctx):
        """Explain the different patterns observed in the turnip market
        in Animal Crossing: New Horizons.
        """
        await ctx.send(':warning: Work in progress')

    @turnip.command(name='price', aliases=['prix', 'p'])
    async def turnip_price(self, ctx, price: int,
                           weekday: WeekDay = None,
                           am_pm: AmPm = None):
        """Register the price of turnips for a given period, or the current
        one if not specified.
        """
        now = datetime.now()  # don't use UTC here
        if weekday is None:
            weekday = now.weekday()

        if am_pm is None:
            am_pm = int(now.hour >= 12)

        turnip_index = 2 * weekday + am_pm if weekday != 6 else 12
        self.data[ctx.author.id][turnip_index] = price
        out_str = (
            'OK! Let me set the price for '
            f'{WeekDay.weekdays[weekday][0].title()} '
            f'{AmPm.am_pm[am_pm].upper()} '
            f'to {price} bells!'
            )
        await ctx.send(out_str)

    @turnip_price.before_invoke
    async def turnip_price_before(self, ctx):
        """Reset the member's data if it is Sunday."""

        if datetime.now().weekday() == 6:  # Sunday
            await ctx.send(
                'It is Sunday, let me reset your prices for the week.')
            try:
                del self.data[ctx.author.id]

            except KeyError:
                pass

    @turnip_price.error
    async def turnip_price_error(self, ctx, error):
        """Error handler for the turnip price command."""

        if isinstance(error, (
                commands.MissingRequiredArgument,
                commands.BadArgument,
                )):
            await ctx.send(error)

        else:
            raise error

    def _turnip_plot(self, author: discord.Member):
        """Plot the turnip price evolution for the given user."""

        prices = self.data[author.id].values

        with plt.xkcd():
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.axhline(prices[-1], color='r', label='Bought At')
            ax.plot(prices[:-1], '-o', c='C2', ms=8, label='Price Evolution')
            ax.legend()
            ax.set_xlabel('Day of the week')
            ax.set_ylabel('Bells')
            ax.set_xticks(range(0, 12, 2))
            ax.set_xticklabels(
                [day[1].title() for day in WeekDay.weekdays])
            plt.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png')
        plt.close(fig=fig)
        buffer.seek(0)

        return buffer

    async def send_typing_delay(self, channel):
        r = np.random.rand()  # [0, 1)
        t = 1.5 * r + 0.5  # [0.5, 2)
        await channel.trigger_typing()
        await asyncio.sleep(t)
