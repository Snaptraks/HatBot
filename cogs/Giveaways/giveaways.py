import asyncio
import json
import logging
from collections import Counter
from datetime import date

import discord
from discord import HTTPException, app_commands
from discord.ext import commands
from snapcogs import Bot
from snapcogs.utils.db import read_sql_query

from ..utils.checks import NotOwner, is_owner
from .base import (
    EMBED_COLOR,
    GIVEAWAY_TIME,
    HVC_MC_SERVER_CHATTER,
    HVC_STAFF_ROLES,
    SQL,
    Game,
    Giveaway,
)
from .views import GiveawayView

LOGGER = logging.getLogger(__name__)


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

    async def cog_unload(self):
        # cancel giveaways tasks when unloading to prevent duplicates
        for t in self._tasks.values():
            t.cancel()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check to make sure commands for this Cog are only run in servers we want."""

        name = getattr(interaction.command, "qualified_name", "Unknown")
        LOGGER.debug(f"Running check for interaction {name}")
        guild_ids = {
            308049114187431936,  # HVC
            588171715960635393,  # BTS
        }
        if interaction.guild is None:
            return False
        return interaction.guild.id in guild_ids

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_loaded:
            await self.load_ongoing_giveaways()
            self.persistent_views_loaded = True

    async def load_ongoing_giveaways(self) -> None:
        for giveaway in await self._get_ongoing_giveaways():
            LOGGER.debug(f"Loading view for message {giveaway.message_id}")

            self._tasks[giveaway.giveaway_id] = asyncio.create_task(
                self.giveaway_task(
                    interaction=None,
                    giveaway=giveaway,
                )
            )

    async def giveaway_task(
        self,
        *,
        interaction: discord.Interaction | None,
        giveaway: Giveaway,
    ) -> None:
        """Main task that handles the giveaways."""

        ends_in = discord.utils.format_dt(giveaway.trigger_at, style="R")
        ends_at = discord.utils.format_dt(giveaway.trigger_at, style="F")
        game_title_link = giveaway.game.title_link
        if interaction is not None:
            # send initial message
            embed = discord.Embed(
                color=EMBED_COLOR,
                description=(
                    "# Hatventures Game Giveaway!\n"
                    f"### We are giving away {game_title_link}.\n"
                    "### Press the button to enter!\n"
                    f"This giveaway ends at {ends_at} ({ends_in})"
                ),
            )

            view = GiveawayView(self.bot, giveaway)
            await interaction.response.send_message(embed=embed, view=view)
            original_message = await interaction.original_response()
            await self._save_presistent_view(view, original_message)
            await self._update_giveaway(giveaway, original_message)

        else:
            view = await self._get_view(giveaway)
            self.bot.add_view(view, message_id=giveaway.message_id)

        await discord.utils.sleep_until(giveaway.trigger_at)
        view.stop()
        winner = await self._get_random_winner(giveaway)

        if winner is None:
            LOGGER.info(f"No winner for {giveaway}, marking game as still available.")
            await self._edit_game_given(giveaway.game, False)
            embed = discord.Embed(
                color=EMBED_COLOR,
                description=(
                    "# Better luck next time!\n"
                    f"No one entered the giveaway for {game_title_link}.\n"
                    "The prize goes back in the pool."
                ),
            )

        else:
            LOGGER.info(f"Sending game key for {giveaway.game.title} to {winner}")
            try:
                # sending message to winner
                await winner.send(
                    f"Congratulations! You won the giveaway for "
                    f"**{game_title_link}**!\n"
                    f"Your Steam key is ||{giveaway.game.key}|| ."
                )
            except discord.Forbidden:
                # cannot send to winner, sending message to bot owner
                LOGGER.info(
                    f"Could not send message to {winner}, sending to bot owner."
                )
                app_info = await self.bot.application_info()
                await app_info.owner.send(
                    f"Could not DM {winner.display_name} "
                    f"({winner.mention}). They won the giveaway for "
                    f"**{giveaway.game.title}** with key ||{giveaway.game.key}||."
                )

            LOGGER.info(f"Key sent to {winner}, editing original message")

            embed = discord.Embed(
                color=EMBED_COLOR,
                description=(
                    f"# Congratulations! \N{PARTY POPPER}\n"
                    f"### {winner.display_name} ({winner.mention}) "
                    f"won the giveaway for {game_title_link}.\n"
                    "### Congrats to them!\n"
                    f"This giveaway ended {ends_in}."
                ),
            )

            # send to mc-server-chatter
            mc_server_chatter = self.bot.get_partial_messageable(HVC_MC_SERVER_CHATTER)
            await mc_server_chatter.send(
                f"{winner.display_name} has won {giveaway.game.title} "
                "on the Discord server! You should join for a chance to win too ;)"
            )

        await self._end_giveaway(giveaway)

        channel = self.bot.get_partial_messageable(giveaway.channel_id)
        message = channel.get_partial_message(giveaway.message_id)
        try:
            await message.edit(embed=embed, view=None)
        except Exception:
            LOGGER.exception("There was an unhandled exception", exc_info=True)

    @giveaway.command(name="add")
    @app_commands.describe(attachment="A JSON file with the games' info")
    @is_owner()
    async def giveaway_add(
        self, interaction: discord.Interaction, attachment: discord.Attachment
    ):
        """Add game keys to the database for the giveaways.
        A file must be attached to the command when running it.
        This is an Owner Only command, as only the bot's owner can run it.
        """
        content = await attachment.read()
        data: list[dict[str, str]] = json.loads(content)

        LOGGER.debug(f"Adding {len(data)} games to the database.")
        await self._insert_games(data)

        await interaction.response.send_message(
            f"Thank you! I received {len(data)} keys and updated the database.",
            ephemeral=True,
        )

    @giveaway_add.error
    async def giveaway_add_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Error handler for the giveaway add command."""

        error = getattr(error, "original", error)

        if isinstance(error, NotOwner):
            await interaction.response.send_message(
                "You cannot add games to the giveaway, but you can enter them!"
            )
        else:
            interaction.extras["error_handled"] = False

    @giveaway.command(name="remaining")
    @app_commands.describe(page="Page number to display")
    @app_commands.checks.has_any_role(*HVC_STAFF_ROLES)
    async def giveaway_remaining(self, interaction: discord.Interaction, page: int = 1):
        """List the remaining games for the giveaway."""

        remaining_games = await self._get_remaining_games()
        n_remaining_games = len(remaining_games)
        games_counter = Counter([game.title for game in remaining_games])
        per_page = 15

        games_list = [
            f"`{amount:2d} x` {title}" for title, amount in games_counter.items()
        ]
        max_pages = len(games_list) // per_page + 1

        if page > max_pages:
            page = max_pages
        if page < 1:
            page = 1

        i = (page - 1) * per_page
        j = page * per_page
        today = date.today()
        dec_31 = date(today.year, 12, 31)
        days_until_dec_31 = dec_31 - today
        content = (
            "## To give out all the games by December 31st, we need to give "
            f"{n_remaining_games // days_until_dec_31.days} games per day!"
        )
        embed = discord.Embed(
            title=(
                f"{n_remaining_games} Remaining Games / "
                f"{len(games_counter)} Individual Titles"
            ),
            color=EMBED_COLOR,
            description="\n".join(games_list[i:j]),
        ).set_footer(
            text=f"Page {page}/{max_pages}",
        )

        await interaction.response.send_message(
            content=content, embed=embed, ephemeral=True
        )

    @giveaway.command(name="start")
    @app_commands.checks.has_any_role(*HVC_STAFF_ROLES)
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

        self._tasks[giveaway.giveaway_id] = asyncio.create_task(
            self.giveaway_task(
                interaction=interaction,
                giveaway=giveaway,
            )
        )

    async def _create_tables(self) -> None:
        """Create the necessary tables if they do not exist."""

        await self.bot.db.execute(read_sql_query(SQL / "create_game_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_giveaway_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_entry_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_view_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_component_table.sql"))

        await self.bot.db.commit()

    async def _create_giveaway(self, game_id: int) -> int | None:
        """Create the database entry for the giveaway."""

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

    async def _get_game(self, game_id: int) -> Game | None:
        """Return a Game by it's ID."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_game.sql"),
            dict(
                game_id=game_id,
            ),
        ) as c:
            row = await c.fetchone()

        if row is not None:
            return Game(**row)

    async def _get_giveaway(self, giveaway_id: int) -> Giveaway | None:
        """Return the a Giveaway by it's ID."""

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

        game = await self._get_game(giveaway_row["game_id"])
        if game is not None:
            return Giveaway(**dict(giveaway_row), game=game)
        else:
            return None

    async def _get_ongoing_giveaways(self) -> list[Giveaway]:
        """Return the list of giveaways that are not done yet."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_ongoing_giveaways.sql")
        ) as c:
            giveaway_rows = await c.fetchall()

        giveaway_rows = list(giveaway_rows)
        if len(giveaway_rows) == 0:
            # exit early if no ongoing giveaways
            return []

        giveaways: list[Giveaway] = []
        for row in giveaway_rows:
            game = await self._get_game(row["game_id"])

            if game is not None:
                giveaways.append(Giveaway(**dict(row), game=game))

        return giveaways

    async def _get_remaining_games(self) -> list[Game]:
        """Return the list of remaining games."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_remaining_games.sql")
        ) as c:
            rows = await c.fetchall()

        return [Game(**row) for row in rows]

    async def _get_random_game(self) -> Game | None:
        """Return a random game that is not given yet.
        If None is returned, it means there are no available games yet.
        """
        async with self.bot.db.execute(
            read_sql_query(SQL / "get_random_game.sql")
        ) as c:
            row = await c.fetchone()

        if row:
            game = Game(**row)
            await self._edit_game_given(game, True)
            return game
        else:
            return None

    async def _insert_games(self, list_of_games: list[dict[str, str]]) -> None:
        """Add a list of games and keys to the database."""

        await self.bot.db.executemany(
            read_sql_query(SQL / "insert_games.sql"),
            list_of_games,
        )

        await self.bot.db.commit()

    async def _edit_game_given(self, game: Game, given: bool) -> None:
        """Mark the game as given (or not, if no one wins it)."""

        await self.bot.db.execute(
            read_sql_query(SQL / "edit_game_given.sql"),
            {
                "game_id": game.game_id,
                "given": given,
            },
        )

        await self.bot.db.commit()

    async def _get_random_winner(self, giveaway: Giveaway) -> discord.User | None:
        """Return one random entry for the giveaway."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_random_winner.sql"),
            {"giveaway_id": giveaway.giveaway_id},
        ) as c:
            row = await c.fetchone()

        if row is None:
            return None

        winner = self.bot.get_user(row["user_id"]) or await self.bot.fetch_user(
            row["user_id"]
        )
        return winner

    async def _save_presistent_view(
        self, view: GiveawayView, message: discord.InteractionMessage
    ) -> None:
        """Save the information needed to reconstruct later to the database."""

        LOGGER.debug(f"Saving View data for message {message.id}.")
        assert message.guild is not None
        row = await self.bot.db.execute_insert(
            read_sql_query(SQL / "save_view.sql"),
            dict(
                guild_id=message.guild.id,
                message_id=message.id,
            ),
        )
        assert row is not None
        view_id: int = row[0]

        await self.bot.db.executemany(
            read_sql_query(SQL / "save_component.sql"),
            [
                dict(component_id=v, name=k, view_id=view_id)
                for k, v in view.components_id.items()
            ],
        )

        await self.bot.db.commit()

    async def _update_giveaway(
        self, giveaway: Giveaway, message: discord.InteractionMessage
    ) -> None:
        """Update the database entry with the info from the message
        containing the View.
        """
        await self.bot.db.execute(
            read_sql_query(SQL / "update_giveaway.sql"),
            {
                "giveaway_id": giveaway.giveaway_id,
                "channel_id": message.channel.id,
                "created_at": message.created_at,
                "message_id": message.id,
            },
        )

        await self.bot.db.commit()

    async def _end_giveaway(self, giveaway: Giveaway) -> None:
        """Mark the giveaway as done."""

        await self.bot.db.execute(
            read_sql_query(SQL / "end_giveaway.sql"),
            {
                "giveaway_id": giveaway.giveaway_id,
            },
        )
        LOGGER.debug(f"Giveaway for {giveaway.game.title} ended")
        await self.bot.db.commit()

    async def _get_view(self, giveaway: Giveaway) -> GiveawayView:
        """Get the View associated with the Giveaway."""

        async with self.bot.db.execute(
            read_sql_query(SQL / "get_view.sql"),
            dict(message_id=giveaway.message_id),
        ) as c:
            view_row = await c.fetchone()

        if view_row is None:
            raise ValueError(f"No view attached to message {giveaway.message_id}.")

        components_id = await self._get_components_id(view_row["view_id"])

        return GiveawayView(self.bot, giveaway, components_id=components_id)

    async def _get_components_id(self, view_id: int) -> dict[str, str]:
        """Get the dict of components ID for the View with view_id."""

        rows = await self.bot.db.execute_fetchall(
            read_sql_query(SQL / "get_components.sql"),
            dict(view_id=view_id),
        )
        components_id = {row["name"]: row["component_id"] for row in rows}
        return components_id
