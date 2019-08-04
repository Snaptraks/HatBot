from .feesh import Feesh


def setup(bot):
    bot.add_cog(Feesh(bot))
