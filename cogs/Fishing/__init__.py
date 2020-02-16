from .fishing import Fishing


def setup(bot):
    bot.add_cog(Fishing(bot))
