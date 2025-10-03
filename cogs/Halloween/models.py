import datetime
from enum import Enum, auto

from snapcogs.database import Base
from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class Event(Enum):
    CLAIM_FREE_TREATS = auto()
    GIVE_TREAT = auto()
    COLLECT_TREAT = auto()
    REQUESTED_TREAT = auto()
    NOT_REQUESTED_TREAT = auto()
    COLLECT_LOOT = auto()
    GET_CURSE = auto()
    SPAWN_TRICK_OR_TREATER = auto()


class HalloweenBase(Base):
    __abstract__ = True

    guild_id: Mapped[int]
    user_id: Mapped[int]


class TrickOrTreaterMessage(HalloweenBase):
    """The message containing a trick-or-treater that a member has given a treat to."""

    __tablename__ = "halloween_trick_or_treater_log"

    message_id: Mapped[int]


class Loot(HalloweenBase):
    """The loot that a member has."""

    __tablename__ = "halloween_loot"
    __table_args__ = (UniqueConstraint("guild_id", "user_id", "name"),)

    name: Mapped[str]
    rarity: Mapped[str]


class TreatCount(HalloweenBase):
    """The number of treats a member has."""

    __tablename__ = "halloween_treat_count"

    name: Mapped[str]
    emoji: Mapped[str]
    amount: Mapped[int] = mapped_column(default=0)


class OriginalName(HalloweenBase):
    """The display name a member has at the begining of the event."""

    __tablename__ = "halloween_original_name"
    __table_args__ = (UniqueConstraint("guild_id", "user_id"),)

    display_name: Mapped[str]


class EventLog(Base):
    """A record of an event that happened."""

    __tablename__ = "halloween_event_log"

    guild_id: Mapped[int]
    user_id: Mapped[int | None]
    event: Mapped[Event]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
