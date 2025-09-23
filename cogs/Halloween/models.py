from snapcogs.database import Base
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class HalloweenBase(Base):
    __abstract__ = True

    guild_id: Mapped[int]
    user_id: Mapped[int]


class TrickOrTreaterLog(HalloweenBase):
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

    display_name: Mapped[str]
