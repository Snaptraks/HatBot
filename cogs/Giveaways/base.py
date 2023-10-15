from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


SQL = Path(__file__).parent / "sql"

# GIVEAWAY_TIME = timedelta(hours=24)
GIVEAWAY_TIME = timedelta(seconds=60)
EMBED_COLOR = 0xB3000C


@dataclass
class Game:
    game_id: int
    given: bool = field(repr=False)
    key: str = field(repr=False)
    title: str
    url: str = field(repr=False)


@dataclass
class Giveaway:
    giveaway_id: int
    channel_id: int = field(repr=False)
    created_at: datetime = field(repr=False)
    game: Game
    game_id: int = field(repr=False)
    is_done: bool = field(repr=False)
    message_id: int = field(repr=False)
    trigger_at: datetime
