from .presence import Presence


def setup(bot):
    bot.add_cog(Presence(bot))
