from snapcogs import Bot
from .giveaways import Giveaways


async def setup(bot: Bot):
    await bot.add_cog(Giveaways(bot))
