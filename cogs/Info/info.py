import io
import json

import discord
from discord.ext import commands

from ..utils.cogs import BasicCog
from ..utils.datetime_modulo import datetime
from ..utils.formats import pretty_print_timedelta
from datetime import timedelta


class Info(BasicCog):
    """Collection of informative commands."""

    def __init__(self, bot):
        super().__init__(bot)
        with open('cogs/Info/tz/tz.json', 'r') as f:
            self.tz_table = json.load(f)

    @commands.command()
    async def about(self, ctx):
        """Get information about the bot itself.
        Inspired by RoboDanny.
        """
        embed = discord.Embed(
            title="Official GitHub Repository",
            url="https://github.com/Snaptraks/HatBot",
            color=discord.Color.blurple(),
            description=(
                f"Information about {str(self.bot.user)}."
            ),
        )

        owner = self.bot.owner
        embed.set_author(
            name=str(self.bot.user),
            icon_url=self.bot.user.avatar_url,
        )

        # some statistics
        version = discord.__version__

        total_members = 0
        total_online = 0
        offline = discord.Status.offline
        for member in self.bot.get_all_members():
            total_members += 1
            if member.status is not offline:
                total_online += 1

        total_unique = len(self.bot.users)

        text_channels = 0
        voice_channels = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text_channels += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice_channels += 1

        embed.add_field(
            name="Members",
            value=(
                f"{total_members} total\n"
                f"{total_unique} unique\n"
                f"{total_online} online"
            ),
        )
        embed.add_field(
            name="Channels",
            value=(
                f"{text_channels + voice_channels} total\n"
                f"{text_channels} text\n"
                f"{voice_channels} voice"
            ),
        )
        embed.add_field(
            name="Servers",
            value=guilds,
        )
        embed.add_field(
            name="Uptime",
            value=pretty_print_timedelta(datetime.utcnow()
                                         - self.bot.boot_time),
        )

        embed.set_footer(
            text=f"Made with discord.py v{version} by {str(owner)}",
            icon_url="http://i.imgur.com/5BFecvA.png",
        )
        embed.timestamp = datetime.utcnow()

        await ctx.send(embed=embed)

    @commands.command()
    async def time(self, ctx, tz_abr="UTC"):
        """Get the current time in the requested timezone."""

        now_utc = ctx.message.created_at
        tz_abr = tz_abr.upper()

        try:
            TZ = self.tz_table[tz_abr]
        except KeyError:
            TZ = self.tz_table['UTC']
            tz_abr = "UTC"

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

        emoji = f":clock{r_time}:"
        now = now_tz.strftime('%H:%M')
        tz_name = TZ['NAME']
        offset = TZ['OFFSET']

        content = f"{emoji} It is {now} {tz_abr} ({tz_name}, {offset})."
        await ctx.send(content)

    @commands.command(aliases=["pfp"])
    async def avatar(self, ctx, *, member: discord.Member = None):
        """Send the member's avatar in the channel."""

        if member is None:
            member = ctx.author

        avatar_url = str(member.avatar_url_as(size=4096))
        try:
            extension = \
                avatar_url[avatar_url.rindex('.'):avatar_url.rindex('?')]
        except ValueError as e:
            extension = ".png"

        async with self.bot.http_session.get(avatar_url) as resp:
            if resp.status == 200:
                data = io.BytesIO(await resp.content.read())
        file = discord.File(data, filename=f'{member.id}{extension}')

        await ctx.send(file=file)
