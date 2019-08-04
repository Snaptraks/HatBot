import asyncio
import discord
from discord.ext import commands

from ..utils.cog import BasicCog


class Git(BasicCog):
    """Commands for the GitHub repository."""
    def __init__(self, bot):
        super().__init__(bot)

    @commands.command()
    async def git(self, ctx):
        await ctx.send('https://github.com/Snaptraks/HatBot')
