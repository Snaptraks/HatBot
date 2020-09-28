import asyncio
from collections import Counter, defaultdict
import copy
from datetime import datetime, timedelta
import io

import discord
from discord.ext import commands, tasks
from discord.utils import escape_markdown
import matplotlib.pyplot as plt
import numpy as np

from ..utils.cogs import FunCog
from ..utils.datetime_modulo import datetime as datetime_modulo
from ..utils.formats import pretty_print_timedelta
from . import menus
from .objects import (
    Fish,
    Weather,
    get_fish_species_str,
    get_fish_size_color,
    FISH_SPECIES,
)


EMBED_COLOR = discord.Color.blurple()


def to_mpl_rbg(rgb_tuple):
    return [c / 255 for c in rgb_tuple]


class FishTopNoEntriesError(commands.CommandError):
    """Exception raised when the fish_top or fish_exptop commands are
    called but no best catches or experience are set yet.
    """
    pass


class NoFishError(commands.CommandError):
    """Exception raised when the member has no Fish in their inventory."""

    pass


class IsStunnedError(commands.CheckFailure):
    """Exception raised when the check `is_not_stunned` has failed."""

    pass


class OpenedInventoryError(commands.CheckFailure):
    """Exception raised when the check `no_opened_inventory` has failed."""

    pass


def is_not_stunned():
    """Decorator that checks if the member is stunned and cannot fish."""

    def predicate(ctx):
        stunned_until = ctx.cog.stunned_until[ctx.author.id]

        stunned = datetime.utcnow() < stunned_until
        if stunned:
            stunned_for = stunned_until - datetime.utcnow()
            raise IsStunnedError("You are still stunned for "
                                 f"{pretty_print_timedelta(stunned_for)}!")

        return True

    return commands.check(predicate)


def no_opened_inventory():
    """Decorator that checks if the member has an inventory opened."""

    def predicate(ctx):
        if ctx.author.id in ctx.cog.opened_inventory:
            raise OpenedInventoryError(
                "You need to close your inventory/trade menu first.")

        return True

    return commands.check(predicate)


