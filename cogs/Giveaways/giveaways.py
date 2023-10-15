import asyncio
from collections import Counter
import json
import logging

import discord
from discord import app_commands
from discord.ext import commands

from snapcogs import Bot
from snapcogs.utils.db import read_sql_query

from .base import EMBED_COLOR, GIVEAWAY_TIME, SQL, Game, Giveaway
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
                self.old_giveaway_task(
                    ctx,
                    giveaway_data=giveaway,
                    message=message,
                    timeout=None,
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
        game_title_link = f"[{giveaway.game.title}]({giveaway.game.url})"
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
            message = await interaction.original_response()
            await self._save_presistent_view(view, message)
            await self._update_giveaway(giveaway, message)

        else:
            view = await self._get_view(giveaway)
            self.bot.add_view(view, message_id=giveaway.message_id)
            channel = self.bot.get_partial_messageable(giveaway.channel_id)
            message = channel.get_partial_message(giveaway.message_id)

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
                    f"**{giveaway.game.title}**!\n"
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

        await message.edit(embed=embed, view=None)
        await self._end_giveaway(giveaway)

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

        self._tasks[giveaway.giveaway_id] = asyncio.create_task(
            self.giveaway_task(
                interaction=interaction,
                giveaway=giveaway,
            )
        )

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
        await self.bot.db.execute(read_sql_query(SQL / "create_view_table.sql"))
        await self.bot.db.execute(read_sql_query(SQL / "create_component_table.sql"))

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
            async with self.bot.db.execute(
                read_sql_query(SQL / "get_game.sql"),
                dict(game_id=row["game_id"]),
            ) as c:
                game_row = await c.fetchone()

            if game_row is not None:
                game = Game(**game_row)
                giveaways.append(Giveaway(**dict(row), game=game))

        return giveaways

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
            LOGGER.warn("Marking game as given disabled!")
            # await self._edit_game_given(row["game_id"], True)  # disable for testing
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

    async def _edit_game_given(self, game: Game, given: bool):
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
        LOGGER.debug("Saving View data.")
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
        """Update the DB entry with the info from the message
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

    async def _end_giveaway(self, giveaway: Giveaway):
        """Mark the giveaway as done."""

        await self.bot.db.execute(
            read_sql_query(SQL / "end_giveaway.sql"),
            {
                "giveaway_id": giveaway.giveaway_id,
            },
        )

        await self.bot.db.commit()

    async def _get_view(self, giveaway: Giveaway) -> GiveawayView:
        async with self.bot.db.execute(
            read_sql_query(SQL / "get_view.sql"),
            dict(message_id=giveaway.message_id),
        ) as c:
            view_row = await c.fetchone()

        if view_row is None:
            raise ValueError(f"No view attached to message {giveaway.message_id}.")

        components_id = {
            component["name"]: component["component_id"]
            for component in await self._get_components(view_row["view_id"])
        }

        return GiveawayView(self.bot, giveaway, components_id=components_id)

    async def _get_components(self, view_id: int) -> list[dict[str, str]]:
        rows = await self.bot.db.execute_fetchall(
            read_sql_query(SQL / "get_components.sql"),
            dict(view_id=view_id),
        )
        return [dict(row) for row in rows]
