import discord
import asyncio
from discord.ext import commands
import numpy as np
from datetime import datetime, timedelta

from ..utils.cogs import BasicCog

today = datetime.today()
April_Fools = datetime(year=today.year, month=4, day=1)
April_Sec = datetime(year=today.year, month=4, day=2)


def load_links(filename):
    with open(filename, 'r') as f:
        links = [l.strip('\n') for l in f.readlines()]
    return links


class NSFW(BasicCog):
    """Not Safe For Work!
    Written as an April Fool's joke
    """

    def __init__(self, bot):
        super().__init__(bot)

    async def on_ready(self):
        guild = discord.utils.get(
            self.bot.guilds,
            name='Hatventures Community'
            )
        everyone = discord.utils.get(guild.roles, name='@everyone')
        channel = discord.utils.get(guild.channels, name='nsfw')

        self.guild = guild
        self.everyone = everyone
        self.channel_nsfw = channel

    async def enable_channel(self):
        await self.bot.wait_until_ready()
        overwrite = discord.PermissionOverwrite(read_messages=True)
        delay = April_Fools - datetime.today()
        # print(delay.total_seconds())
        await asyncio.sleep(delay.total_seconds())
        # print('enabling channel')
        await self.channel_nsfw.set_permissions(
            self.everyone,
            overwrite=overwrite
            )
        await self.channel_nsfw.send('@everyone We now have a NSFW channel!')
        await self.channel_nsfw.send(
            ('If you want me to post NSFW images, just type `!nsfw`, '
             'and you will get a selected gif or picture! Just for you!'
            )
            )

    async def disable_channel(self):
        await self.bot.wait_until_ready()
        overwrite = discord.PermissionOverwrite(send_messages=False)
        delay = April_Sec - datetime.today()
        # print(delay.total_seconds())
        await asyncio.sleep(delay.total_seconds())
        # print('disabling channel')
        await self.channel_nsfw.set_permissions(
            self.everyone,
            overwrite=overwrite
            )
        await self.channel_nsfw.send('The NSFW channel is now closed.')

    @commands.cooldown(1, 1 * 60, commands.BucketType.channel)
    @commands.command(name='nsfw', hidden=True)
    @commands.is_nsfw()
    async def _nsfw(self, ctx):
        """Send a NSFW picture or gif to the NSFW channel."""
        
        channel = ctx.message.channel
        links = load_links('cogs/NSFW/links.txt')
        await channel.send(np.random.choice(links))
