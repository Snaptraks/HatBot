from snapcogs import Bot
from .avatar import Avatar


async def setup(bot: Bot) -> None:
    await bot.add_cog(Avatar(bot))
