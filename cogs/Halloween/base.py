from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .models import TreatCount

    type Inventory = list[TreatCount]

    class LootRates(TypedDict):
        common: int
        uncommon: int
        rare: int

    class TrickOrTreater(TypedDict):
        name: str
        image: str
        common: str
        uncommon: str
        rare: str


@dataclass(frozen=True)
class BaseTreat:
    name: str
    emoji: str


TRICK_OR_TREAT_CHANNEL = 588171779957063680  # Bot Testing Server
