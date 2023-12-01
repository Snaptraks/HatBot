from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


SQL = Path(__file__).parent / "sql"

GIVEAWAY_TIME = timedelta(hours=24)
# GIVEAWAY_TIME = timedelta(seconds=60)
EMBED_COLOR = 0xB3000C

HVC_STAFF_ROLES = [
    308050057977135114,  # Admin
    308053679796387851,  # Dev
    589237207005397161,  # Discord Tech
    308050309312151552,  # Mod
    588846761758425089,  # BTS Discord Tech
]

HVC_MC_SERVER_CHATTER = 561313326231978009  # #mc-server-chatter channel ID


@dataclass
class Game:
    game_id: int
    given: bool = field(repr=False)
    key: str = field(repr=False)
    title: str
    url: str = field(repr=False)

    @property
    def title_link(self) -> str:
        return f"[{self.title}]({self.url})"


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
