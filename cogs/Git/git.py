import asyncio
import discord
from discord.ext import commands

from ..utils.cogs import BasicCog


class Git(BasicCog):
    """Commands for the GitHub repository."""

    def __init__(self, bot):
        super().__init__(bot)

        with open('.git/config') as f:
            while not 'remote "origin"' in f.readline():
                pass
            self.repo_url = f.readline().split()[-1]

    @commands.group(aliases=['git'])
    async def github(self, ctx):
        """Print the link for the GitHub repository."""

        if ctx.invoked_subcommand is None:
            await ctx.send(self.repo_url)

    @github.command(name='issues')
    async def github_issues(self, ctx):
        """Print the link to the Issues page of the repository."""

        await ctx.send(self.repo_url+'/issues')
