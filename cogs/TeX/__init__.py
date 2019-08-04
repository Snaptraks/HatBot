from .tex import TeX


def setup(bot):
    bot.add_cog(TeX(bot))
