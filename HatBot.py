import logging
import platform
import aiosqlite

import aiohttp
from datetime import datetime
import discord
from discord.ext.commands import Bot
from discord.ext import commands

import config


async def create_http_session(loop):
    """Create an async HTTP session. Required to be from an async function
    by aiohttp>=3.5.4
    """
    return aiohttp.ClientSession(loop=loop)


async def create_db_connection(db_name):
    """Create the connection to the database."""

    return await aiosqlite.connect(
        db_name, detect_types=1)  # 1: parse declared types


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create HTTP session
        self.http_session = self.loop.run_until_complete(
            create_http_session(self.loop))

        # Make DB connection
        self.db = self.loop.run_until_complete(
            create_db_connection(kwargs.get('db_name', ':memory:')))
        # allow for name-based access of data columns
        self.db.row_factory = aiosqlite.Row

        self.boot_time = datetime.utcnow()

    async def close(self):
        """Subclass the close() method to close the HTTP Session."""

        await self.http_session.close()
        # because .close is called twice for some reason
        # if self.db._connection:
        #     await self.db.close()
        await self.db.close()
        await super().close()

    async def on_ready(self):
        permissions = discord.Permissions(permissions=67584)
        oauth_url = discord.utils.oauth_url(
            self.user.id, permissions=permissions)
        print(
            f"Logged in as {self.user.name} (ID:{self.user.id}) "
            f"| Connected to {len(self.guilds)} guilds "
            f"| Connected to {len(set(self.get_all_members()))} users\n"
            "--------\n"
            f"Startup Time: {self.boot_time.strftime('%c')} UTC\n"
            f"Current Time: {datetime.utcnow().strftime('%c')} UTC\n"
            "--------\n"
            f"Current Discord.py Version: {discord.__version__} "
            f"| Current Python Version: {platform.python_version()}\n"
            "--------\n"
            f"Use this link to invite {self.user.name}:\n"
            f"{oauth_url}\n"
            "--------"
        )

        # make sure to populate self.owner_id at startup
        await self.init_owner()

    async def init_owner(self):
        user = self.get_user(self.owner_id)
        if user:
            return user

        else:
            app = await self.application_info()
            self.owner_id = app.owner.id
            self.owner = app.owner
            return app.owner


if __name__ == '__main__':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        filename='HatBot.log',
        encoding='utf-8',
        mode='w',
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # TODO: Filter out intents that are not needed
    intents = discord.Intents.all()

    bot = MyBot(
        description="HatBot by Snaptraks#2606",
        command_prefix="!",
        help_command=commands.DefaultHelpCommand(dm_help=True),
        intents=intents,
        chunk_guilds_at_startup=True,
        db_name='db/HatBot.db',
    )

    # This specifies what extensions to load when the bot starts up
    startup_extensions = [
        'cogs.ACNH',
        'cogs.Admin',
        'cogs.Announcements',
        'cogs.Dev',
        'cogs.Fishing',
        'cogs.Fun',
        'cogs.Git',
        'cogs.Help',
        'cogs.HVC',
        'cogs.Info',
        'cogs.Minigames',
        'cogs.Moderation',
        'cogs.Poll',
        'cogs.Presence',
        'cogs.Reminders',
        'cogs.Responses',
        'cogs.Roles',
        'cogs.Halloween',
    ]

    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = f"{type(e).__name__}: {e}"
            print(f"Failed to load extension {extension}\n{exc}")

    bot.run(config.hatbot_token)
