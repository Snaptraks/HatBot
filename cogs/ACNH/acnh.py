import asyncio
from datetime import datetime
from collections import defaultdict
import io
import json
import os

import discord
from discord.ext import commands, tasks
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..utils.cogs import BasicCog
from . import menus


EMBED_COLOR = 0xF3F5E8
TURNIP_PROPHET_BASE = 'https://turnipprophet.io/?'


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


class ACNH(BasicCog):
    """Module for actions related to Animal Crossing: New Horizons."""

    def __init__(self, bot):
        super().__init__(bot)
        self.presence_task.start()

        with open(os.path.join(self._cog_path, 'quotes.json'), 'r') as f:
            self.quotes = json.load(f)

        self._create_tables.start()

    def cog_unload(self):
        super().cog_unload()
        self.presence_task.cancel()

    @tasks.loop(hours=1)
    async def presence_task(self):
        """Change the presence of the bot once fully loaded."""

        if self.bot.user.id != 695308113007607840:  # Mr. Resetti
            self.presence_task.cancel()
            return

        game = discord.Game(name='Animal Crossing: New Horizons')
        await self.bot.change_presence(activity=game)

    @presence_task.before_loop
    async def presence_task_before(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener(name='on_message')
    async def on_mention(self, message):
        """Send a funny reply when the bot is mentionned."""

        if message.guild:
            if message.guild.id != 489435669215707148:  # Les GrandMasters
                return

        ctx = await self.bot.get_context(message)

        if ctx.me.mentioned_in(message) \
                and not message.author.bot \
                and not message.mention_everyone \
                and not message.content.startswith(self.bot.command_prefix):

            out_str = np.random.choice(self.quotes)
            await self.send_typing_delay(ctx.channel)
            await ctx.send(out_str)

    @commands.group(aliases=['turnips', 'navet', 'navets'],
                    invoke_without_command=True)
    async def turnip(self, ctx, member: discord.Member = None):
        """Command group to manage and check the turnip prices."""

        if member is None:
            member = ctx.author

        data = await self._get_member_data(member)
        turnip_emoji = self.bot.get_emoji(697120729476497489)  # turnip_badge

        if data is None:
            # The member has no data saved
            await ctx.send(f'No data saved for member {member.display_name}')
            return

        prices = await self._get_turnip_prices(member)
        url = await self._get_turnip_url(member)

        if len(prices) == 0 or prices[0] is None:
            bought_str = (
                'You did not buy turnips this week, '
                'or did not save the price.'
                )

        else:
            bought_str = (
                f'You bought turnips for {prices[0]} bells this week.'
                )

        prices_array = np.array(prices[1:], dtype=np.float64)
        if not np.isnan(prices_array).all():
            price_max = np.nanmax(prices_array)
            price_min = np.nanmin(prices_array)
            min_max_str = (
            f'The maximum sell price was {int(price_max)} bells.\n'
            f'The lowest sell price was {int(price_min)} bells.\n'
            )
        else:
            min_max_str = ''

        description = (
            f'{bought_str}\n'
            f'{min_max_str}'
            f'[Your prices on Turnip Prophet]({url})'
            )

        graph = await self.bot.loop.run_in_executor(
            None, self._turnip_plot, prices)
        graph_file = discord.File(graph, filename='graph.png')

        embed = discord.Embed(
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
        """Explain the different turnip patterns."""

        await ctx.send(':warning: Work in progress')

    @turnip.command(name='price', aliases=['prix'])
    async def turnip_price(self, ctx, weekday: WeekDay, am_pm: AmPm,
                           price: int):
        """Register the price of turnips for a given period.
        Example syntax:
            !turnip price Monday AM 123
            !turnip price fri pm 90
            !turnip price WED PM 101
        """

        weekday_str = f'{WeekDay.weekdays[weekday][1]}'
        if weekday != 6:  # not sunday
            weekday_str += f'_{AmPm.am_pm[am_pm]}'

        await self._save_turnip_price(ctx.author, weekday_str, price)
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

        if ctx.args[2] == 6:  # weekday == Sunday
            # TODO: use menu to ask for first-time buyer and previous pattern
            m = menus.ResetConfirm(
                'It is Sunday, do you want to reset your prices for the week?')
            reset = await m.prompt(ctx)

            if reset:
                await self._reset_week(ctx.author)

                options = {}
                m = menus.FirstTimeMenu()
                options['first_time'] = await m.prompt(ctx)

                m = menus.PreviousPatternMenu()
                options['previous_pattern'] = await m.prompt(ctx)

                await self._save_options(ctx.author, options)

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

    @turnip.command(name='reset')
    async def turnip_reset(self, ctx):
        """Reset the turnip data."""

        m = menus.ResetConfirm('Reset your data?')
        reset = await m.prompt(ctx)

        if reset:
            await self._reset_week(ctx.author)

    def _turnip_plot(self, prices):
        """Plot the turnip price evolution."""

        fig, ax = plt.subplots(figsize=(6, 4))
        if prices[0]:
            ax.axhline(prices[0], color='r', label='Bought At')
        ax.plot(prices[1:], '-o', c='C2', ms=8, label='Price Evolution')
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

    @tasks.loop(count=1)
    async def _create_tables(self):
        """Create the necessary DB tables if they do not exist."""

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS acnh_turnip(
                user_id      INTEGER PRIMARY KEY,
                first_time   INTEGER DEFAULT 1,
                prev_pattern INTEGER DEFAULT NULL,
                sun          INTEGER,
                mon_am       INTEGER,
                mon_pm       INTEGER,
                tue_am       INTEGER,
                tue_pm       INTEGER,
                wed_am       INTEGER,
                wed_pm       INTEGER,
                thu_am       INTEGER,
                thu_pm       INTEGER,
                fri_am       INTEGER,
                fri_pm       INTEGER,
                sat_am       INTEGER,
                sat_pm       INTEGER
            )
            """
            )

        await self.bot.db.commit()

    async def _get_member_data(self, member):
        """Return the turnip data the user has registered."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM acnh_turnip
                 WHERE user_id = :user_id
                """,
                {'user_id': member.id}
                ) as c:
            row = await c.fetchone()

        return row

    async def _get_turnip_prices(self, member):
        """Return the turnip prices the user has registered."""

        data = await self._get_member_data(member)
        if data is None:
            return []
        return data[3:]

    async def _get_turnip_url(self, member):
        """Generate the URL for the web turnip tracker."""

        data = await self._get_member_data(member)
        if data is None:
            return

        options = {}
        options['prices'] = '.'.join(
            [str(p) if p is not None else '' for p in data[3:]])
        options['first'] = str(bool(data['first_time'])).lower()
        options['pattern'] = data['prev_pattern']
        options_str = '&'.join(
            [f'{key}={value}' for key, value in options.items()])

        url = f'{TURNIP_PROPHET_BASE}{options_str}'
        return url

    async def _save_turnip_price(self, member, day, price):
        """Save the price of a member's turnips for a given day (AM/PM)."""

        await self.bot.db.execute(
            f"""
            UPDATE acnh_turnip
               SET {day} = :price
             WHERE user_id = :user_id
            """,
            {'price': price, 'user_id': member.id}
            )
        await self.bot.db.commit()

    async def _save_options(self, member, options):
        """Save the options for this week's prices
        (first time buy, previous pattern) of a member.
        """

        options.update({'user_id': member.id})
        await self.bot.db.execute(
            """
            UPDATE acnh_turnip
               SET first_time = :first_time,
                   prev_pattern = :previous_pattern
             WHERE user_id = :user_id
            """,
            options
            )

    async def _reset_week(self, member):
        """Reset the prices for a member's turnips."""

        await self.bot.db.execute(
            """
            DELETE FROM acnh_turnip
             WHERE user_id = :user_id
            """,
            {'user_id': member.id}
            )
        await self.bot.db.execute(
            """
            INSERT INTO acnh_turnip(user_id)
            VALUES (:user_id)
            """,
            {'user_id': member.id}
            )
        await self.bot.db.commit()
