import asyncio
import csv
from datetime import datetime, timedelta, timezone
import random

import numpy as np
import discord
from discord.ext import commands, tasks

from ..utils.cogs import FunCog
from ..utils.checks import has_role_or_above


GIFT_EMOJI = '\U0001F381'
GIVEAWAY_TIME = timedelta(hours=24)
# GIVEAWAY_TIME = timedelta(seconds=15)


class Christmas(FunCog):
    def __init__(self, bot):
        super().__init__(bot)

        self.steam_keys = []
        with open('cogs/Christmas/keys.csv', 'r') as f:
            csv_reader = csv.reader(f, delimiter=',')
            for i, row in enumerate(csv_reader):
                if i != 0:
                    self.steam_keys.append(tuple(row))

        try:
            with open('cogs/Christmas/keys_given.txt', 'r') as f:
                self.steam_keys_given = [key.strip() for key in f.readlines()]
                self.steam_keys_given = set(self.steam_keys_given)

        except FileNotFoundError:
            self.steam_keys_given = set()


    def cog_unload(self):
        super().cog_unload()
        with open('cogs/Christmas/keys_given.txt', 'w') as f:
            f.write('\n'.join(self.steam_keys_given))

    @commands.is_owner()
    @commands.group(aliases=['ga'])
    async def giveaway(self, ctx):
        """Commands to control the giveaways."""

        pass

    @commands.is_owner()
    @giveaway.command(name='start')
    async def giveaway_start(self, ctx):
        """Start the giveaways to create one at regular interval."""

        try:
            self.giveaway_master_task.ctx = ctx
            self.giveaway_master_task.start(ctx)
        except RuntimeError as e:
            await ctx.message.delete()
            await ctx.send('Task alread running.', delete_after=15)

    @commands.is_owner()
    @giveaway.command(name='stop')
    async def giveaway_stop(self, ctx):
        """Stop the giveaways."""

        self.giveaway_master_task.cancel()

    @has_role_or_above('Mod')
    @giveaway.command(name='trigger')
    async def giveaway_trigger(self, ctx):
        """Trigger one giveaway event."""

        self.bot.loop.create_task(self.giveaway_task(ctx))

    # @commands.is_owner()
    @giveaway.command(name='remaining')
    async def giveaway_remaining(self, ctx):
        """List of the remaining available games for the giveaway."""

        remaining = []
        for game_info in self.steam_keys:
            if game_info[1] not in self.steam_keys_given:
                remaining.append(game_info[0])

        remaining_str = '\n'.join(remaining)

        await ctx.send(f'```\n{remaining_str}\n```')

    @tasks.loop(hours=24)
    async def giveaway_master_task(self, ctx):
        """Main task for giveaways.
        Start a giveaway task at regular interval.
        """
        self.bot.loop.create_task(self.giveaway_task(ctx))

    async def giveaway_task(self, ctx):
        """Start one giveaway task.
        Will send the message in the channel where `!giveaway start` or
        `!giveaway trigger` was invoked.
        """
        if len(self.steam_keys) == len(self.steam_keys_given):
            await ctx.send('No more keys!')
            # stop the master task just in case
            self.giveaway_master_task.cancel()
            return

        game_info = random.choice(self.steam_keys)
        while game_info[1] in self.steam_keys_given:
            game_info = random.choice(self.steam_keys)
        self.steam_keys_given.add(game_info[1])

        embed = discord.Embed(
            title='Holidays Giveaway!',
            color=0xB3000C,
            description=(
                f'We are giving away [**{game_info[0]}**]({game_info[2]})!\n'
                f'React with {GIFT_EMOJI} to enter!'
                )
            )
        giveaway_end = datetime.now(timezone.utc) + GIVEAWAY_TIME
        embed.set_footer(
            text=f"This giveaway ends at {giveaway_end.strftime('%c %Z')}",
            )

        giveaway_message = await ctx.send(embed=embed)
        await giveaway_message.add_reaction(GIFT_EMOJI)

        await asyncio.sleep(GIVEAWAY_TIME.total_seconds())  # time for giveaway

        giveaway_message = await giveaway_message.channel.fetch_message(
            giveaway_message.id)
        giveaway_reaction = discord.utils.get(
            giveaway_message.reactions,
            emoji=GIFT_EMOJI,
            )
        giveaway_members = await giveaway_reaction.users().flatten()
        giveaway_members = [m for m in giveaway_members if not m.bot]

        try:
            giveaway_winner = random.choice(giveaway_members)
        except IndexError as e:
            # If list is empty, remove key from steam_keys_given
            # and delete the giveaway
            self.steam_keys_given.remove(game_info[1])
            await giveaway_message.delete()
            return

        try:
            await giveaway_winner.send(
                f'Congratulations! You won the giveaway for '
                f'**{game_info[0]}**!\n'
                f'Your Steam key is ||{game_info[1]}|| .\n'
                'Happy Holidays!'
                )
        except discord.Forbidden as e:
            app_info = await self.bot.application_info()
            await app_info.owner.send(
                f'Could not DM {giveaway_winner.display_name} '
                f'({giveaway_winner.mention}). They won the giveaway for '
                f'**{game_info[0]}** with key ||{game_info[1]}||.'
                )

        embed.description = (
            f'{giveaway_winner.display_name} won the giveaway for '
            f'[**{game_info[0]}**]({game_info[2]}). Congrats to them!'
            )

        await giveaway_message.edit(embed=embed)

    @giveaway_master_task.before_loop
    async def giveaway_master_before_loop(self):
        pass

    @giveaway_master_task.after_loop
    async def giveaway_master_after_loop(self):
        if self.giveaway_master_task.is_being_cancelled():
            await self.giveaway_master_task.ctx.send('Giveaway was stopped.')

        elif self.giveaway_master_task.failed():
            await self.giveaway_master_task.ctx.send(
                'An exception occured. Contact the Tech!')

        else:
            await self.giveaway_master_task.ctx.send('No more keys!')
