from snapcogs import Bot
from .presence import Presence


async def setup(bot: Bot):
    await bot.add_cog(Presence(bot))
