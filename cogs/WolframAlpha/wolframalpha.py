import io
import discord
from discord.ext import commands

import config


class WolframAlpha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=["wa"], invoke_without_command=True)
    async def wolfram(self, ctx, *, query):

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

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(error)

        else:
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
                resp.raise_for_status()
