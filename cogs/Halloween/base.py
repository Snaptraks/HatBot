from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypedDict

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


TRICK_OR_TREAT_CHANNEL = 588171779957063680  # Bot Testing Server
