from snapcogs.bot import Bot

from .halloween import Halloween


async def setup(bot: Bot) -> None:
    await bot.add_cog(Halloween(bot))
