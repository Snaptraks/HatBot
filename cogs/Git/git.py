import asyncio
import discord
from discord.ext import commands

from ..utils.cog import BasicCog


class Git(BasicCog):
    """Commands for the GitHub repository."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.repo_url = 'https://github.com/Snaptraks/HatBot'

    @commands.group(aliases=['git'])
    async def github(self, ctx):
        """Prints the link for the GitHub repository."""
        if ctx.invoked_subcommand is None:
            await ctx.send(self.repo_url)

    @github.command(name='issues')
    async def github_issues(self, ctx):
        """Prints the link to the Issues page of the repository."""
        await ctx.send(self.repo_url+'/issues')
