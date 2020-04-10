from .hvc import HVC


def setup(bot):
    bot.add_cog(HVC(bot))
