from snapcogs.bot import Bot

from .halloween import Halloween
from .trophies import Trophies


async def setup(bot: Bot) -> None:
    await bot.add_cog(Halloween(bot))
    await bot.add_cog(Trophies(bot))
