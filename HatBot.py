import discord
import asyncio
import aiohttp
import json
import logging
import pickle
import platform
import sys
import time

from discord.ext.commands import Bot
from discord.ext import commands
import numpy as np

# custom datetime with modulo
from cogs.utils.datetime_modulo import datetime
from datetime import timedelta
import config


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename='HatBot.log',
    encoding='utf-8',
    mode='a',
    )
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # background tasks
        game_period = timedelta(hours=1)
        self.bg_game = self.loop.create_task(self.change_game(game_period))

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
        print(inv_link.format(self.user.id))
        print('--------')

    async def on_message(self, message):

        if message.content.startswith(self.command_prefix):
            # run the command, if it is one
            await self.process_commands(message)

    async def on_reaction_add(self, reaction, user):
        message = reaction.message
        if not user.bot and not message.author.bot:
            emoji = reaction.emoji
            r = np.random.randint(10)
            if r == 0:
                await asyncio.sleep(2)
                await message.add_reaction(emoji)

    async def change_game(self, period):
        """
        Input
        -----
        period : timedelta
            Period of the message.
        """
        if not isinstance(period, timedelta):
            raise ValueError('period {:f} is not timedelta'.format(period))

        await self.wait_until_ready()

        while not self.is_closed():
            with open('games.json', 'r') as f:
                games = json.load(f)['games']
            game_name = np.random.choice(games)
            await self.change_presence(activity=discord.Game(name=game_name))
            await asyncio.sleep(period.total_seconds())


if __name__ == '__main__':

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
        'cogs.Dev',
        'cogs.Feesh',
        'cogs.Fun',
        'cogs.Info',
        'cogs.Levels',
        'cogs.Moderation',
        'cogs.Poll',
        'cogs.Responses',
        'cogs.Roles',
        'cogs.Snake',
        ]

    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))

    loop.run_until_complete(bot.start(config.hatbot_token))