class Fishing(FunCog):
    """Collection of fish-related commands."""

    def __init__(self, bot):
        super().__init__(bot)
        self.stunned_until = defaultdict(lambda: datetime.min)
        self.opened_inventory = set()

        # Make sure the necessary tables exist
        self._create_tables.start()

        # start tasks loops
        self.change_weather.start()
        self.interest_experience.start()

    def cog_unload(self):
        super().cog_unload()
        self.change_weather.cancel()
        self.interest_experience.cancel()

    def cog_check(self, ctx):
        """Check if is in a guild, and if in appropriate channel."""

        return ctx.guild is not None and super().cog_check(ctx)

    @tasks.loop(hours=24)
    async def change_weather(self):
        """Change the weather randomly every day."""

        self.weather = Weather.from_random()

    @tasks.loop(hours=12)
    async def interest_experience(self):
        """Give some experience to a random active member."""

        limit = datetime.utcnow() - timedelta(days=7)
        rows = await self._get_last_catches(limit)
        active_members = [row['caught_by'] for row in rows]

        if len(active_members) == 0:
            return

        winner_id = np.random.choice(active_members)
        winner = self.guild.get_member(winner_id)
        bonus_experience = np.random.triangular(3, 5, 15)
        content = (
            f":moneybag: {escape_markdown(winner.display_name)} got a little "
            f"bit of experience! ({bonus_experience:.3f} exp)"
        )

        msg = await self.channel_msg.send(content)

        await self._save_interest_experience(winner, msg, bonus_experience)

    @interest_experience.before_loop
    async def interest_experience_before(self):
        """Wait until time mod 12h and fetch the channel."""

        await self.bot.wait_until_ready()

        # bot-0
        # self.channel_msg = self.bot.get_channel(588171779957063680)
        # hatbot-land
        self.channel_msg = self.bot.get_channel(548606793656303625)
        # hatbot-meta
        # self.channel_msg = self.bot.get_channel(680866127546679307)
        if self.channel_msg is None:
            # will not work until dpy v1.4
            self.interest_experience.cancel()
            return

        self.guild = self.channel_msg.guild

        now = datetime_modulo.utcnow()
        _12h = timedelta(hours=12)
        next = now // _12h + _12h  # get next 00 or 12
        await discord.utils.sleep_until(next)  # wait until then

    @commands.group(aliases=["feesh", "<:feesh:427018890137174016>", "FEESH"],
                    invoke_without_command=True, cooldown_after_parsing=True)
    # 1 every 20 mins
    @commands.cooldown(1, 20 * 60, commands.BucketType.member)
    @is_not_stunned()
    @no_opened_inventory()
    async def fish(self, ctx):
        """Command group for the fishing commands.
        If invoked without subcommand, catches a random fish.
        """
        user_exp = await self._get_experience(ctx.author)

        catch = Fish.from_random(user_exp, self.weather.state, ctx.author.id)

        embed = catch.to_embed()

        keep = await menus.FishingConfirm(embed).prompt(ctx)

        state = 0 if keep else 1

        await self._save_fish(catch, state)

    @fish.error
    async def fish_error(self, ctx, error):
        """Error handling for the fish command.
        In case of CommandOnCooldown error, allow user to check how much
        time is left.
        """
        if isinstance(error, commands.CommandOnCooldown):
            await menus.CooldownMenu(
                ctx.message, error,
                "You have already tried to fish recently").start(ctx)

        elif isinstance(error, (IsStunnedError, OpenedInventoryError)):
            await ctx.send(error)

        else:
            raise error

    @fish.command(name="bomb", cooldown_after_parsing=True)
    @commands.cooldown(1, 30, commands.BucketType.member)
    @no_opened_inventory()
    async def fish_bomb(self, ctx, *, member: discord.Member):
        """Slap another member with up to 10 of your biggest fish.
        Slapping someone prevents them from fishing for a given amount
        of time. The fish used to slap the member are destroyed upon
        use, so think wisely.
        """
        slapper = ctx.author
        bomb_fish = await self._get_bomb_fish(slapper)

        if len(bomb_fish) == 0:
            raise NoFishError("You do not have any fish to slap with.")

        # slap with a list of Fish
        stunned_time = await self._execute_slap_bomb(member, bomb_fish)

        content = (
            f"{escape_markdown(member.display_name)} got **bombed** by "
            f"{escape_markdown(slapper.display_name)} with "
            f"**{len(bomb_fish)} fish**!\n"
            f"They are stunned for {pretty_print_timedelta(stunned_time)} "
            "and cannot go fishing!"
        )

        await ctx.send(content)

    @fish.command(name="card")
    async def fish_card(self, ctx, *, member: discord.Member = None):
        """Show some statistics about a member's fishing experience."""

        if member is None:
            member = ctx.author

        best_catch_dict = await self._get_best_catch(member)

        # check if the row is empty before creating the Fish
        if not all(_ is None for _ in dict(best_catch_dict).values()):
            best_catch = Fish.from_dict(best_catch_dict)
            date_str = best_catch.catch_time.strftime('%b %d %Y')
        else:
            best_catch = "No catches yet"
            date_str = None

        exp = await self._get_experience(member)

        embed = discord.Embed(
            title=f"Fishing Card of {escape_markdown(member.display_name)}",
            color=EMBED_COLOR,
        ).set_thumbnail(
            url=member.avatar_url,
        )

        embed.add_field(
            name="Best Catch",
            value=best_catch,
        ).add_field(
            name="Caught on",
            value=date_str,
        ).add_field(
            name="Experience",
            value=f"{exp:.3f} exp",
        )

        await ctx.send(embed=embed)

    @fish.command(name='exptop')
    async def fish_exptop(self, ctx):
        """Display the users who have the most experience."""

        sorted_experience = await self._get_exptop()

        if len(sorted_experience) == 0:
            raise FishTopNoEntriesError("No one with experience yet.")

        top_menu = menus.TopMenu(
            source=menus.TopExperienceSource(sorted_experience),
            clear_reactions_after=True,
        )

        await top_menu.start(ctx)

    @fish_exptop.error
    async def fish_exptop_error(self, ctx, error):
        """Error handling for the fish_exptop command."""

        if isinstance(error, FishTopNoEntriesError):
            await ctx.send(error)

        else:
            raise error

    @fish.command(name="inventory", aliases=["inv", "bag", "sell"])
    async def fish_inventory(self, ctx):
        """Look at your fishing inventory.
        Also allows you to sell the fish you previously saved.
        """
        inventory = await self._get_inventory(ctx.author)
        if len(inventory) == 0:
            raise NoFishError("No fish in inventory.")

        inventory_menu = menus.InventoryMenu(
            source=menus.InventorySource(inventory),
            clear_reactions_after=True,
        )
        to_sell = await inventory_menu.prompt(ctx)

        # not pretty but I need to strip some keys
        rows = []
        for i in to_sell:
            rows.append({'rowid': inventory[i]['rowid']})

        await self._sell_fish(rows)

    @fish_inventory.before_invoke
    async def fish_inventory_before(self, ctx):
        """Register the member as currently with an opened inventory."""

        self.opened_inventory.add(ctx.author.id)

    @fish_inventory.after_invoke
    async def fish_inventory_after(self, ctx):
        """Remove the member from being currently with an opened inventory."""

        self.opened_inventory.remove(ctx.author.id)

    @fish_inventory.error
    async def fish_inventory_error(self, ctx, error):
        """Error handler for the fish_inventory command."""

        if isinstance(error, NoFishError):
            embed = discord.Embed(
                title="Fish Inventory",
                description="No fish in inventory.",
                color=EMBED_COLOR,
            )
            delay = 3 * 60
            inv_msg = await ctx.send(embed=embed)
            await asyncio.sleep(delay)
            await ctx.channel.delete_messages([ctx.message, inv_msg])

        else:
            raise error

    @fish.group(name="journal", aliases=["log", "stats"],
                invoke_without_command=True)
    async def fish_journal(self, ctx, member: discord.Member = None):
        """Fishing log of the amount of fish caught and different stats."""

        if member is None:
            member = ctx.author

        embed, file = await self._build_journal_embed(member)
        message = await ctx.send(embed=embed, file=file)
        journal = menus.JournalMenu(message)

        await journal.start(ctx)

    @fish_journal.error
    async def fish_journal_error(self, ctx, error):
        """Error handling for the fish_journal command."""

        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

        else:
            raise error

    @fish_journal.command(name="global", aliases=["all"])
    async def fish_journal_global(self, ctx):
        """Global fishing log."""

        embed, file = await self._build_journal_embed()
        message = await ctx.send(embed=embed, file=file)
        journal = menus.JournalMenu(message)

        await journal.start(ctx)

    @fish.command(name="slap", cooldown_after_parsing=True)
    @commands.cooldown(1, 30, commands.BucketType.member)
    @no_opened_inventory()
    async def fish_slap(self, ctx, *, member: discord.Member):
        """Slap another member with one of your fish.
        Slapping someone prevents them from fishing for a given amount
        of time. The fish used to slap the member is destroyed upon
        use, so think wisely.
        """
        slapper = ctx.author
        slap_fish = await self._get_slap_fish(slapper)

        if len(slap_fish) == 0:
            raise NoFishError("You do not have any fish to slap with.")

        stunned_time = await self._execute_slap_bomb(member, slap_fish)

        content = (
            f"{escape_markdown(member.display_name)} got slapped by "
            f"{escape_markdown(slapper.display_name)} with a "
            f"{Fish.from_dict(slap_fish[0])}!\n"
            f"They are stunned for {pretty_print_timedelta(stunned_time)} "
            "and cannot go fishing!"
        )

        await ctx.send(content)

    @fish_bomb.error
    @fish_slap.error
    async def fish_slap_error(self, ctx, error):
        """Error handling for the fish_bomb and fish_slap command."""

        if isinstance(error, commands.CommandOnCooldown):
            await menus.CooldownMenu(
                ctx.message,
                error,
                f"You have already tried to {ctx.command.name} recently",
            ).start(ctx)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"You need to specify someone to {ctx.command.name}.")

        elif isinstance(error, (
                commands.BadArgument,
                NoFishError,
                OpenedInventoryError,
        )):
            await ctx.send(error)

        else:
            raise error

    @fish.command(name="top")
    async def fish_top(self, ctx):
        """Display the best catches server-wide."""

        sorted_best_catches = await self._get_top()

        if len(sorted_best_catches) == 0:
            raise FishTopNoEntriesError("No best catches yet.")

        top_menu = menus.TopMenu(
            source=menus.TopCatchesSource(sorted_best_catches),
            clear_reactions_after=True,
        )

        await top_menu.start(ctx)

    @fish_top.error
    async def fish_top_error(self, ctx, error):
        """Error handling for the fish_top command."""

        if isinstance(error, FishTopNoEntriesError):
            await ctx.send(error)

        else:
            raise error

    @fish.command(name="trade")
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def fish_trade(self, ctx, *, other_member: discord.Member):
        """Trade fish with another member."""

        if other_member == ctx.author:
            raise commands.BadArgument("You cannot trade with yourself!")

        author_inventory = await self._get_inventory(ctx.author)
        other_inventory = await self._get_inventory(other_member)
        other_str = escape_markdown(other_member.display_name)

        if len(author_inventory) == 0:
            raise NoFishError("You have no fish to trade!")

        elif len(other_inventory) == 0:
            raise NoFishError(f"{other_str} has no fish to trade!")

        if not other_member.mentioned_in(ctx.message):
            other_str = other_member.mention

        msg = copy.copy(ctx.message)
        msg.author = other_member
        other_ctx = await self.bot.get_context(msg, cls=type(ctx))

        confirm_msg = (
            f"Hey {other_str}, "
            f"{escape_markdown(ctx.author.display_name)} "
            "wants to trade with you! Do you accept?"
        )

        confirm = await menus.TradeConfirm(confirm_msg).prompt(other_ctx)

        if confirm:
            await ctx.send("Trade accepted.", delete_after=5 * 60)
            # start both menus and then transfer the fish
            author_menu = menus.TradeMenu(
                source=menus.TradeSource(
                    author_inventory,
                ),
                clear_reactions_after=True,
            )
            other_menu = menus.TradeMenu(
                source=menus.TradeSource(
                    other_inventory,
                ),
                clear_reactions_after=True,
            )

            tasks = [
                asyncio.create_task(author_menu.prompt(ctx)),
                asyncio.create_task(other_menu.prompt(other_ctx)),
            ]

            # done is a set of tasks, in the order they were COMPLETED
            # (not in the order of `tasks`!!!)
            # or not I can't seem to figure it out
            done, pending = await asyncio.wait(tasks)

            to_trade = [t.result() for t in done]
            to_trade = {t[0].id: t[1] for t in to_trade}
            if None in to_trade.values():
                await ctx.send("Trade cancelled.", delete_after=5 * 60)
                return

            # proceed to trade
            author_trade = author_inventory[to_trade[ctx.author.id]]
            other_trade = other_inventory[to_trade[other_member.id]]
            await self._trade_fish(author_trade, other_trade)

            await ctx.send("Trade successful!", delete_after=5 * 60)

        else:
            await ctx.send("Trade denied.", delete_after=5 * 60)

    @fish_trade.before_invoke
    async def fish_trade_before(self, ctx):
        """Register the two members as currently in trade."""

        other_member = ctx.kwargs['other_member']
        self.opened_inventory.add(ctx.author.id)
        self.opened_inventory.add(other_member.id)

    @fish_trade.after_invoke
    async def fish_trade_after(self, ctx):
        """Remove the two members from being currently in trade."""

        other_member = ctx.kwargs['other_member']
        self.opened_inventory.remove(ctx.author.id)
        self.opened_inventory.remove(other_member.id)

    @fish_trade.error
    async def fish_trade_error(self, ctx, error):
        """Error handling for the fish_trade command."""

        if isinstance(error, commands.MaxConcurrencyReached):
            name = error.per.name
            suffix = f"for this {name}" if name != "default" else "globally"
            await ctx.send(f"This command is already running {suffix}.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You need to specify a member to trade with.")

        elif isinstance(error, (commands.BadArgument, NoFishError)):
            await ctx.send(error)

        else:
            raise error

    @commands.group(invoke_without_command=True)
    async def weather(self, ctx):
        """Check today's weather."""

        await ctx.send(f"The weather currently is {self.weather}")

    @weather.command(name='set')
    @commands.is_owner()
    async def weather_set(self, ctx, state: int):
        """Set the weather to the given state (positive integer)."""

        self.weather = Weather(state)
        await ctx.send(f"Weather set to {self.weather}")

    def _build_journal_from_rows(self, rows):
        """Convert a list of Rows to a defaultdict of Counters."""

        journal = defaultdict(Counter)
        for row in rows:
            journal[row['size']][row['species']] += row['number_catch']

        return journal

    async def _build_journal_embed(self, member=None):
        """Create the Embed for the fish_journal command and subcommand."""

        if member is not None:
            journal = await self._get_journal(member)
            total_weight = await self._get_journal_total_weight(member)
            embed_title = (
                "Fishing Journal of "
                f"{escape_markdown(member.display_name)}"
            )
            thumbnail = member.avatar_url

        else:
            journal = await self._get_journal_global()
            total_weight = await self._get_journal_global_total_weight()
            embed_title = "Global Fishing Journal"
            thumbnail = ""

        if total_weight is None:
            total_weight = 0

        total_caught = sum([sum(c.values()) for c in journal.values()])

        total_species = {key: len(value['species'])
                         for key, value in FISH_SPECIES.items()}

        species_caught = {key: len(value)
                          for key, value in journal.items()}
        species_caught = {size: len(journal.get(size, []))
                          for size in FISH_SPECIES}

        species_caught_str = "\n".join(
            f"{size.title()}: **{species_caught[size]}/{total_species[size]}**"
            for size in FISH_SPECIES.keys()
        )

        most_caught = {key: value.most_common(1)[0]
                       for key, value in journal.items()
                       if len(value) > 0}

        most_caught_str = "\n".join((
            f"{size.title()} "
            f"**{get_fish_species_str(size, most_caught[size][0])} "
            f"({most_caught[size][1]})**")
            for size in most_caught.keys()
        )

        totals_str = (
            "Species Caught: "
            f"**{sum(species_caught.values())}"
            f"/{sum(total_species.values())}**\n"
            f"Catches: **{total_caught}**\n"
            f"Weight Fished: **{total_weight:.0f} kg**"
        )

        graph = await self.bot.loop.run_in_executor(
            None, self._plot_journal_pie_chart, journal)
        file = discord.File(graph, filename="pie.png")

        embed = discord.Embed(
            title=embed_title,
            color=EMBED_COLOR,
        ).set_thumbnail(
            url=thumbnail,
        ).add_field(
            name="Species Caught",
            value=species_caught_str if species_caught_str else None,
        ).add_field(
            name="Most Caught",
            value=most_caught_str if most_caught_str else None,
        ).add_field(
            name="Totals",
            value=totals_str,
        ).set_image(
            url=f"attachment://{file.filename}",
        )

        return embed, file

    def _plot_journal_pie_chart(self, journal):
        """Plot the pie charts of the sizes of caught fish."""

        SIZES = [
            ['tiny', 'small', 'average'],
            ['large', 'giant', 'epic', 'legendary'],
        ]

        fig, ax = plt.subplots(ncols=2, figsize=(7, 3.5))
        title = ["Smaller Fish", "Bigger Fish"]
        startangle = [180, 0]

        for i in range(2):
            x = []
            labels = []
            colors = []
            for s in SIZES[i]:
                x.append(sum(journal[s].values()))
                if x[-1] > 0:
                    labels.append(f"{s.title()} ({x[-1]})")
                else:
                    labels.append("")
                colors.append(
                    to_mpl_rbg(
                        get_fish_size_color(s).to_rgb()
                    )
                )

            if i == 0:
                x.append(sum([sum(journal[s].values()) for s in SIZES[1]]))
                if x[-1] > 0:
                    labels.append("Bigger Fish")
                else:
                    labels.append("")
                colors.append([1, 0, 0])  # red

            ax[i].pie(x, labels=labels, colors=colors,
                      startangle=startangle[i],
                      wedgeprops={'width': 0.5})
            ax[i].set_title(title[i])

        plt.tight_layout()
        fig.suptitle("Fish Size Chart")
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png")
        plt.close(fig=fig)
        buffer.seek(0)

        return buffer

    @tasks.loop(count=1)
    async def _create_tables(self):
        """Create the necessary DB tables if they do not exist."""

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS fishing_fish(
                catch_time TIMESTAMP NOT NULL,
                caught_by  INTEGER   NOT NULL,
                owner_id   INTEGER   NOT NULL,
                size       TEXT      NOT NULL,
                smell      INTEGER   NOT NULL,
                species    INTEGER   NOT NULL,
                state      INTEGER   NOT NULL,
                weight     REAL      NOT NULL
            )
            """
        )

        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS fishing_interest(
                amount       REAL      NOT NULL,
                message_time TIMESTAMP NOT NULL,
                jump_url     TEXT      NOT NULL,
                user_id      INTEGER   NOT NULL
            )
            """
        )

        await self.bot.db.commit()

    async def _execute_slap_bomb(self, member, fish_list):
        """Helper function to set the stunned time, and set the fish as
        used for a slap.
        """
        slap_time = timedelta(0)
        for fish in fish_list:
            slap_time += timedelta(hours=np.sqrt(fish['weight']))

        await self.bot.db.executemany(
            """
                UPDATE fishing_fish
                   SET state = 2
                 WHERE rowid = :rowid
                """,
            [{'rowid': fish['rowid']} for fish in fish_list]
        )
        await self.bot.db.commit()

        beginning = max(datetime.utcnow(), self.stunned_until[member.id])
        self.stunned_until[member.id] = until = beginning + slap_time
        stunned_time = until - datetime.utcnow()

        return stunned_time

    async def _get_best_catch(self, member):
        """Get the best catch of a member."""

        async with self.bot.db.execute(
                """
                SELECT size, species, catch_time, MAX(weight) AS weight
                  FROM fishing_fish
                 WHERE caught_by = :caught_by
                """,
                {'caught_by': member.id}
        ) as c:
            row = await c.fetchone()

        return row

    async def _get_bomb_fish(self, member):
        """Get the fish to be used in a bomb (not slap)."""

        async with self.bot.db.execute(
                """
                SELECT rowid, weight
                  FROM fishing_fish
                 WHERE owner_id = :owner_id
                   AND state = 0
                 ORDER BY weight DESC
                 LIMIT 10
                """,
                {'owner_id': member.id}
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_experience(self, member):
        """Return the total experience of a member."""

        async with self.bot.db.execute(
                """
                SELECT SUM(amount) AS exp
                  FROM (SELECT SUM(weight) AS amount
                          FROM fishing_fish
                         WHERE owner_id = :member_id
                           AND state = 1

                         UNION

                        SELECT SUM(amount) AS amount
                          FROM fishing_interest
                         WHERE user_id = :member_id)
                """,
                {'member_id': member.id}
        ) as c:
            row = await c.fetchone()

        exp = row['exp']
        return exp if exp is not None else 0

    async def _get_exptop(self):
        """Return the list of users sorted by total experience."""

        async with self.bot.db.execute(
                """
                SELECT id, SUM(amount) AS exp
                  FROM (SELECT owner_id AS id, SUM(weight) AS amount
                          FROM fishing_fish
                         WHERE state = 1
                         GROUP BY id

                         UNION

                        SELECT user_id AS id, SUM(amount) AS amount
                          FROM fishing_interest
                         GROUP BY id)
                 GROUP BY id
                 ORDER BY exp DESC
                """
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_inventory(self, member):
        """Return the list of fish in a member's inventory."""

        async with self.bot.db.execute(
                """
                SELECT rowid, *
                  FROM fishing_fish
                 WHERE owner_id = :owner_id
                   AND state = 0
                 ORDER BY weight ASC
                """,
                {'owner_id': member.id}
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_journal(self, member):
        """Return the number of times each species was caught,
        sorted by weight.
        """
        async with self.bot.db.execute(
                """
                SELECT size, species, COUNT(species) AS number_catch
                  FROM fishing_fish
                 WHERE caught_by = :caught_by
                 GROUP BY size, species
                 ORDER BY weight ASC
                """,
                {'caught_by': member.id}
        ) as c:
            rows = await c.fetchall()

        journal = self._build_journal_from_rows(rows)

        return journal

    async def _get_journal_total_caught(self, member):
        """Return the amount of fish caught for the given member."""

        async with self.bot.db.execute(
                """
                SELECT COUNT(*) as total_caught
                  FROM fishing_fish
                 WHERE caught_by = :caught_by
                """,
                {'caught_by': member.id}
        ) as c:
            row = await c.fetchone()

        return row['total_caught']

    async def _get_journal_total_weight(self, member):
        """Get the total weight of all the fish caught."""

        async with self.bot.db.execute(
                """
                SELECT SUM(weight) AS total_weight
                  FROM fishing_fish
                 WHERE caught_by = :caught_by
                """,
                {'caught_by': member.id}
        ) as c:
            row = await c.fetchone()

        return row['total_weight']

    async def _get_journal_global(self):
        """Get the number of time each species was caught globally."""

        async with self.bot.db.execute(
                """
                SELECT size, species, COUNT(species) AS number_catch
                  FROM fishing_fish
                 GROUP BY size, species
                 ORDER BY weight ASC
                """
        ) as c:
            rows = await c.fetchall()

        journal = self._build_journal_from_rows(rows)

        return journal

    async def _get_journal_global_total_weight(self):
        """Get the total weight of all the fish caught."""

        async with self.bot.db.execute(
                """
                SELECT SUM(weight) AS total_weight
                  FROM fishing_fish
                """
        ) as c:
            row = await c.fetchone()

        return row['total_weight']

    async def _get_last_catches(self, limit):
        """Get the last fish caught by every member."""

        async with self.bot.db.execute(
                """
                SELECT caught_by, MAX(catch_time) as catch_time
                  FROM fishing_fish
                 WHERE catch_time > :limit
                 GROUP BY caught_by
                """,
                {'limit': limit.isoformat()}
        ) as c:

            rows = await c.fetchall()

        return rows

    async def _get_slap_fish(self, member):
        """Get the fish to be used in a slap (not bomb)."""

        async with self.bot.db.execute(
                """
                SELECT rowid, *
                  FROM fishing_fish
                 WHERE owner_id = :owner_id
                   AND state = 0
                 ORDER BY RANDOM()
                 LIMIT 1
                """,
                {'owner_id': member.id}
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_top(self):
        """Return the list of best catches for each member,
        sorted by weight.
        """
        async with self.bot.db.execute(
                """
                SELECT size, species, MAX(weight) AS weight,
                       caught_by, catch_time
                  FROM fishing_fish
                 GROUP BY caught_by
                 ORDER BY weight DESC
                """
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _save_interest_experience(self, member, message, amount):
        """Add the amount of bi-daily interest to the given member."""

        await self.bot.db.execute(
            """
            INSERT INTO fishing_interest
            VALUES (:amount,
                    :interest_time,
                    :jump_url,
                    :user_id)
            """,
            {
                'amount': amount,
                'interest_time': message.created_at,
                'jump_url': message.jump_url,
                'user_id': member.id,
            }
        )
        await self.bot.db.commit()

    async def _save_fish(self, fish, state):
        """Save the fish to the database.
        state = 0: in inventory
        state = 1: sold
        """
        fish_dict = fish.to_dict()
        fish_dict['state'] = state
        await self.bot.db.execute(
            """
            INSERT INTO fishing_fish
            VALUES (:catch_time,
                    :caught_by,
                    :owner_id,
                    :size,
                    :smell,
                    :species,
                    :state,
                    :weight)
            """,
            fish_dict
        )
        await self.bot.db.commit()

    async def _sell_fish(self, rows):
        """Set the fish as sold."""

        await self.bot.db.executemany(
            """
            UPDATE fishing_fish
               SET state = 1
             WHERE rowid = :rowid
            """,
            rows
        )
        await self.bot.db.commit()

    async def _trade_fish(self, author_fish, other_fish):
        """Trade the fish from the author of the command to the other
        member (the one that was asked to trade). We need to change the
        owner_id of both, NOT the caught_by attribute.
        """
        new_ids = [
            {'rowid': author_fish['rowid'],
             'new_owner_id': other_fish['owner_id']},
            {'rowid': other_fish['rowid'],
             'new_owner_id': author_fish['owner_id']},
        ]
        await self.bot.db.executemany(
            """
            UPDATE fishing_fish
               SET owner_id = :new_owner_id
             WHERE rowid = :rowid
            """,
            new_ids
        )
        await self.bot.db.commit()
