import asyncio
import logging
import platform
import sys

import aiohttp
from datetime import datetime
import discord
from discord.ext.commands import Bot
from discord.ext import commands
import numpy as np

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

    async def close(self):
        """Subclass the close() method to close the HTTP Session."""

        await self.http_session.close()
        await super().close()

    async def on_ready(self):
        print('Logged in as ' +
              self.user.name +
              ' (ID:' +
              str(self.user.id) +
              ') | Connected to ' +
              str(len(self.guilds)) +
              ' guilds | Connected to ' +
              str(len(set(self.get_all_members()))) +
              ' users')
        print('--------')
        print('Startup Time: {}'.format(datetime.now()))
        print('--------')
        print(('Current Discord.py Version: {} | ' +
               'Current Python Version: {}').format(discord.__version__,
                                                    platform.python_version()))
        print('--------')
        print('Use this link to invite {}:'.format(self.user.name))
        inv_link = discord.utils.oauth_url(self.user.id)
        print(inv_link)
        print('--------')


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
        'cogs.Halloween',
        'cogs.Info',
        'cogs.Levels',
        'cogs.Minigames',
        'cogs.Moderation',
        'cogs.Poll',
        'cogs.Presence',
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
