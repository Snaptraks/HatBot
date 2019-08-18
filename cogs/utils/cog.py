import asyncio
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
        # Restore cooldowns
        try:
            # Open the cog's cooldowns
            with open(f'cogs/{self.qualified_name}/cooldowns.pkl', 'rb') as f:
                buckets = pickle.load(f)
            # iterate on the set() of commands, in case of aliases
            for command in set(self.walk_commands()):
                try:
                    cld_map = buckets[command.name]
                    original_cd = cld_map._cooldown

                    # Restore BucketType Enum
                    if original_cd is not None:
                        cld_map._cooldown = restore_cooldown(original_cd)

                    # Restore the _cache
                    for key in cld_map._cache.keys():
                        cld_map._cache[key] = \
                            restore_cooldown(cld_map._cache[key])

                    # Restore to command
                    command._buckets = cld_map

                except KeyError:
                    # If the command does not have a cooldown,
                    # ie. it was added and has not been backed up yet
                    pass

        except FileNotFoundError:
            # If the file does not already exist, just skip
            pass

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
        with open(f'cogs/{self.qualified_name}/cooldowns.pkl', 'wb') as f:
            pickle.dump(buckets, f)


class FunCog(BasicCog):
    """Cogs with commands that can only be run in hatbot channels."""

    def cog_check(self, ctx):
        if ctx.guild:
            if ctx.guild.name == 'Hatventures Community':
                ch_name = ctx.channel.name
                return ch_name.startswith('hatbot')
            else:
                return True
        else:
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
