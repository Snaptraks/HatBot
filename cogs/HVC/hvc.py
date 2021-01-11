import discord
from discord.ext import commands
from mcstatus import MinecraftServer

from ..utils.cogs import BasicCog
import config


class HVC(BasicCog):
    """Module for information regarding the Hatventures Community."""

    def __init__(self, bot):
        super().__init__(bot)

    @commands.command(aliases=["ts"])
    async def teamspeak(self, ctx):
        """Get the TeamSpeak server information."""

        embed = discord.Embed(
            title="TeamSpeak Server",
            description="Come chat with us!",
            colour=0x445277,
            url="https://www.teamspeak.com/",
        )
        embed.add_field(
            name="IP",
            value=config.hvc_ts['ip'],
            inline=False,
        )
        embed.set_thumbnail(url=config.hvc_ts['icon'])
        await ctx.reply(embed=embed)

    @commands.command(aliases=["mc", "map", "ip"])
    async def minecraft(self, ctx):
        """Get the Minecraft server information."""

        server = MinecraftServer.lookup(config.hvc_mc['ip'])

        embed = discord.Embed(
            title="Minecraft Server",
            description="Official Hatventures Community Minecraft server",
            colour=0x5A894D,
            url=None)
        embed.add_field(
            name="IP",
            value=config.hvc_mc['ip_name'],
            inline=True
        )
        embed.add_field(
            name="Dynmap",
            value=config.hvc_mc['dynmap'],
            inline=True
        )
        try:
            status = server.status()
            embed.add_field(
                name="Version",
                value=status.version.name,
                inline=True
            )
            embed.add_field(
                name="Status",
                value="Online!",
                inline=True
            )
            embed.add_field(
                name="Players",
                value=f"{status.players.online}/{status.players.max}",
                inline=True
            )
        except Exception as e:
            print(e)
            embed.add_field(name="Status", value="Offline!")

        embed.set_thumbnail(url=config.hvc_mc['icon'])

        await ctx.reply(embed=embed)

    @commands.command()
    async def ttt(self, ctx):
        """Get Capgun's TTT server information."""

        embed = discord.Embed(
            title="TTT Server",
            description=(
                "Provided and managed by <@136971401566355456>"
            ),
            colour=0x1394F0,
        )
        embed.add_field(
            name="IP",
            value=config.capgun_ttt['ip'],
        )
        embed.add_field(
            name="Password",
            value=config.capgun_ttt['password'],
        )

        # link = "steam://connect/{ip}/{password}".format(**config.capgun_ttt)
        link = (
            f"steam://connect/{config.capgun_ttt.ip}/"
            f"{config.capgun_ttt.password}"
        )
        await ctx.reply(content=link, embed=embed)
