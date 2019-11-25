import asyncio
import csv
import random

import numpy as np
import discord
from discord.ext import commands, tasks

from ..utils.cogs import FunCog


GIFT_EMOJI = '\U0001F381'


class Christmas(FunCog):
    def __init__(self, bot):
        super().__init__(bot)

        self.steam_keys = []
        with open('cogs/Christmas/keys.csv', 'r') as f:
            csv_reader = csv.reader(f, delimiter=',')
            for i, row in enumerate(csv_reader):
                if i != 0:
                    self.steam_keys.append(tuple(row))

        self.steam_keys_given = set()  # save and load

    @commands.is_owner()
    @commands.group(aliases=['ga'])
    async def giveaway(self, ctx):
        pass

    @commands.is_owner()
    @giveaway.command(name='start')
    async def giveaway_start(self, ctx):
        try:
            self.giveaway_master_task.ctx = ctx
            self.giveaway_master_task.start(ctx)
        except RuntimeError as e:
            await ctx.send('Task alread running.', delete_after=15)

    @commands.is_owner()
    @giveaway.command(name='trigger')
    async def giveaway_trigger(self, ctx):
        self.bot.loop.create_task(self.giveaway_task(ctx))

    @tasks.loop(seconds=60)
    async def giveaway_master_task(self, ctx):
        self.bot.loop.create_task(self.giveaway_task(ctx))

    async def giveaway_task(self, ctx):
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
        embed.set_footer(
            text='Giveaway ends at TIMEUTC',
            )

        giveaway_message = await ctx.send(embed=embed)
        await giveaway_message.add_reaction(GIFT_EMOJI)

        await asyncio.sleep(15)  # time for giveaway

        giveaway_message = await giveaway_message.channel.fetch_message(
            giveaway_message.id)
        giveaway_reaction = discord.utils.get(
            giveaway_message.reactions,
            emoji=GIFT_EMOJI,
            )
        giveaway_members = await giveaway_reaction.users().flatten()
        giveaway_members = [m for m in giveaway_members if not m.bot]
        giveaway_winner = random.choice(giveaway_members)

        try:
            await giveaway_winner.send(
                f'Congratulations! You won the giveaway for **{game_info[0]}**!\n'
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

        if len(self.steam_keys) == len(self.steam_keys_given):
            self.giveaway_master_task.cancel()

    @giveaway_master_task.before_loop
    async def giveaway_master_before_loop(self):
        pass

    @giveaway_master_task.after_loop
    async def giveaway_master_after_loop(self):
        await self.giveaway_master_task.ctx.send('No more keys!')
