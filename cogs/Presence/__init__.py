from .presence import Presence


async def setup(bot):
    await bot.add_cog(Presence(bot))
