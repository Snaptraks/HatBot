import asyncio
import inspect
import os
import pickle

import discord
from discord.ext import commands
from discord.ext.commands import Cooldown, CooldownMapping, BucketType


class BasicCog(commands.Cog):
    """Basic class for Cog methods that are used often, like for saving/
    restoring cooldowns.
    """

    def __init__(self, bot):
        self.bot = bot
        self._cog_path = os.path.dirname(inspect.getfile(self.__class__))
        # Restore cooldowns
        try:
            # Open the cog's cooldowns
            with open(os.path.join(self._cog_path, 'cooldowns.pkl'), 'rb') as f:
                buckets = pickle.load(f)
        except (FileNotFoundError, EOFError):
            # If the file does not already exist, just skip
            buckets = {}

        # iterate on the set() of commands, in case of aliases
        for command in set(self.walk_commands()):
            try:
                cld_map = buckets[command.name]

            except KeyError:
                # If the command does not have a cooldown,
                # ie. it was added and has not been backed up yet
                continue

            original_cd = cld_map._cooldown

            current = command._buckets.copy()

            if current._cooldown is None:
                # do no restore if current command has no cooldown
                continue

            elif original_cd != extract_cooldown(current._cooldown):
                # use the new cooldown / BucketType if it is different
                # than the one saved
                continue

            # Restore BucketType Enum
            if original_cd is not None:
                cld_map._cooldown = restore_cooldown(original_cd)

            # Restore the _cache
            for key in cld_map._cache.keys():
                cld_map._cache[key] = \
                    restore_cooldown(cld_map._cache[key])

            # Restore to command
            command._buckets = cld_map

    def cog_unload(self):
        # Save cooldowns to disk
        buckets = {}
        # iterate on the set() of commands, in case of aliases
        for command in set(self.walk_commands()):
            # Create a copy of the cooldown mappings
            cld_map = command._buckets.copy()
            if cld_map._cooldown is not None:
                original_cd = extract_cooldown(cld_map._cooldown)
            else:
                original_cd = None

            # Overrite BucketType Enum
            cld_map._cooldown = original_cd

            # Save the _cache
            for key in cld_map._cache.keys():
                # print(cld_map._cache[key])
                cld_map._cache[key] = \
                    extract_cooldown(cld_map._cache[key])

            # Save in dict by command name
            buckets[command.name] = cld_map

        # Save the cog's cooldowns to a file
        with open(os.path.join(self._cog_path, 'cooldowns.pkl'), 'wb') as f:
            pickle.dump(buckets, f)


class FunCog(BasicCog):
    """Cogs with commands that can only be run in hatbot channels."""

    def cog_check(self, ctx):
        if ctx.guild:
            # Hatventures Community server
            if ctx.guild.id == 308049114187431936:
                category = ctx.channel.category
                return (
                    category is not None
                    # bots category
                    and category.id == 586524742022987778
                )

        return True


def extract_cooldown(cooldown):
    """Assume we already checked it exists (is not None)."""
    cld_dict = {x: getattr(cooldown, x) for x in cooldown.__slots__}
    cld_dict['type'] = cld_dict['type'].name
    return cld_dict


def restore_cooldown(cld_dict):
    """Assume we already checked it exists (is not None)."""
    rate = cld_dict['rate']
    per = cld_dict['per']
    cdtype = BucketType[cld_dict['type']]
    cooldown = Cooldown(rate, per, cdtype)
    cooldown._window = cld_dict['_window']
    cooldown._tokens = cld_dict['_tokens']
    cooldown._last = cld_dict['_last']
    return cooldown
