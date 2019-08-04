from .poll import Poll


def setup(bot):
    bot.add_cog(Poll(bot))
