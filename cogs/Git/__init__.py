from .git import Git


def setup(bot):
    bot.add_cog(Git(bot))
