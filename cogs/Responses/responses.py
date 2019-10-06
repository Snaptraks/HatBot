import asyncio
from glob import glob
import json
import re

import discord
from discord.ext import commands
import numpy as np

from ..utils.datetime_modulo import datetime
from datetime import timedelta
from ..utils.cogs import BasicCog


class Responses(BasicCog):
    """Cog that adds on_message() functionality."""

    def __init__(self, bot):
        super().__init__(bot)

        # Init messaging channel.
        self.bot.loop.create_task(self.load_data())

        # Background tasks
        self.bg_tasks = [
            ]

        # hello_there parameters
        self.hello_there_params = {
            'cooldown': timedelta(minutes=1),
            'last_time': datetime.min,
            }

        # they_said parameters
        self.they_said_params = {
            'cooldown': timedelta(minutes=1),
            'chained': False,
            'last_author': None,
            'last_message': None,
            'last_time': datetime.min,
            }

    def cog_unload(self):
        super().cog_unload()
        for task in self.bg_tasks:
            task.cancel()  # Cancel background tasks

    async def load_data(self):
        """Load data from the server, such as channel and emoji"""

        await self.bot.wait_until_ready()
        guild = discord.utils.get(
            self.bot.guilds,
            name='Hatventures Community'
            )

        self.guild = guild

    @commands.Cog.listener(name='on_message')
    async def on_mention(self, message):
        """Send a funny reply when the bot is mentionned."""

        if self.bot.user.mention in message.content \
                and not message.author.bot \
                and not message.content.startswith(self.bot.command_prefix):

            with open('cogs/Responses/mentions.json', 'r') as f:
                mentions = json.load(f)['mentions']
            out = np.random.choice(mentions)
            await self.send_typing_delay(message.channel)
            await message.channel.send(out)

    @commands.Cog.listener(name='on_message')
    async def hello_there(self, message):
        """Send a picture if 'hello there' is in a message."""

        if 'hello there' in message.content.lower() \
                and not message.author.bot \
                and not message.content.startswith(self.bot.command_prefix) \
                and not self.bot.user.mention in message.content \
                and message.channel.name != 'general':

            dt = datetime.now() - self.hello_there_params['last_time']

            if dt > self.hello_there_params['cooldown']:
                pics = glob('cogs/Responses/hellothere/*.*')
                meme = discord.File(np.random.choice(pics))
                await self.send_typing_delay(message.channel)
                # await self.channel_msg.send(file=meme)
                await message.channel.send(file=meme)
                self.hello_there_params['last_time'] = datetime.now()

    @commands.Cog.listener(name='on_message')
    async def they_said(self, message):
        """Reply with the last message IN CAPS."""

        whats = ('what', 'whut', 'whot', 'wat', 'wut', 'wot')

        if message.content.lower() in whats \
                and message.channel.name != 'general':

            author = message.author
            channel = message.channel
            dt = datetime.now() - self.they_said_params['last_time']

            if author == self.they_said_params['last_author'] \
                    and dt < self.they_said_params['cooldown']:

                self.they_said_params['last_time'] = datetime.now()
                return  # don't let people spam wat in succession

            i = 0
            async for m in channel.history(limit=3):

                i += 1
                is_valid = False

                if i == 1:  # first message, a whats, skip
                    continue

                elif i == 2 and not m.author.bot:  # possible message to repeat
                    # don't select a message from the same person
                    # don't select a bot's message
                    # don't select a whats
                    # don't select a message with embeds
                    # don't select a message with attachments
                    # don't select a message with mentions
                    # don't select a message with role mentions
                    # don't select a message that mentionned @everyone
                    is_valid = m.author != author \
                        and not m.author.bot \
                        and m.content.lower() not in whats \
                        and len(m.embeds) == 0 \
                        and len(m.attachments) == 0 \
                        and len(m.mentions) == 0 \
                        and len(m.role_mentions) == 0 \
                        and not m.mention_everyone

                    # if a second whats is sent, only repeat the same message
                    # if it follows a whats directly
                    self.they_said_params['chained'] = is_valid

                elif i == 3 and self.they_said_params['chained']:
                    if m.content.lower() in whats:
                        is_valid = True
                        m = self.they_said_params['last_message']
                    else:
                        # don't send anything
                        # print('stop looking for message')
                        return

                if is_valid:
                    self.they_said_params['last_author'] = author
                    self.they_said_params['last_message'] = m
                    self.they_said_params['last_time'] = datetime.now()
                    out_content = m.content.upper()

                    if message.content == message.content.upper():
                        prefix = 'THEY SAID'
                    else:
                        prefix = 'They said'

                    out_str = '{} **{}**'.format(prefix, out_content)
                    await self.send_typing_delay(channel)
                    await channel.send(out_str)
                    # print('Sent they_said at i={} ({})'.format(i, out_content))
                    return

    async def send_typing_delay(self, channel):
        r = np.random.rand()  # [0, 1)
        t = 1.5 * r + 0.5  # [0.5, 2)
        await channel.trigger_typing()
        await asyncio.sleep(t)
