from .announcements import Announcements


async def setup(bot):
    await bot.add_cog(Announcements(bot))
