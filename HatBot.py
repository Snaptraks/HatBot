import asyncio
import logging
import platform
import sys

import aiohttp
from datetime import datetime
import discord
from discord.ext.commands import Bot
from discord.ext import commands

import config


async def create_http_session(loop):
    """Create an async HTTP session. Required to be from an async function
    by aiohttp 3.5.4
    """
    return aiohttp.ClientSession(loop=loop)


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create HTTP session
        self.http_session = self.loop.run_until_complete(
            create_http_session(self.loop))

        self.boot_time = datetime.now()

    async def close(self):
        """Subclass the close() method to close the HTTP Session."""

        await self.http_session.close()
        await super().close()

    async def on_ready(self):
        print(
            f'Logged in as {self.user.name} (ID:{self.user.id}) '
            f'| Connected to {len(self.guilds)} guilds '
            f'| Connected to {len(set(self.get_all_members()))} users'
            )
        print('--------')
        print(f'Startup Time: {datetime.now()}')
        print('--------')
        print(
            f'Current Discord.py Version: {discord.__version__} '
            f'| Current Python Version: {platform.python_version()}'
            )
        print('--------')
        print(f'Use this link to invite {self.user.name}:')
        print(discord.utils.oauth_url(self.user.id))
        print('--------')

        # make sure to populate self.owner_id at startup
        await self.owner()

    async def owner(self):
        user = self.get_user(self.owner_id)
        if user:
            return user

        else:
            app = await self.application_info()
            self.owner_id = app.owner.id
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

    if 'win32' in sys.platform:
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    loop = asyncio.get_event_loop()

    bot = MyBot(
        description='HatBot by Snaptraks#2606',
        command_prefix='!',
        help_command=commands.DefaultHelpCommand(dm_help=True),
        loop=loop,
        )

    # This specifies what extensions to load when the bot starts up
    startup_extensions = [
        'cogs.Admin',
        'cogs.Announcements',
        'cogs.Dev',
        'cogs.Feesh',
        'cogs.Fun',
        'cogs.Git',
        'cogs.Help',
        'cogs.Info',
        'cogs.Levels',
        'cogs.Minigames',
        'cogs.Moderation',
        'cogs.Poll',
        'cogs.Presence',
        'cogs.Reminders',
        'cogs.Responses',
        'cogs.Roles',
        ]

    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))

    bot.run(config.hatbot_token)
