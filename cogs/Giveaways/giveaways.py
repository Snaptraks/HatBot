from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from snapcogs import Bot
from snapcogs.utils.db import read_sql_query

from . import views


LOGGER = logging.getLogger(__name__)
SQL = Path(__file__).parent / "sql"

# GIVEAWAY_TIME = timedelta(hours=24)
GIVEAWAY_TIME = timedelta(seconds=15)
EMBED_COLOR = 0xB3000C


@dataclass
class Game:
    game_id: int
    given: bool
    key: str
    title: str
    url: str


@dataclass
class Giveaway:
    giveaway_id: int
    channel_id: int
    created_at: datetime
    game: Game
    game_id: int
    is_done: bool
    message_id: int
    trigger_at: datetime


class Giveaways(commands.Cog):
    """Cog for giving away games back to the community."""

    giveaway = app_commands.Group(
        name="giveaway",
        description="Commands to manage the games giveaway",
        default_permissions=discord.Permissions(mention_everyone=True),
    )

    def __init__(self, bot: Bot):
        self.bot = bot
        self.persistent_views_loaded = False
        self._tasks = {}

    async def cog_load(self):
        await self._create_tables()
        # await self.reload_menus()
        # await self._insert_fake_games()

    async def cog_unload(self):
        # cancel giveaways tasks when unloading to prevent duplicates
        for t in self._tasks.values():
            t.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_loaded:
            # await self.reload_menus()
            self.persistent_views_loaded = True

    async def reload_menus(self):
        """Reload menus upon startup."""

        await self.bot.wait_until_ready()
        giveaways = await self._get_ongoing_giveaways()

        for giveaway in giveaways:
            giveaway_id = giveaway["giveaway_id"]
            channel = self.bot.get_channel(
                giveaway["channel_id"]
            ) or await self.bot.fetch_channel(giveaway["channel_id"])
            message = await channel.fetch_message(giveaway["message_id"])
            ctx = await self.bot.get_context(message)

            self._tasks[giveaway_id] = self.bot.loop.create_task(
                self.giveaway_task(
                    ctx,
                    giveaway_data=giveaway,
                    message=message,
                    timeout=None,
                )
            )

    async def save_presistent_view(
        self, view: views.GiveawayView, message: discord.InteractionMessage
    ) -> None:
        ...

    @giveaway.command(name="add")
    async def giveaway_add(self, interaction: discord.Interaction):
        ...

    @giveaway.command(name="remaining")
    async def giveaway_remaining(self, interaction: discord.Interaction):
        ...

    @giveaway.command(name="start")
    async def giveaway_start(self, interaction: discord.Interaction):
        """Start one giveaway event."""

        game = await self._get_random_game()
        if game is None:
            await interaction.response.send_message(
                "No more games! Sorry!", ephemeral=True
            )
            return

        LOGGER.debug(f"Giving game {game}")
        giveaway_id = await self._create_giveaway(game.game_id)
        if giveaway_id is None:
            raise ValueError("Giveaway ID cannot be None!")

        giveaway = await self._get_giveaway(giveaway_id)
        if giveaway is None:
            raise ValueError(f"Giveaway with ID {giveaway_id} does not exist!")

        view = views.GiveawayView()
        ends_in = discord.utils.format_dt(giveaway.trigger_at, style="R")
        embed = discord.Embed(
            color=EMBED_COLOR,
            description=(
                "# Giveaway!\n"
                "## We are giving away "
                f"[{game.title}]({game.url}).\n"
                "## Press the button to enter!\n"
                f"This giveaway ends {ends_in}"
            ),
        )
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        await self.save_presistent_view(view, message)

    @commands.group(aliases=["ga"])
    async def old_giveaway(self, ctx):
        """Commands to control the giveaways."""

        pass

    @old_giveaway.command(name="add")
    @commands.is_owner()
    async def old_giveaway_add(self, ctx):
        """Add a list of games to the DB.
        The command expects a .json file to be attached to the message.
        """

        file = ctx.message.attachments[0]
        content = await file.read()
        data = json.loads(content)
        await self._insert_games(data)
        await ctx.reply("Games were added to the DB!")

    @giveaway_add.error
    async def old_giveaway_add_error(self, ctx, error):
        """Error handler for the giveaway add command."""

        await ctx.reply(f"There was an error:\n{error}")
        raise error

    @old_giveaway.command(name="remaining")
    # @has_role_or_above("Mod")
    async def old_giveaway_remaining(self, ctx):
        """List of the remaining available games for the giveaway."""

        remaining = await self._get_remaining_games()
        remaining_titles = Counter([g["title"] for g in remaining])

        menu = menus.GameListMenu(
            source=menus.GameListSource(
                entries=list(remaining_titles.items()),
                per_page=10,
            ),
            clear_reactions_after=True,
        )

        await menu.start(ctx)

    @old_giveaway.command(name="start")
    # @has_role_or_above("Mod")
    async def old_giveaway_start(self, ctx):
        """Start one giveaway event."""

        game = await self._get_random_game()
        if game is None:
            await ctx.reply("No more games!")
            return

        giveaway_id = await self._create_giveaway(game["game_id"])
        giveaway_data = await self._get_giveaway(giveaway_id)

        self._tasks[giveaway_id] = self.bot.loop.create_task(
            self.old_giveaway_task(
                ctx,
                giveaway_data=giveaway_data,
                timeout=None,
            )
        )

    async def old_giveaway_task(self, ctx, **kwargs):
        """Start one giveaway task.
        Will send the message in the channel where `!giveaway start`
        was invoked.
        """
        game = kwargs.get("giveaway_data")
        menu = menus.GiveawayMenu(**kwargs)
        await menu.start(ctx)

        await discord.utils.sleep_until(game["trigger_at"])
        winner = await menu.stop()

        if winner is None:
            # If list is empty, remove key from steam_keys_given
            # and delete the giveaway
            await self._edit_game_given(game["game_id"], False)
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

    async def _create_tables(self):
        """Create the necessary tables if they do not exist."""

        await self.bot.db.execute(read_sql_query(SQL / "create_game_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_giveaway_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_entry_table.sql"))

        await self.bot.db.commit()

    # @_create_tables.after_loop
    async def _insert_fake_games(self):
        await self.bot.db.executemany(
            read_sql_query(SQL / "insert_games.sql"),
            [
                dict(
                    key="12345-12345-12345",
                    title="game name here",
                    url="https://store.steampowered.com",
                ),
                dict(
                    key="ABCDE-ABCDE-ABCDE",
                    title="another game",
                    url="https://store.steampowered.com",
                ),
                dict(
                    key="12345-GHJKL-54321",
                    title="one more for the trip",
                    url="https://store.steampowered.com",
                ),
            ],
        )

        await self.bot.db.commit()

    async def _create_giveaway(self, game_id: int) -> int | None:
        """Create the DB entry for the giveaway."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "create_giveaway.sql"),
            dict(
                game_id=game_id,
                trigger_at=discord.utils.utcnow() + GIVEAWAY_TIME,
            ),
        ) as c:
            giveaway_id = c.lastrowid

        await self.bot.db.commit()

        return giveaway_id

    async def _get_giveaway(self, giveaway_id: int) -> Giveaway | None:
        """Get the data on the giveaway from the DB."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_giveaway.sql"),
            dict(
                giveaway_id=giveaway_id,
            ),
        ) as c:
            giveaway_row = await c.fetchone()

        if giveaway_row is None:
            # exit early if giveaway doesn't exist
            return None

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_game.sql"),
            dict(
                game_id=giveaway_row["game_id"],
            ),
        ) as c:
            game_row = await c.fetchone()

        if game_row is not None:
            game = Game(**game_row)
            return Giveaway(**dict(giveaway_row), game=game)
        else:
            return None

    async def _get_ongoing_giveaways(self):
        """Return the list of giveaways that are not done yet."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_ongoing_giveaways.sql")
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_remaining_games(self):
        """Return the list of remaining games."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_remaining_games.sql")
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_random_game(self) -> Game | None:
        """Return a random game that is not given yet.
        If None is returned, it means there are no available games yet.
        """
        async with self.bot.db.execute(
            read_sql_query(SQL / "get_random_game.sql")
        ) as c:
            row = await c.fetchone()

        if row:
            await self._edit_game_given(row["game_id"], True)
            return Game(**row)
        else:
            return None

    async def _insert_games(self, list_of_games):
        """Add a list of games and keys to the DB."""

        await self.bot.db.executemany(
            read_sql_query(SQL / "insert_games.sql"),
            list_of_games,
        )

        await self.bot.db.commit()

    async def _edit_game_given(self, game_id, given):
        """Mark the game as given (or not, if no one wins it)."""

        await self.bot.db.execute(
            read_sql_query(SQL / "edit_game_given.sql"),
            {
                "game_id": game_id,
                "given": int(given),
            },
        )

        await self.bot.db.commit()
