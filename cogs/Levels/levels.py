import asyncio
import logging
import pickle

import discord
from discord.ext import commands
import numpy as np

from ..utils.cog import BasicCog
from .userprofile import UserProfile


class Levels(BasicCog):
    def __init__(self, bot):
        # init self.bot and cooldowns
        super().__init__(bot)
        # Load levels data
        try:
            with open('cogs/Levels/levels_data.pkl', 'rb') as f:
                self.data = pickle.load(f)
        except FileNotFoundError:
            # File does not exist yet, make it an empty dict
            self.data = {}

    def cog_unload(self):
        super().cog_unload()
        self._save_data()
        # cancel background tasks?

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author
        if not isinstance(author, discord.Member):
            # skip if the author is not a member (ie webhook)
            return
        if not isinstance(message.channel, discord.channel.TextChannel):
            # skip if not in a text channel
            return
        if author.bot:
            # skip if it is a message from a bot
            return
        if message.content.startswith(self.bot.command_prefix):
            # if the message is a command
            return

        try:
            profile = self.data[author.id]
        except KeyError as e:
            # author doesn't have a profile yet
            self.data[author.id] = UserProfile(author)
            profile = self.data[author.id]

        profile.give_exp(message)

        self._save_data()

    def _save_data(self):
        with open('cogs/Levels/levels_data.pkl', 'wb') as f:
            pickle.dump(self.data, f)

    @commands.command()
    @commands.is_owner()
    async def exp(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        try:
            await ctx.send(self.data[member.id].exp)
        except KeyError as e:
            await ctx.send(0)
