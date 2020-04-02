from .acnh import ACNH


def setup(bot):
    bot.add_cog(ACNH(bot))
