import datetime
from enum import Enum, auto

from snapcogs.database import Base
from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class Event(Enum):
    GIVE_TREAT = auto()
    COLLECT_TREAT = auto()
    REQUESTED_TREAT = auto()
    NOT_REQUESTED_TREAT = auto()
    GET_CURSE = auto()
    SPAWN_TRICK_OR_TREATER = auto()


class HalloweenBase(Base):
    __abstract__ = True

    guild_id: Mapped[int]
    user_id: Mapped[int]


class TrickOrTreaterMessage(HalloweenBase):
    __tablename__ = "halloween_trick_or_treater_log"

    message_id: Mapped[int]


class Loot(HalloweenBase):
    __tablename__ = "halloween_loot"
    __table_args__ = (UniqueConstraint("guild_id", "user_id", "name"),)

    name: Mapped[str]
    rarity: Mapped[str]


class TreatCount(HalloweenBase):
    __tablename__ = "halloween_treat_count"

    name: Mapped[str]
    emoji: Mapped[str]
    amount: Mapped[int] = mapped_column(default=0)


class OriginalName(HalloweenBase):
    __tablename__ = "halloween_original_name"
    __table_args__ = (UniqueConstraint("guild_id", "user_id"),)

    display_name: Mapped[str]


class EventLog(Base):
    __tablename__ = "halloween_event_log"

    guild_id: Mapped[int]
    user_id: Mapped[int | None]
    event: Mapped[Event]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
