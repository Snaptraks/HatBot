from snapcogs.database import Base
from sqlalchemy.orm import Mapped


class HalloweenBase(Base):
    __abstract__ = True

    guild_id: Mapped[int]
    user_id: Mapped[int]


class Loot(HalloweenBase):
    __tablename__ = "halloween_loot"

    name: Mapped[str]
    rarity: Mapped[str]


class Treat(HalloweenBase):
    __tablename__ = "halloween_treat"

    name: Mapped[str]
    emoji: Mapped[str]


class OriginalName(HalloweenBase):
    __tablename__ = "halloween_original_name"

    display_name: Mapped[str]
