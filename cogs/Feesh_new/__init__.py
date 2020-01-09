from .feesh import FeeshCog


def setup(bot):
    bot.add_cog(FeeshCog(bot))
