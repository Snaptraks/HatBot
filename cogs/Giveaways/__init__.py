from snapcogs.bot import Bot

from .giveaways import Giveaways


async def setup(bot: Bot) -> None:
    await bot.add_cog(Giveaways(bot))
