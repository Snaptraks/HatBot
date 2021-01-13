from discord.ext import commands
import aiowolframalpha

import config


class WolframAlpha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wolfram_client = aiowolframalpha.Client(
            config.wolfram_alpha_api,
            session=self.bot.http_session,
        )

    @commands.command()
    async def wolfram(self, ctx, *, input_):
        res = await self.wolfram_client.query(input_)
