import logging

import discord
from discord.ext import commands
from snapcogs import Bot

import config

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def main() -> None:
    intents = discord.Intents.default()
    intents.members = True
    allowed_mentions = discord.AllowedMentions(replied_user=False)

    startup_extensions = [
        "cogs.Announcements",
        "cogs.Presence",
        "snapcogs.Admin",
        "snapcogs.Information",
        "snapcogs.Tips",
    ]

    bot = Bot(
        description="Hatventures Community's helpful bot.",
        command_prefix=commands.when_mentioned_or("!"),
        intents=intents,
        allowed_mentions=allowed_mentions,
        db_name="db/HatBot.db",
        startup_extensions=startup_extensions,
    )

    bot.run(config.snapbot_token, log_level=logging.WARNING)


if __name__ == "__main__":
    main()
