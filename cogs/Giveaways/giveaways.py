import asyncio
import json
import logging
import random
from collections import Counter
from datetime import date

import discord
from discord import app_commands
from discord.ext import commands
from snapcogs import Bot
from snapcogs.utils.views import Confirm
from sqlalchemy import asc, func, not_, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import joinedload

from ..utils.checks import NotOwner, is_owner
from .base import (
    EMBED_COLOR,
    GIVEAWAY_TIME,
    HVC_MC_SERVER_CHATTER,
    HVC_STAFF_ROLES,
)
from .models import Component, Entry, Game, Giveaway, View
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
        self.persistent_views_loaded: bool = False
        self._tasks: dict[int, asyncio.Task] = {}

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
            try:
                await self.load_ongoing_giveaways()
                self.persistent_views_loaded = True
            except OperationalError:
                LOGGER.info(
                    f"Database tables for cog {self.__class__.__name__} "
                    "do not exist yet."
                )

    async def load_ongoing_giveaways(self) -> None:
        for giveaway in await self._get_ongoing_giveaways():
            LOGGER.debug(f"Loading view for message {giveaway.message_id}")

            self._tasks[giveaway.id] = asyncio.create_task(
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

            giveaway.channel_id = original_message.channel.id
            giveaway.created_at = original_message.created_at
            giveaway.message_id = original_message.id
            giveaway = await self._save_giveaway(giveaway)

        else:
            view = await self._get_view(giveaway)
            self.bot.add_view(view, message_id=giveaway.message_id)

        LOGGER.debug(f"Sleeping for giveaway {giveaway.id}")
        await discord.utils.sleep_until(giveaway.trigger_at)
        view.stop()

        winner = await self._get_random_winner(giveaway)

        if winner is None:
            LOGGER.info(
                f"No winner for {giveaway.id}, marking game as still available."
            )
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
            try:
                await mc_server_chatter.send(
                    f"{winner.display_name} has won {giveaway.game.title} "
                    "on the Discord server! You should join for a chance to win too ;)"
                )
            except Exception:
                LOGGER.info("Could not send to mc-server-chatter")

        await self._end_giveaway(giveaway)

        # the following attributes should never be None
        channel = self.bot.get_partial_messageable(giveaway.channel_id)  # type: ignore
        message = channel.get_partial_message(giveaway.message_id)  # type: ignore

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
        games_data: list[dict[str, str]] = json.loads(content)

        LOGGER.debug(f"Adding {len(games_data)} games to the database.")
        await self._insert_games(games_data)

        await interaction.response.send_message(
            f"Thank you! I received {len(games_data)} keys and updated the database.",
            ephemeral=True,
        )

    @giveaway.command(name="readd")
    @app_commands.describe(key="Steam Key of the game to add back in the database.")
    @is_owner()
    async def giveaway_readd(self, interaction: discord.Interaction, key: str):
        """Re-add a game key in the database for the giveaways.
        The key must be a string as it is entered in the database.
        It is useful when someone did not want the key, already had the game, and
        wants to give it back.
        This is an Owner Only command, as only the bot's owner can run it.
        """

        view = Confirm()
        await interaction.response.send_message(
            "Really add back the key?", view=view, ephemeral=True
        )
        await view.wait()

        if view.value and view.interaction is not None:
            await self._re_add_game_key(key)
            await view.interaction.response.send_message(
                "Adding back the key to the giveaway!", ephemeral=True
            )

    @giveaway_add.error
    @giveaway_readd.error
    async def giveaway_add_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Error handler for the giveaway add command."""

        error = getattr(error, "original", error)

        if isinstance(error, NotOwner):
            await interaction.response.send_message(
                "You cannot add games to the giveaway, but you can enter them!",
                ephemeral=True,
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
    @app_commands.checks.cooldown(10, 10 * 60, key=None)  # 10 calls per 10 mionutes
    @app_commands.checks.has_any_role(*HVC_STAFF_ROLES)
    async def giveaway_start(self, interaction: discord.Interaction):
        """Start one Giveaway event."""

        game = await self._get_random_game()
        if game is None:
            await interaction.response.send_message(
                "No more games! Sorry!", ephemeral=True
            )
            return

        LOGGER.debug(f"Giving game {game.title} ({game.id=})")
        giveaway = Giveaway(
            trigger_at=discord.utils.utcnow() + GIVEAWAY_TIME,
            game=game,
        )
        giveaway = await self._save_giveaway(giveaway)

        self._tasks[giveaway.id] = asyncio.create_task(
            self.giveaway_task(
                interaction=interaction,
                giveaway=giveaway,
            )
        )

    async def _get_ongoing_giveaways(self) -> list[Giveaway]:
        """Return the list of Giveaways that are not done yet."""

        async with self.bot.db.session() as session:
            giveaways = await session.scalars(
                select(Giveaway)
                .where(not_(Giveaway.is_done))
                .options(
                    joinedload(Giveaway.game),
                )
            )

        return list(giveaways)

    async def _save_giveaway(self, giveaway: Giveaway) -> Giveaway:
        """Save the Giveaway information to the database."""
        async with self.bot.db.session() as session:
            async with session.begin():
                session.add(giveaway)

        LOGGER.debug(f"Saved Giveaway {giveaway.id}.")

        return giveaway

    async def _end_giveaway(self, giveaway: Giveaway) -> None:
        """Mark the Giveaway as done."""

        async with self.bot.db.session() as session:
            async with session.begin():
                giveaway.is_done = True
                session.add(giveaway)

        LOGGER.debug(f"Giveaway {giveaway.id} for {giveaway.game.title} ended.")

    async def _get_random_game(self) -> Game | None:
        """Return a random game that is not given yet.
        If None is returned, it means there are no available games yet.
        """
        async with self.bot.db.session() as session:
            game = await session.scalar(
                select(Game)
                .where(
                    not_(Game.given),
                )
                .order_by(
                    func.random(),
                )
                .limit(1)
            )

        LOGGER.debug(f"Randomly selected Game {game}")

        if game is not None:
            await self._edit_game_given(game, given=True)

        return game

    async def _edit_game_given(self, game: Game, given: bool) -> None:
        """Mark the game as given (or not, if no one wins it)."""

        async with self.bot.db.session() as session:
            async with session.begin():
                game.given = given
                session.add(game)

        LOGGER.debug(f"Edited Game {game.id} ({game.title}) as {given=}.")

    async def _get_remaining_games(self) -> list[Game]:
        """Return the list of remaining games."""

        async with self.bot.db.session() as session:
            games = await session.scalars(
                select(Game)
                .where(
                    not_(Game.given),
                )
                .order_by(
                    asc(Game.title),
                )
            )

        return list(games)

    async def _insert_games(self, games_data: list[dict[str, str]]) -> None:
        """Add a list of games and keys to the database."""

        # this is the least hackish way I could find that actually works.
        # this is a limitation qith SQLAlchemy where the "ON CONFLICT IGNORE"
        # is not well implemented in the ORM
        async with self.bot.db.session() as session:
            async with session.begin():
                for game_data in games_data:
                    await session.execute(
                        insert(Game)
                        .values(
                            key=game_data["key"],
                            title=game_data["title"],
                            url=game_data["url"],
                        )
                        .on_conflict_do_nothing(index_elements=["key"])
                    )

    async def _re_add_game_key(self, key: str) -> None:
        """Mark the game key as not given."""

        async with self.bot.db.session() as session:
            async with session.begin():
                await session.execute(
                    update(Game)
                    .where(
                        Game.key == key,
                    )
                    .values(
                        given=False,
                    )
                )
        LOGGER.debug(f"Marked the key {key} as given=False.")

    async def _get_random_winner(self, giveaway: Giveaway) -> discord.User | None:
        """Return one random entry for the giveaway."""

        async with self.bot.db.session() as session:
            entries = await session.scalars(
                select(Entry)
                .where(
                    Entry.giveaway_id == giveaway.id,
                )
                .order_by(
                    func.random(),
                )
            )

        entries = list(entries)

        if len(entries) == 0:
            return None

        LOGGER.debug(f"Selecting a random winner from {len(entries)} entries.")
        winning_entry = random.choice(entries)

        winner = self.bot.get_user(winning_entry.user_id) or await self.bot.fetch_user(
            winning_entry.user_id
        )

        return winner

    async def _save_presistent_view(
        self, view: GiveawayView, message: discord.InteractionMessage
    ) -> None:
        """Save the information needed to reconstruct later to the database."""

        LOGGER.debug(f"Saving View data for message {message.id}.")
        assert message.guild is not None

        async with self.bot.db.session() as session:
            async with session.begin():
                model_view = View(
                    guild_id=message.guild.id,
                    message_id=message.id,
                    components=[
                        Component(name=name, component_id=component_id)
                        for name, component_id in view.components_id.items()
                    ],
                )
                session.add(model_view)

    async def _get_view(self, giveaway: Giveaway) -> GiveawayView:
        """Get the View associated with the Giveaway."""

        async with self.bot.db.session() as session:
            view_model = await session.scalar(
                select(View)
                .where(
                    View.message_id == giveaway.message_id,
                )
                .options(
                    joinedload(View.components),
                )
            )

        assert view_model is not None

        return GiveawayView(
            self.bot,
            giveaway,
            components_id={c.name: c.component_id for c in view_model.components},
        )
