from .responses import Responses


def setup(bot):
    bot.add_cog(Responses(bot))
