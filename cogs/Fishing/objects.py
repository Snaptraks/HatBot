import json
from datetime import datetime
import os

import discord
import numpy as np


with open(os.path.join(os.path.dirname(__file__), 'fish.json')) as f:
    FISH_SPECIES = json.load(f)


def get_fish_species_str(size, species_index):
    return FISH_SPECIES[size]['species'][species_index]


SMELLS = [
    'It smells delightful!',
    'It smells alright.',
    'It does not smell that bad.',
    'It does not smell anything.',
    'It does not smell good.',
    'It smells bad.',
    'It smells horrible!',
    'Oh no! What is that ungodly smell?!',
    ]


WEATHERS = [
    ('completely sunny', '\u2600\ufe0f'),
    ('not very cloudy', '\U0001f324\ufe0f'),
    ('partially cloudy', '\u26c5'),
    ('cloudy', '\U0001f325\ufe0f'),
    ('completely cloudy', '\u2601\ufe0f'),
    ('somewhat rainy', '\U0001f326\ufe0f'),
    ('rainy', '\U0001f327\ufe0f'),
    ('stormy', '\u26c8\ufe0f'),
    ('snowy', '\U0001f328\ufe0f'),
    ]


class Fish:
    """One fish instance."""

    def __init__(self, **kwargs):
        self.catch_time = kwargs.get('catch_time', datetime.utcnow())
        self.caught_by = kwargs.get('caught_by')
        self.size = kwargs.get('size')
        self.smell = kwargs.get('smell')
        self.species = kwargs.get('species')
        self.state = kwargs.get('state')
        self.owner_id = kwargs.get('owner_id')
        self.weight = kwargs.get('weight')


        self.species_str = get_fish_species_str(self.size, self.species)
        self.color = getattr(discord.Color,
                             FISH_SPECIES[self.size]['color'],
                             discord.Color.default)()

    @classmethod
    def from_random(cls, exp, weather, owner_id):
        """Create a fish randomly based on the weather."""

        rates = [cls._catch_rate(exp, weather, *size['rates'])
                 for size in FISH_SPECIES.values()]
        p = np.asarray(rates) / sum(rates)

        size = np.random.choice(list(FISH_SPECIES.keys()), p=p)
        species = np.random.randint(len(FISH_SPECIES[size]['species']))
        smell = np.random.randint(len(SMELLS))
        weight = np.random.uniform(*FISH_SPECIES[size]['weight'])

        return cls(
            caught_by=owner_id,
            size=size,
            species=species,
            smell=smell,
            weight=weight,
            owner_id=owner_id)

    @staticmethod
    def _catch_rate(exp, weather, r_min, r_max):
        """Defines the rate of catching a fish with.
        exp: The member's experience. Higher exp means better rate.
        weather: The current weather. The higher the value, the
                 higher the rates.
        r_min: The minimal catch rate. Is the value returned if exp = 0.
        r_max: The maximal catch rate. Is the value returned if exp -> infinity.
        """
        return r_min + (r_max - r_min) * (1 - np.exp(- weather * exp / 5e4))

    def to_embed(self):
        """Return a discord.Embed object to send in a discord.Message."""
        embed = discord.Embed(
            color=self.color,
            description=SMELLS[self.smell],
        ).add_field(
            name='Fish',
            value=f'{self.size.title()} {self.species_str}',
        ).add_field(
            name='Weight',
            value=f'{self.weight:.3f} kg',
        ).add_field(
            name='Caught By',
            value=f'<@{self.caught_by}>',
        )

        return embed

    def to_dict(self):
        """Convert to a DB friendly dict."""
        return {
            'catch_time': self.catch_time,
            'caught_by': self.caught_by,
            'size': self.size,
            'smell': self.smell,
            'species': self.species,
            'owner_id': self.owner_id,
            'weight': self.weight,
            }

    @classmethod
    def from_dict(cls, fish_dict):
        """Convert a dict form the DB to a class instance."""

        instance = cls(**fish_dict)
        instance.catch_time = datetime.fromisoformat(
            instance.catch_time)

        return instance

    def __repr__(self):
        return f'{self.size.title()} {self.species_str} ({self.weight:.3f} kg)'

    def __lt__(self, other):
        """Less than operator. Compare instances on the weight attribute."""
        return self.weight < other.weight


class Weather:
    """Define the weather for the day."""

    def __init__(self, state):
        state = min(state, len(WEATHERS) - 1)  # not above the limit
        state = max(state, 0)  # is above 0
        self.state = state

    @classmethod
    def from_random(cls):
        state = np.random.randint(len(WEATHERS))
        return cls(state)

    def __repr__(self):
        return '{0} {1}'.format(*WEATHERS[self.state])
