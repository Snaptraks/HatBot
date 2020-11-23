from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from . import menus

from ..utils.checks import has_role_or_above
from ..utils.cogs import BasicCog

# GIVEAWAY_TIME = timedelta(hours=24)
GIVEAWAY_TIME = timedelta(seconds=15)


class Giveaways(BasicCog):
    """Cog for giving away games back to the community."""

    def __init__(self, bot):
        super().__init__(bot)
        self._create_tables.start()
        self.reload_menus.start()

    @tasks.loop(count=1)
    async def reload_menus(self):
        """Reload menus upon startup."""

        giveaways = await self._get_giveaways()

        for giveaway in giveaways:
            channel = (self.bot.get_channel(giveaway['channel_id'])
                       or await self.bot.fetch_channel(giveaway['channel_id']))
            message = await channel.fetch_message(giveaway['message_id'])
            ctx = await self.bot.get_context(message)

            self.bot.loop.create_task(
                self.giveaway_task(
                    ctx,
                    giveaway_data=giveaway,
                    message=message,
                    timeout=None,
                )
            )

    @reload_menus.before_loop
    async def reload_menus_before(self):
        await self.bot.wait_until_ready()

    @commands.group(aliases=["ga"])
    async def giveaway(self, ctx):
        """Commands to control the giveaways."""

        pass

    # @commands.is_owner()
    @giveaway.group(name="remaining", invoke_without_command=True)
    async def giveaway_remaining(self, ctx):
        """Count of the remaining available games for the giveaway."""

        remaining = await self._get_remaining()

        await ctx.send(f"{len(remaining)} remaining games.")

    @giveaway_remaining.command(name="list")
    async def giveaway_remaining_list(self, ctx):
        """List of the remaining available games for the giveaway."""

        remaining = await self._get_remaining()
        remaining_str = '\n'.join([g['title'] for g in remaining])

        await ctx.send(
            f"{len(remaining)} remaining games:\n"
            f"```\n{remaining_str}\n```"
        )

    @has_role_or_above('Mod')
    @giveaway.command(name='start')
    async def giveaway_start(self, ctx):
        """Start one giveaway event."""

        game = await self._get_random_game()
        if game is None:
            await ctx.send("No more games!")
            return

        giveaway_id = await self._create_giveaway(game['game_id'])
        giveaway_data = await self._get_giveaway(giveaway_id)

        self.bot.loop.create_task(
            self.giveaway_task(
                ctx,
                giveaway_data=giveaway_data,
                timeout=None,
            )
        )

    async def giveaway_task(self, ctx, **kwargs):
        """Start one giveaway task.
        Will send the message in the channel where `!giveaway start`
        was invoked.
        """
        game = kwargs.get('giveaway_data')
        menu = menus.GiveawayMenu(**kwargs)
        await menu.start(ctx)

        await discord.utils.sleep_until(game['trigger_at'])
        winner = await menu.stop()

        if winner is None:
            # If list is empty, remove key from steam_keys_given
            # and delete the giveaway
            await self._edit_game_given(game['game_id'], False)
            return

        try:
            await winner.send(
                f"Congratulations! You won the giveaway for "
                f"**{game['title']}**!\n"
                f"Your Steam key is ||{game['key']}|| ."
            )
        except discord.Forbidden:
            app_info = await self.bot.application_info()
            await app_info.owner.send(
                f"Could not DM {winner.display_name} "
                f"({winner.mention}). They won the giveaway for "
                f"**{game['title']}** with key ||{game['key']}||."
            )

    @tasks.loop(count=1)
    async def _create_tables(self):
        """Create the necessary tables if they do not exist."""

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS giveaways_game(
                game_id INTEGER NOT NULL PRIMARY KEY,
                given   INTEGER DEFAULT 0,
                key     TEXT    NOT NULL,
                title   TEXT    NOT NULL,
                url     TEXT    NOT NULL,
                UNIQUE (key)
            )
            """
        )

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS giveaways_giveaway(
                giveaway_id INTEGER   NOT NULL PRIMARY KEY,
                channel_id  INTEGER,
                created_at  TIMESTAMP,
                is_done     INTEGER   DEFAULT 0,
                game_id     INTEGER   NOT NULL,
                message_id  INTEGER,
                trigger_at  TIMESTAMP NOT NULL,
                FOREIGN KEY (game_id)
                    REFERENCES giveaways_game (game_id)
            )
            """
        )

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS giveaways_entry(
                giveaway_id INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                FOREIGN KEY (giveaway_id)
                    REFERENCES giveaways_giveaway (giveaway_id)
                UNIQUE (giveaway_id, user_id)
            )
            """
        )

        await self.bot.db.commit()

    # @_create_tables.after_loop
    async def _insert_fake_games(self):
        await self.bot.db.executemany(
            """
            INSERT OR IGNORE INTO giveaways_game(key, title, url)
            VALUES (:key,
                    :title,
                    :url)
            """,
            [
                {
                    'key': '12345-12345-12345',
                    'title': 'game name here',
                    'url': 'https://store.steampowered.com',
                },
                {
                    'key': 'ABCDE-ABCDE-ABCDE',
                    'title': 'another game',
                    'url': 'https://store.steampowered.com',
                },
                {
                    'key': '12345-GHJKL-54321',
                    'title': 'one more for the trip',
                    'url': 'https://store.steampowered.com'
                },
            ]
        )

        await self.bot.db.commit()

    async def _create_giveaway(self, game_id):
        """Create the DB entry for the giveaway."""

        async with self.bot.db.execute(
                """
                INSERT INTO giveaways_giveaway (game_id, trigger_at)
                VALUES (:game_id,
                        :trigger_at)
                """,
                {
                    'game_id': game_id,
                    'trigger_at': datetime.utcnow() + GIVEAWAY_TIME,
                }
        ) as c:
            giveaway_id = c.lastrowid

        await self.bot.db.commit()

        return giveaway_id

    async def _get_giveaway(self, giveaway_id):
        """Get the data on the giveaway from the DB."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM giveaways_giveaway AS giveaway
                       INNER JOIN giveaways_game AS game
                       ON giveaway.game_id = game.game_id
                 WHERE giveaway_id = :giveaway_id
                """,
                {
                    'giveaway_id': giveaway_id,
                }
        ) as c:
            row = await c.fetchone()

        return row

    async def _get_giveaways(self):
        """Return the list of giveaways that are not done yet."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM giveaways_giveaway AS giveaway
                       INNER JOIN giveaways_game AS game
                       ON giveaway.game_id = game.game_id
                 WHERE is_done = 0
                """
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_remaining(self):
        """Return the list of remaining games."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM giveaways_game
                 WHERE given = 0
                 ORDER BY title ASC
                """
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_random_game(self):
        """Return a random game that is not given yet.
        If None is returned, it means there are no available games yet.
        """
        async with self.bot.db.execute(
                """
                SELECT *
                  FROM giveaways_game
                 WHERE given = 0
                 ORDER BY RANDOM()
                 LIMIT 1
                """
        ) as c:
            row = await c.fetchone()

        if row:
            await self._edit_game_given(row['game_id'], True)

        return row

    async def _edit_game_given(self, game_id, given):
        """Mark the game as given (or not, if no one wins it)."""

        await self.bot.db.execute(
            """
            UPDATE giveaways_game
               SET given = :given
             WHERE game_id = :game_id
            """,
            {
                'game_id': game_id,
                'given': int(given),
            }
        )

        await self.bot.db.commit()
