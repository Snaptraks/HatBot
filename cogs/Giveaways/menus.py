import discord
from discord.ext import menus


GIFT_EMOJI = '\U0001F381'
EMBED_COLOR = 0xB3000C


class GiveawayMenu(menus.Menu):
    """Menu for the Giveaway registration."""

    def __init__(self, *args, **kwargs):
        self.giveaway_data = kwargs.pop('giveaway_data')
        super().__init__(*args, **kwargs)

        giveaway_end = self.giveaway_data['trigger_at']
        self.game_title_and_link = (f"[**{self.giveaway_data['title']}**]"
                                    f"({self.giveaway_data['url']})")
        self.embed = discord.Embed(
            title="Giveaway!",
            color=EMBED_COLOR,
            description=(
                "We are giving away "
                f"{self.game_title_and_link}\n"
                f"React with {GIFT_EMOJI} to enter!"
            )
        ).set_footer(
            text=f"This giveaway ends at {giveaway_end.strftime('%c UTC')}",
        )

    async def send_initial_message(self, ctx, channel):
        """Send the Giveaway Embed message."""

        self.message = await channel.send(embed=self.embed)
        # update DB with message details
        await self._update_giveaway()

        return self.message

    def reaction_check(self, payload):
        """Override the function to allow for everyone to react."""

        if payload.message_id != self.message.id:
            return False

        if payload.user_id == self.bot.user.id:
            return False

        return payload.emoji in self.buttons

    async def finalize(self, timed_out):
        """Mark the giveaway as finished and display the winner."""

        if self.winner is None:
            await self.message.delete()

        else:
            self.embed.description = (
                f"{self.winner.display_name} ({self.winner.mention}) "
                f"won the giveaway for {self.game_title_and_link}."
                " Congrats to them!"
            )
            await self.message.edit(embed=self.embed)

        await self._end_giveaway()

    async def stop(self):
        entry = await self._get_random_winner()
        if entry is None:
            self.winner = None

        else:
            self.winner = (
                self.ctx.guild.get_member(entry['user_id'])
                or await self.ctx.guild.fetch_member(entry['user_id'])
            )

        super().stop()
        return self.winner

    @menus.button(GIFT_EMOJI)
    async def on_register(self, payload):
        """Add the user entry to the giveaway."""

        await self._add_entry(payload.user_id)

    async def _add_entry(self, user_id):
        """Add the entry to the DB."""

        await self.bot.db.execute(
            """
            INSERT OR IGNORE INTO giveaways_entry
            VALUES (:giveaway_id,
                    :user_id)
            """,
            {
                'giveaway_id': self.giveaway_data['giveaway_id'],
                'user_id': user_id,
            }
        )

        await self.bot.db.commit()

    async def _get_entries(self):
        """Return the list of entries for the giveaway."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM giveaways_entry
                 WHERE giveaway_id = :giveaway_id
                """,
                {
                    'giveaway_id': self.giveaway_data['giveaway_id'],
                }
        ) as c:
            rows = await c.fetchall()

        return rows

    async def _get_random_winner(self):
        """Return one random entry for the giveaway."""

        async with self.bot.db.execute(
                """
                SELECT *
                  FROM giveaways_entry
                 WHERE giveaway_id = :giveaway_id
                 ORDER BY RANDOM()
                 LIMIT 1
                """,
                {
                    'giveaway_id': self.giveaway_data['giveaway_id'],
                }
        ) as c:
            row = await c.fetchone()

        return row

    async def _update_giveaway(self):
        """Update the DB entry with the info from the message
        containing the Menu.
        """
        await self.bot.db.execute(
            """
            UPDATE giveaways_giveaway
               SET channel_id = :channel_id,
                   created_at = :created_at,
                   message_id = :message_id
             WHERE giveaway_id = :giveaway_id
            """,
            {
                'giveaway_id': self.giveaway_data['giveaway_id'],
                'channel_id': self.message.channel.id,
                'created_at': self.message.created_at,
                'message_id': self.message.id
            }
        )

        await self.bot.db.commit()

    async def _end_giveaway(self):
        """Mark the giveaway as done."""

        await self.bot.db.execute(
            """
            UPDATE giveaways_giveaway
               SET is_done = 1
             WHERE giveaway_id = :giveaway_id
            """,
            {
                'giveaway_id': self.giveaway_data['giveaway_id'],
            }
        )

        await self.bot.db.commit()


class GameListMenu(menus.MenuPages):
    """Menu to list the remaining games."""


class GameListSource(menus.ListPageSource):
    """PageSource for the GameListMenu."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.count = sum([e[1] for e in self.entries])

    async def format_page(self, menu, page):
        """Format the remaining games nicely."""

        content = "\n".join(
            [f"`{p[1]} x` {p[0]}" for p in page]
        )

        embed = discord.Embed(
            title=f"{self.count} Remaining Games",
            color=EMBED_COLOR,
            description=content,
        ).set_footer(
            text=f"Page {menu.current_page + 1}/{self.get_max_pages()}",
        )

        return embed
