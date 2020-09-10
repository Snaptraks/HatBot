import asyncio
from datetime import datetime, timedelta
import json

import numpy as np
import discord
from discord.ext import commands, tasks

from ..utils.cogs import FunCog


CANDY = [
    '\U0001F36B',  # :chocolate_bar:
    '\U0001F36C',  # :candy:
    '\U0001F36D',  # :lollipop:
]

BUG = [
]


def get_random_candy():
    """Return the ID and unicode for a random candy."""

    candy_id = np.random.randint(len(CANDY))
    candy = CANDY[candy_id]

    return candy_id, candy


def get_next_halloween():
    """Return the next Halloween day (Oct. 31).
    If Halloween in the current year is already passed, return
    the day for next year.
    """
    now = datetime.utcnow()
    halloween = datetime(year=now.year, month=10, day=31)

    if (halloween - now).total_seconds() < 0:
        halloween = halloween.replace(year=halloween.year + 1)

    return halloween


def format_candy_bag(row):
    """Nicely format the candy bag into a mostly square grid."""

    candy_list = []
    for key in row.keys():
        if key.startswith('candy_'):
            candy_id = int(key[key.rindex('_') + 1:])
            candy_list += [CANDY[candy_id]] * row[key]

    np.random.shuffle(candy_list)
    n_candy = len(candy_list)
    side = int(np.sqrt(n_candy))
    candy_array = np.array_split(candy_list, side)

    return '\n'.join(' '.join(row) for row in candy_array)


