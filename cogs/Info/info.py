import asyncio
import io
import json

import discord
from discord.ext import commands
from mcstatus import MinecraftServer

from ..utils.cogs import BasicCog
from ..utils.datetime_modulo import datetime
from datetime import timedelta
import config


class Info(BasicCog):
    """Collection of informative commands."""

    def __init__(self, bot):
        super().__init__(bot)
        with open('cogs/Info/tz/tz.json', 'r') as f:
            self.tz_table = json.load(f)

    @commands.command()
    async def ts(self, ctx):
        """Get the TeamSpeak server information."""

        embed = discord.Embed(
            title='TeamSpeak Server',
            description='Come chat with us!',
            colour=0x445277,
            url='https://www.teamspeak.com/',
            )
        embed.add_field(
            name='IP',
            value=config.hvc_ts['ip'],
            inline=False,
            )
        embed.set_thumbnail(url=config.hvc_ts['icon'])
        await ctx.send(embed=embed)

    @commands.command(aliases=['map', 'ip'])
    async def mc(self, ctx):
        """Get the Minecraft server information."""

        server = MinecraftServer.lookup(config.hvc_mc['ip'])

        embed = discord.Embed(
            title='Minecraft Server',
            description='Official Hatventures Community Minecraft server',
            colour=0x5A894D,
            url=None)
        embed.add_field(
            name='IP',
            value=config.hvc_mc['ip_name'],
            inline=True
            )
        embed.add_field(
            name='Dynmap',
            value=config.hvc_mc['dynmap'],
            inline=True
            )
        try:
            status = server.status()
            embed.add_field(
                name='Version',
                value=status.version.name,
                inline=True
                )
            embed.add_field(
                name='Status',
                value='Online!',
                inline=True
                )
            embed.add_field(
                name='Players',
                value='{0.online}/{0.max}'.format(status.players),
                inline=True
                )
        except Exception as e:
            print(e)
            embed.add_field(name='Status', value='Offline!')

        embed.set_thumbnail(url=config.hvc_mc['icon'])

        await ctx.send(embed=embed)

    @commands.command()
    async def time(self, ctx, tz_abr='UTC'):
        """Get the current time in the requested timezone."""

        now_utc = ctx.message.created_at
        tz_abr = tz_abr.upper()

        try:
            TZ = self.tz_table[tz_abr]
        except KeyError:
            TZ = self.tz_table['UTC']
            tz_abr = 'UTC'

        utc_offset = timedelta(
            hours=TZ['HOURS'],
            minutes=TZ['MINUTES'],
            )
        now_tz = now_utc + utc_offset
        now_tz = datetime.fromtimestamp(now_tz.timestamp())

        # Round time to previous half-hour, for emoji
        r_time = now_tz - (now_tz % timedelta(minutes=30))
        r_time = r_time.strftime('%I%M')
        if r_time[-2:] == '00':
            r_time = r_time[-4:-2]
        r_time = int(r_time)

        emoji = f':clock{r_time}:'
        now = now_tz.strftime('%H:%M')
        tz_name = TZ['NAME']
        offset = TZ['OFFSET']

        out_str = f'{emoji} It is {now} {tz_abr} ({tz_name}, {offset}).'
        await ctx.send(out_str)

    @commands.command(aliases=['pfp'])
    async def avatar(self, ctx, *, member: discord.Member = None):
        """Send the member's avatar in the channel."""

        if member is None:
            member = ctx.author

        avatar_url = str(member.avatar_url_as(size=4096))
        try:
            extension = \
                avatar_url[avatar_url.rindex('.'):avatar_url.rindex('?')]
        except ValueError as e:
            extension = '.png'

        async with self.bot.http_session.get(avatar_url) as resp:
            if resp.status == 200:
                data = io.BytesIO(await resp.content.read())
        file = discord.File(data, filename=f'{member.id}{extension}')

        await ctx.send(file=file)
