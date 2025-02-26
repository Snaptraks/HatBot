from snapcogs.bot import Bot

from .presence import Presence


async def setup(bot: Bot) -> None:
    await bot.add_cog(Presence(bot))
