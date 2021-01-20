import io
import discord
from discord.ext import commands
import aiowolframalpha

import config


class QueryError(commands.CommandError):
    pass


class WolframAlpha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wolfram_client = aiowolframalpha.Client(
            config.wolfram_alpha_api,
            session=self.bot.http_session,
        )

    @commands.group(aliases=["wa"], invoke_without_command=True)
    async def wolfram(self, ctx, *, query):
        """Wolfram|Alpha query command.
        Return the data in a nicely formatted Embed.
        """
        embed = discord.Embed(
            title="Wolfram|Alpha",
            description=f"Results for query ``{query}``",
            color=0xdd1100,
        )

        async with ctx.typing():
            result = await self.wolfram_client.query(query)

            if result.success == "false":
                raise QueryError(
                    "The query failed. Maybe try a different query?")

            for pod in result.pods:
                value = []

                for subpod in pod.subpods:
                    image = next(subpod.img)

                    plaintext = subpod.plaintext
                    if plaintext is not None:
                        value.append(f"• {plaintext}")

                    elif (embed.image.url == discord.Embed.Empty
                          and image is not None):
                        embed.set_image(
                            url=image.src,
                        )

                value = discord.utils.escape_markdown("\n".join(value))
                if value:
                    if len(value) > 1024:
                        value = "Too long to display."
                    embed.add_field(
                        name=pod.title,
                        value=value,
                    )

            await ctx.reply(embed=embed)

    @wolfram.command(name="simple", aliases=["s"])
    async def wolfram_simple(self, ctx, *, query):
        """Simple Wolfram|Alpha query command.
        Return the data in an already generated image from Wolfram itself.
        """
        async with ctx.typing():
            result = await self.get_wolfram_simple_query(query)
            file = discord.File(result, filename="wolfram_alpha_result.png")
            await ctx.reply(file=file)

    @wolfram.error
    @wolfram_simple.error
    async def wolfram_error(self, ctx, error):
        """Error handler for the wolfram command."""

        error = getattr(error, "original", error)

        if isinstance(error, (commands.MissingRequiredArgument,
                              QueryError)):
            await ctx.reply(error)

        else:
            await ctx.reply("Something went wrong!")
            raise error

    async def get_wolfram_simple_query(self, query):
        """Function to send the query to Wolfram|Alpha and return the
        generated image.
        """
        parameters = {
            "i": query,
            "appid": config.wolfram_alpha_api,
            "layout": "labelbar",  # default: "divider"
            "background": "36393F",  # default: "white"
            "foreground": "white",  # default: "black"
            "fontsize": 14,  # default: 14
            "width": 600,  # default: 500
            "units": "metric",  # default: location based
        }

        url = "http://api.wolframalpha.com/v1/simple"
        async with self.bot.http_session.get(url, params=parameters) as resp:
            if resp.status == 200:
                result = io.BytesIO(await resp.content.read())
                result.seek(0)

                return result

            else:
                raise QueryError(
                    "The query failed. Maybe try a different query?")
