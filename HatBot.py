import logging
from pathlib import Path
from typing import Any

import discord
import tomllib
from discord.ext import commands
from snapcogs import Bot

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def load_config(file_path: Path | str) -> dict[str, Any]:
    with open(file_path, "rb") as f:
        return tomllib.load(f)


def main() -> None:
    config = load_config("config.toml")
    intents = discord.Intents.default()
    intents.members = True
    allowed_mentions = discord.AllowedMentions(replied_user=False)

    startup_extensions = [
        "cogs.Announcements",
        "cogs.Avatar",
        "cogs.Giveaways",
        "cogs.Presence",
        "snapcogs.Admin",
        "snapcogs.Fun",
        "snapcogs.Information",
    ]

    bot = Bot(
        description="Hatventures Community's helpful bot.",
        command_prefix=commands.when_mentioned_or("!"),
        intents=intents,
        allowed_mentions=allowed_mentions,
        db_name="db/HatBot.db",
        startup_extensions=startup_extensions,
    )

    bot.run(config["hatbot_token"], log_level=logging.WARNING)


if __name__ == "__main__":
    main()
