import asyncio
from datetime import datetime
import io
import json
import os
import re
from string import Template

import discord
from discord.ext import commands, tasks
from discord.ext.menus import MenuPages
import matplotlib.pyplot as plt
import numpy as np

from ..utils.cogs import BasicCog
from . import menus
from . import objects


class InvalidCode(Exception):
    """Raised when the code provided isn't a valid AC:NH code."""
    pass


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

    @commands.group(invoke_without_command=True)
    async def acnh(self, ctx):
        """Command group to check and register AC:NH information."""

        all_profile_data = await self._get_all_profile_data()

        menu = MenuPages(
            source=menus.ProfileSource(all_profile_data),
            clear_reactions_after=True
        )
        await menu.start(ctx)

    @acnh.command(name='card', aliases=['passport', 'profile'])
    async def acnh_card(self, ctx, member: discord.Member = None):
        """Check your or someone else's AC:NH profile card."""

        if member is None:
            member = ctx.author

        profile_data = await self._get_profile_data(member)

        profile_picture = io.BytesIO(profile_data['profile_picture'])
        resident_picture = discord.File(
            profile_picture, filename='resident_picture.png')

        thumbnail_url = f'attachment://{resident_picture.filename}'

        embed = menus.make_profile_embed(member, profile_data, thumbnail_url)

        await ctx.send(embed=embed, file=resident_picture)

    @acnh.command(name='creators', aliases=['creator', 'designs', 'design'])
    async def acnh_creators(self, ctx):
        """Get the list of registered Creator IDs."""

        embed = await self._make_codes_embed(
            ctx, 'creator_id', 'Creator IDs')

        await ctx.send(embed=embed)

    @acnh.command(name='dreams', aliases=['dream'])
    async def acnh_dreams(self, ctx):
        """Get the list of registered Dream Addresses."""

        embed = await self._make_codes_embed(
            ctx, 'dream_address', 'Dream Addresses')

        await ctx.send(embed=embed)

    @acnh.command(name='friends', aliases=['friend'])
    async def acnh_friends(self, ctx):
        """Get the list of registered Friend Codes."""

        embed = await self._make_codes_embed(
            ctx, 'friend_code', 'Friend Codes')

        await ctx.send(embed=embed)

    @acnh.command(name='form')
    @commands.dm_only()
    async def acnh_form(self, ctx, *, form: str):
        """Send the filled out form and save it."""

        profile_data = [re.split(r':\s?', line) for line in form.split('\n')]
        for data in profile_data:
            if data[1] == '':
                data[1] = None

        profile_data = dict(profile_data)

        # parse hemisphere and native_fruit
        profile_data['hemisphere'] = self._parse_hemisphere(
            profile_data['hemisphere'])

        profile_data['native_fruit'] = self._parse_native_fruit(
            profile_data['native_fruit'])

        # parse friend_code, creator_id and dream_address
        code_prefix = {
            'friend_code': 'SW',
            'creator_id': 'MA',
            'dream_address': 'DA',
        }
        for c in ('friend_code', 'creator_id', 'dream_address'):
            code = profile_data[c]
            if code is not None:
                parsed = self._parse_acnh_code(code)
                profile_data[c] = f'{code_prefix[c]}-{parsed}'

        await self._save_profile_data(ctx.author, profile_data)

        await ctx.send('I successfully saved your information! Thank you!')

    @acnh_form.error
    async def acnh_form_error(self, ctx, error):
        """Error handler for the form filing process."""

        await ctx.send(
            'There was an error filling out the form. '
            'Do not forget to copy-paste the form in full before '
            'filling it out! (You can leave sections empty though)'
        )
        raise error

    @acnh.command(name='picture')
    @commands.dm_only()
    async def acnh_picture(self, ctx):
        """Register a picture for the AC:NH profile card.
        Attach a picture when typing the command, so that the message you send
        has the command and the picture file.
        """

        picture = ctx.message.attachments[0]

        await self._save_profile_picture(ctx.author, picture)

        await ctx.send('I successfully saved your picture! Thank you!')

    @acnh_picture.error
    async def acnh_picture_error(self, ctx, error):
        """Error handler for the acnh_picture command."""

        await ctx.send(f'There was an error:\n{error}')

    @acnh.command(name='register')
    async def acnh_register(self, ctx):
        """Start the registration process for the AC:NH profile card."""

        member = ctx.author
        try:
            await member.send(
                'Let\'s begin creating your Animal Crossing: New Horizons '
                'profile card, shall we? I will ask you a few questions.'
            )
        except discord.Forbidden:
            await ctx.send(
                'I cannot send you private messages... :('
            )
            return

        with open(os.path.join(
                self._cog_path, 'acnh_profile_card_template.txt')) as f:
            template = Template(f.read())

        example_data = {
            'resident_name': 'HatBot',
            'island_name': 'HatLand',
            'hemisphere': 'north',
            'native_fruit': 'orange',
            'friend_code': 'SW-1234-1234-1234',
            'creator_id': '',
            'dream_address': 'DA-9012-9012-9012',
        }

        hint_data = {
            'resident_name': '<Name Here>',
            'island_name': '<Island Name Here>',
            'hemisphere': '<north or south>',
            'native_fruit': '<apple, cherry, orange, peach, or pear>',
            'friend_code': 'SW-xxxx-xxxx-xxxx',
            'creator_id': 'MA-xxxx-xxxx-xxxx',
            'dream_address': 'DA-xxxx-xxxx-xxxx',
        }

        await member.send(
            'I would like some information first. I will send you a form '
            'that you will need to fill out. Once it is done you can send it '
            'back with the command `!acnh form <copy filled form here>`.'
            'Here is an example of a command with the filled form, with'
            'possible data ommited if you do not want to provide it:\n'
            f'```\n!acnh form\n{template.substitute(example_data)}\n```\n'
            'You can also upload a picture of your character! '
            'Simply send the command `!acnh picture` with the file attached '
            'to the message, and you will be good to go!\n'
            f'Here is the form:'
        )

        await member.send(f'```\n{template.substitute(hint_data)}```')

    @acnh.command(name='update')
    @commands.dm_only()
    async def acnh_update(self, ctx, *, form: str = None):
        """Update your AC:NH profile information."""

        if form is None:
            with open(os.path.join(
                    self._cog_path, 'acnh_profile_card_template.txt')) as f:
                template = Template(f.read())

            profile_data = dict(await self._get_profile_data(ctx.author))

            # remove None from the dict
            for key in profile_data.keys():
                if profile_data[key] is None:
                    profile_data[key] = ''

            # change the repr of hemisphere and native_fruit
            hem = profile_data['hemisphere']
            try:
                profile_data['hemisphere'] = objects.PROFILE_HEMISPHERE[hem]
            except TypeError:
                profile_data['hemisphere'] = ''

            fruit = profile_data['native_fruit']
            try:
                profile_data['native_fruit'] = objects.PROFILE_FRUIT[fruit]
            except TypeError:
                profile_data['native_fruit'] = ''

            await ctx.send(
                'You requested to update your AC:NH profile information. '
                'Here is what you have provided already, you can copy it '
                'and edit what you want to add or remove, then send it back '
                'with the command `!acnh update <copy filled form here>`.'
            )
            await ctx.send(
                f'```\n{template.substitute(profile_data)}\n```'
            )

        else:
            # call the acnh_form method with the form
            await self.acnh_form(ctx=ctx, form=form)

    async def _make_codes_embed(self, ctx, code_type, embed_title):

        codes = await self._get_all_profile_codes(code_type)
        lines = []
        for code in codes:
            if code[code_type] is not None:
                member = ctx.guild.get_member(code['user_id'])
                line = f'{member.mention}: **{code[code_type]}**'
                lines.append(line)

        embed = discord.Embed(
            title=f'Animal Crossing: New Horizons {embed_title}',
            timestamp=datetime.utcnow(),
            color=objects.PROFILE_EMBED_COLOR,
            description='\n'.join(lines),
        ).set_thumbnail(
            url=objects.PROFILE_CODE_THUMBNAIL[code_type],
        )

        return embed

    def _parse_hemisphere(self, hem):
        if hem is not None:
            return ('north', 'south').index(hem.lower())

    def _parse_native_fruit(self, nf):
        if nf is not None:
            return (
                'apple',
                'cherry',
                'orange',
                'peach',
                'pear',
            ).index(nf.lower())

    def _parse_acnh_code(self, code):
        code = code.strip()
        extract_digits = re.compile('([0-9]{4})')
        match = re.compile(
            '^(?:(?:DA)|(?:SW)|(?:MA)|(?:da)|(?:sw)|(?:ma))?(?:-?[0-9]{4}){3}$'
        )

        if re.fullmatch(match, code):
            digits = re.findall(extract_digits, code)

        else:
            raise InvalidCode(f'Code {code} is not valid.')

        return '-'.join(digits)

    @commands.group(aliases=['turnips', 'navet', 'navets'],
                    invoke_without_command=True)
    async def turnip(self, ctx, member: discord.Member = None):
        """Command group to manage and check the turnip prices."""

        if member is None:
            member = ctx.author

        data = await self._get_turnip_member_data(member)
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
            color=objects.TURNIP_EMBED_COLOR,
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
            m = menus.TurnipResetConfirm(
                'It is Sunday, do you want to reset your prices for the week?')
            reset = await m.prompt(ctx)

            if reset:
                await self._reset_turnip_week(ctx.author)

                options = {}
                # TODO: don't ask if the value is already set to False
                m = menus.TurnipFirstTimeMenu()
                options['first_time'] = await m.prompt(ctx)

                m = menus.TurnipPreviousPatternMenu()
                options['previous_pattern'] = await m.prompt(ctx)

                await self._save_turnip_options(ctx.author, options)

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

        m = menus.TurnipResetConfirm('Reset your data?')
        reset = await m.prompt(ctx)

        if reset:
            await self._reset_turnip_week(ctx.author)

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
            CREATE TABLE IF NOT EXISTS acnh_profile(
                user_id         INTEGER PRIMARY KEY,
                creator_id      TEXT,
                dream_address   TEXT,
                friend_code     TEXT,
                hemisphere      INTEGER,
                island_name     TEXT,
                native_fruit    INTEGER,
                profile_picture BLOB,
                resident_name   TEXT
            )
            """
        )

        await self.bot.db.commit()

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

    async def _create_empty_profile_data(self, member):
        """Create the empty entry in the database if it does not exist."""

        await self.bot.db.execute(
            """
            INSERT OR IGNORE INTO acnh_profile(user_id)
            VALUES (:user_id)
            """,
            {'user_id': member.id}
        )
        await self.bot.db.commit()

    async def _get_all_profile_data(self):
        """Return a list of all the profiles data."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM acnh_profile
                """
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_all_profile_codes(self, code_type):
        """Return a list of all the codes of a given type.
        Valid code types are friend_code, creator_id, and dream_address.
        """
        async with self.bot.db.execute(
            f"""
            SELECT user_id, {code_type}
              FROM acnh_profile
            """
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_profile_data(self, member):
        """Return the profile data for the given member."""

        # creates it if it does not exist
        await self._create_empty_profile_data(member)

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM acnh_profile
                 WHERE user_id = :user_id
                """,
                {'user_id': member.id}
        ) as c:
            row = await c.fetchone()

        return row

    async def _save_profile_data(self, member, data):
        """Save the data to the database."""

        # creates it if it does not exist
        await self._create_empty_profile_data(member)

        data['user_id'] = member.id

        await self.bot.db.execute(
            """
            UPDATE acnh_profile
               SET creator_id    = :creator_id,
                   dream_address = :dream_address,
                   friend_code   = :friend_code,
                   hemisphere    = :hemisphere,
                   island_name   = :island_name,
                   native_fruit  = :native_fruit,
                   resident_name = :resident_name
             WHERE user_id       = :user_id
            """,
            data
        )
        await self.bot.db.commit()

    async def _save_profile_picture(self, member, attachment):
        """Save the picture as a BLOB in the database."""

        # creates it if it does not exist
        await self._create_empty_profile_data(member)

        await self.bot.db.execute(
            """
            UPDATE acnh_profile
               SET profile_picture = :profile_picture
             WHERE user_id = :user_id
            """,
            {'profile_picture': await attachment.read(), 'user_id': member.id}
        )
        await self.bot.db.commit()

    async def _get_turnip_member_data(self, member):
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

        data = await self._get_turnip_member_data(member)
        if data is None:
            return []
        return data[3:]

    async def _get_turnip_url(self, member):
        """Generate the URL for the web turnip tracker."""

        data = await self._get_turnip_member_data(member)
        if data is None:
            return

        options = {}
        options['prices'] = '.'.join(
            [str(p) if p is not None else '' for p in data[3:]])
        options['first'] = str(bool(data['first_time'])).lower()
        options['pattern'] = data['prev_pattern']
        options_str = '&'.join(
            [f'{key}={value}' for key, value in options.items()])

        url = f'{objects.TURNIP_PROPHET_BASE}{options_str}'
        return url

    async def _save_turnip_price(self, member, day, price):
        """Save the price of a member's turnips for a given day (AM/PM)."""

        await self.bot.db.execute(
            """
            INSERT OR IGNORE INTO acnh_turnip(user_id)
            VALUES (:user_id)
            """,
            {'user_id': member.id}
        )

        await self.bot.db.execute(
            f"""
            UPDATE acnh_turnip
               SET {day} = :price
             WHERE user_id = :user_id
            """,
            {'price': price, 'user_id': member.id}
        )
        await self.bot.db.commit()

    async def _save_turnip_options(self, member, options):
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

    async def _reset_turnip_week(self, member):
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
