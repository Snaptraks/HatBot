from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from discord.app_commands import AppCommandError

if TYPE_CHECKING:
    from .models import TreatCount

    type Inventory = list[TreatCount]

    class Rarity(TypedDict):
        common: int
        uncommon: int
        rare: int

    class TrickOrTreater(TypedDict):
        name: str
        image: str
        common: str
        uncommon: str
        rare: str

    class BaseLoot(TypedDict):
        name: str
        rarity: str

    class CursedNames(TypedDict):
        first_names: list[str]
        last_names: list[str]
        emojis: list[str]


@dataclass(frozen=True)
class BaseTreat:
    name: str
    emoji: str

    def __str__(self) -> str:
        return f"{self.emoji} {self.name}"


class DuplicateLootError(AppCommandError):
    pass


RARITY = ["common", "uncommon", "rare"]

# will have a chance of 1 over the value
TRICK_OR_TREATER_SPAWN_RATE = 30

# will have a 100*value % chance of spawning
TREAT_SPAWN_RATE = 0.75

TRICK_OR_TREATER_LENGTH = 3  # minutes
CURSE_LENGTH = 15  # minutes

TRICK_OR_TREAT_CHANNEL = 766092475902853131  # Hatventures Community
# TRICK_OR_TREAT_CHANNEL = 588171779957063680  # Bot Testing Server


def random_integer(max_value: int) -> int:
    """Return a random integer between 1 and max_value.

    Parameters
    ----------
    max_value : int
        The maximum value of the random integer

    Returns
    -------
    int
        The random integer

    """
    return random.randint(1, max_value)


def fmt_loot(loot: BaseLoot) -> str:
    """Format the loot intem into a nice string.

    Parameters
    ----------
    loot : BaseLoot
        The loot item to get a nice string from.

    Returns
    -------
    str
        The nice string representing the loot item.

    """
    return f"{loot['rarity'].title()} {loot['name']}"