class Halloween(FunCog):
    """Cog for Halloween day!
    Enables trick-or-treating, with candy and a special trick!
    """

    def __init__(self, bot):
        super().__init__(bot)
        self.halloween_day = get_next_halloween()

        with open('cogs/Halloween/halloween_names.json', 'r') as f:
            names = json.load(f)
        first_names = names['first_names']
        names['first_names'] = first_names[0] + first_names[1]
        self.names = names

        self.got_channel = asyncio.Event()
        self.announcement_ids = None

        self._create_tables.start()
        self.get_channel.start()
        self.halloween_event.start()
        self.halloweenify.start()

    def cog_check(self, ctx):
        halloween_before = self.halloween_day - timedelta(hours=12)
        halloween_after = self.halloween_day + timedelta(hours=36)
        # due to TZ
        is_halloween = halloween_before < datetime.utcnow() < halloween_after

        return super().cog_check(ctx) and is_halloween

    def cog_unload(self):
        super().cog_unload()
        self.halloween_event.cancel()
        self.halloweenify.cancel()

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.add_reaction('\U0000231B')  # :hourglass:

        else:
            raise error

    @tasks.loop(count=1)
    async def get_channel(self):
        """Get the channel where the even takes place before starting it."""

        await self.bot.wait_until_ready()
        # Hatventures Community #hatbot-pond
        self.channel = self.bot.get_channel(548606793656303625)

        self.got_channel.set()

    @tasks.loop(count=1)
    async def halloween_event(self):
        """Announce the beginning of the Halloween event, with some help
        about the new commands.
        """
        await self.got_channel.wait()

        row = await self._maybe_get_announcement_ids(self.channel)
        if row:
            self.announcement_ids = (row['channel_id'], row['message_id'])

        else:

            out_str = (
                'Happy Halloween @everyone! Today we have a special event '
                'where you can collect candy from `!trickortreat`ing or '
                'simply having discussions here on the Discord server. '
                'So if you see a candy popping up after one of your messages, '
                'be sure to pick it up!\n\n'
                'Be warned though, I am a playful being and might trick you '
                'while you are trick-or-treating! '
                'If you are the adventurous type, you can ask for a `!trick` '
                'directly and I will cast my magic upon you!\n\n'
                'Once you have collected many candies, you can check your '
                '`!bag` to see now many you collected! '
                'Here are some free ones to get you started. '
                'Happy trick-or-treating!'
            )
            await discord.utils.sleep_until(self.halloween_day)
            announcement_message = await self.channel.send(out_str)
            self.announcement_ids = (
                announcement_message.channel.id,
                announcement_message.id,
            )
            # save IDs in DB / memory
            await self._save_announcement_ids(announcement_message)

            # add candy reactions
            for candy in CANDY:
                await announcement_message.add_reaction(candy)

            await announcement_message.pin()

    @tasks.loop(count=1)
    async def halloweenify(self):
        """Change the Bot's profile picture and guild nickname a week before
        Halloween to something sp00py. Reset everything the day after
        Halloween.
        """
        await self.got_channel.wait()
        week_before = self.halloween_day - timedelta(weeks=1)
        day_after = self.halloween_day + timedelta(days=2)  # due to TZ
        bot_member = self.channel.guild.me

        # change nickname
        await discord.utils.sleep_until(week_before)
        await bot_member.edit(nick='BatBot')
        # remind owner to change avatar
        await self.bot.owner.send(
            'Please change my picture to the Halloween one!'
        )

        # reset nickname to normal
        await discord.utils.sleep_until(day_after)
        await bot_member.edit(nick=None)
        # remind owner to change avatar
        await self.bot.owner.send(
            'Please change my picture to the Normal one!'
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        """React with a random candy to some messages. The author can then
        collect the candy and add it to their bag.
        """
        r = np.random.randint(20)
        # technically we should pass a `Context` object, so let's hope it's ok
        if (self.cog_check(message)
                and not message.content.startswith(self.bot.command_prefix)
                and not message.author.bot):

            if r == 0:
                candy_id, candy = get_random_candy()

                def check(reaction, member):
                    valid = (
                        member == message.author
                        and reaction.message.id == message.id
                        and reaction.emoji == candy
                    )

                    return valid

                await message.add_reaction(candy)
                reaction, member = await self.bot.wait_for(
                    'reaction_add', check=check)

                await self._give_candy(message.author, candy_id)

                await message.clear_reactions()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Listener for the free candy on the Halloween Event
        announcement message.
        """
        if self.announcement_ids is None:
            return  # avoid errors on load time

        is_channel = payload.channel_id == self.announcement_ids[0]
        is_message = payload.message_id == self.announcement_ids[1]
        if payload.guild_id:
            is_not_bot = not payload.member.bot  # will error if not in a guild
        else:
            # True or False shouldn't matter since is_channel will be False
            # if the reaction is added in a DM anyway.
            is_not_bot = False
        is_candy = payload.emoji.name in CANDY

        if is_channel and is_message and is_not_bot and is_candy:
            row = await self._get_candy(payload.member)
            candy_id = CANDY.index(payload.emoji.name)
            free_candy = f'free_candy_{candy_id}'

            if row[free_candy] == 0:
                await self._give_candy(payload.member, candy_id)
                await self._toggle_free_candy(payload.member, candy_id)

    @commands.command()
    async def bag(self, ctx):
        """Show the content of your Halloween bag."""

        row = await self._get_candy(ctx.author)
        n_candy = row['candy_0'] + row['candy_1'] + row['candy_2']
        if n_candy > 0:
            bag = format_candy_bag(row)
        else:
            bag = '\U0001f578'  # :spider_web:

        embed = discord.Embed(
            color=0xEB6123,
        ).set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.avatar_url_as(static_format='png'),
        ).add_field(
            name='Content of your Halloween bag',
            value=bag,
        ).set_footer(
            text='Happy Halloween!'
        )

        await ctx.send(embed=embed)

    @commands.cooldown(1, 15 * 60, commands.BucketType.member)
    @commands.command(name='trickortreat', aliases=['tot'])
    async def trick_or_treat(self, ctx):
        """Get a candy, or a trick!"""

        await ctx.trigger_typing()
        await asyncio.sleep(2)

        r = np.random.randint(10)
        prefix = (
            "Aw, aren't you a cute one with your costume! "
            "I will see what I have for you...\n"
        )
        if r == 0:
            # TRICK
            old_nickname = ctx.author.display_name
            new_nickname = await self.change_nickname(ctx.author)
            suffix = (
                "IT'S A TRICK! Hahaha! Poof your name is now "
                f'**{new_nickname}**! Happy Halloween! :jack_o_lantern:'
            )

            await ctx.send(f'{prefix}{suffix}')
            await self.wait_and_revert(ctx.author, old_nickname)

        else:
            # TREAT
            candy_id, candy = get_random_candy()
            suffix = f'I have some candy! Happy Halloween! {candy}'

            await ctx.send(f'{prefix}{suffix}')
            await self._give_candy(ctx.author, candy_id)

    @commands.cooldown(1, 15 * 60, commands.BucketType.member)
    @commands.command()
    async def trick(self, ctx):
        """Change the author's nickname to a random one."""

        await ctx.trigger_typing()
        await asyncio.sleep(2)

        old_nickname = ctx.author.display_name
        new_nickname = await self.change_nickname(ctx.author)
        out_str = (
            'Oh, you want a trick? Well here you go!\n'
            f'Your name is now **{new_nickname}**! Happy Halloween! '
            ':jack_o_lantern:'
        )

        await ctx.send(out_str)
        await self.wait_and_revert(ctx.author, old_nickname)

    async def change_nickname(self, member):
        first = np.random.choice(self.names['first_names'])
        last = np.random.choice(self.names['last_names'])
        new_nickname = f'{first} {last}'

        try:
            await member.edit(nick=new_nickname, reason='Halloween Trick')

        except discord.Forbidden:
            # we don't have permissions, just ignore it
            pass

        return new_nickname

    async def wait_and_revert(self, member, old_nickname):
        """Wait 15 minutes and revert the member's display_name to
        what it was before the trick.
        """
        await asyncio.sleep(15 * 60)  # 15 minutes
        try:
            await member.edit(
                nick=old_nickname,
                reason='Revert Halloween Trick'
            )

        except discord.Forbidden:
            # we don't have permissions, just ignore it
            pass

    @tasks.loop(count=1)
    async def _create_tables(self):
        """Create the necessary DB tables if they do not exist."""

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS halloween_candy(
                user_id      INTEGER PRIMARY KEY,
                candy_0      INTEGER DEFAULT 0,
                candy_1      INTEGER DEFAULT 0,
                candy_2      INTEGER DEFAULT 0,
                free_candy_0 INTEGER DEFAULT 0,
                free_candy_1 INTEGER DEFAULT 0,
                free_candy_2 INTEGER DEFAULT 0
            )
            """
        )

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS halloween_message(
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL
            )
            """
        )

        await self.bot.db.commit()

    async def _create_or_ignore(self, member):
        """Create an empty DB entry for the member, or ignore if it
        already exists.
        """

        await self.bot.db.execute(
            """
            INSERT OR IGNORE INTO halloween_candy(user_id)
            VALUES (:user_id)
            """,
            {'user_id': member.id}
        )
        # purposefully do not commit yet

    async def _get_candy(self, member):
        """Get a member's amount of candy."""

        await self._create_or_ignore(member)

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM halloween_candy
                 WHERE user_id = :user_id
                """,
                {'user_id': member.id}
        ) as c:
            row = await c.fetchone()

        return row

    async def _give_candy(self, member, candy_id):
        """Increment the number of candy the member has."""

        await self._create_or_ignore(member)

        await self.bot.db.execute(
            f"""
            UPDATE halloween_candy
               SET candy_{candy_id} = candy_{candy_id} + 1
             WHERE user_id = :user_id
            """,
            {'user_id': member.id}
        )

        await self.bot.db.commit()

    async def _toggle_free_candy(self, member, candy_id):
        """Toggle the free_candy switch to same when a user gets its
        free candy of the type candy_id.
        """
        await self.bot.db.execute(
            f"""
            UPDATE halloween_candy
               SET free_candy_{candy_id} = 1
             WHERE user_id = :user_id
            """,
            {'user_id': member.id}
        )

        await self.bot.db.commit()

    async def _maybe_get_announcement_ids(self, channel):
        """Get the message and channel ids for the Halloween Event
        announcement message, if they were posted already.
        """

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM halloween_message
                 WHERE channel_id = :channel_id
                """,
                {'channel_id': channel.id}
        ) as c:
            row = await c.fetchone()

        return row

    async def _save_announcement_ids(self, message):
        """Save the message and channel ids for the Halloween Event
        announcement message.
        """

        await self.bot.db.execute(
            """
            INSERT INTO halloween_message
            VALUES (:channel_id, :message_id)
            """,
            {'channel_id': message.channel.id, 'message_id': message.id}
        )

        await self.bot.db.commit()
