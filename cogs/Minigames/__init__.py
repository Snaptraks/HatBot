from .minigames import Minigames


def setup(bot):
    bot.add_cog(Minigames(bot))
