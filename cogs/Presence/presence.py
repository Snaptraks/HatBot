import asyncio
import copy
import json

import discord
from discord.ext import commands, tasks
import numpy as np

from ..utils.cogs import BasicCog


def get_streaming_activity(activities):
    """Return the discord.Streaming Activity from a list of Activities.
    Return None if no Activities match.
    """
    return discord.utils.get(
        activities, type=discord.ActivityType.streaming)


class Presence(BasicCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.streaming_activities = dict()
        self.advertising_streams = False

        with open('cogs/Presence/presence.json', 'r') as f:
            self.activities = json.load(f)

        self.change_presence.start()

    def cog_unload(self):
        super().cog_unload()

        self.change_presence.cancel()
        self.advertise_streams.cancel()
        self.reset_presence.start()

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    # @commands.Cog.listener(name='on_member_update')
    async def on_streaming(self, before: discord.Member, after: discord.Member):
        """Detects when a member starts or stops streaming."""

        # exit early if member is a bot
        if before.bot:
            return

        streaming_before = get_streaming_activity(before.activities)
        streaming_after = get_streaming_activity(after.activities)

        # DEBUG: print the streaming activities
        if before.id == 337266376941240320:
            print(before.activities)
            print(after.activities)
            print(streaming_before, streaming_after)
            print('==:', streaming_before == streaming_after)
            print('!=:', streaming_before != streaming_after)
            print('before is not None AND after is None:',
                  streaming_before is not None and streaming_after is None)

        # exit early if no changes were made to the Streaming activities
        if streaming_before == streaming_after:
            return

        # detect if a Streaming activity is added/removed in the update
        if streaming_before != streaming_after:
            # if a member starts streaming
            # OR
            # if a member updates their stream
            self.streaming_activities[after.id] = streaming_after

            if not self.advertising_streams and self.is_any_streaming:
                # do not start the task if it is already running
                # or no one is streaming.
                # the second condition should always be True if we added
                # an activity the line before...
                self.advertise_streams.start()

        elif streaming_before is not None and streaming_after is None:
            # if a member stops streaming
            try:
                self.streaming_activities.pop(after.id)
            except KeyError:
                pass

            if self.advertising_streams and not self.is_any_streaming:
                # cancel the task only if it is running AND no one
                # is streaming
                self.advertise_streams.cancel()

        else:
            print(
                'WEIRD MEMBER_UPDATE EVENT',
                streaming_before,
                streaming_after)

    @tasks.loop(hours=1)
    async def change_presence(self):
        """Change the Bot's presence periodically with a random activity."""

        activity_dict = np.random.choice(self.activities)
        type = activity_dict['activitytype']
        name = activity_dict['name']
        activity = discord.Activity(
            type=discord.ActivityType.try_value(type),
            name=name,
        )

        await self.bot.change_presence(activity=activity)

    @change_presence.before_loop
    async def change_presence_before(self):
        """Wait until the Bot is fully loaded."""
        await self.bot.wait_until_ready()

    @property
    def is_any_streaming(self):
        """Return if there are any registered current streams."""
        return len(self.streaming_activities) > 0

    @tasks.loop(minutes=15)
    async def advertise_streams(self):
        """Change the Bot's presence to cycle through members' streams."""

        id = np.random.choice(list(self.streaming_activities))
        user = self.bot.get_user(id)
        # do not edit the one in the dict
        streaming_activity = copy.copy(self.streaming_activities[id])
        streaming_activity.name = (
            f'[{str(user)}]: '
            f'{streaming_activity.name}'
        )
        await self.bot.change_presence(activity=streaming_activity)

    @advertise_streams.before_loop
    async def advertise_streams_before(self):
        """Cancel the change_presence task before advertising streams."""
        self.change_presence.cancel()
        self.advertising_streams = True

    @advertise_streams.after_loop
    async def advertise_streams_after(self):
        """Restart the change_presence task."""
        self.change_presence.start()
        self.advertising_streams = False

    @tasks.loop(count=1)
    async def reset_presence(self):
        """Reset the Bot's presence."""
        await self.bot.change_presence(activity=None)
