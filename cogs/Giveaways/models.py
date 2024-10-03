from datetime import datetime

from snapcogs.database import Base
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class View(Base):
    __tablename__ = "giveaways_view"

    guild_id: Mapped[int]
    message_id: Mapped[int] = mapped_column(unique=True)

    components: Mapped[list["Component"]] = relationship(back_populates="view")


class Component(Base):
    __tablename__ = "giveaways_component"

    name: Mapped[str]
    component_id: Mapped[str]
    view_id: Mapped[int] = mapped_column(
        ForeignKey("giveaways_view.id", ondelete="CASCADE")
    )

    view: Mapped["View"] = relationship(back_populates="components")


class Game(Base):
    __tablename__ = "giveaways_game"

    key: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    url: Mapped[str]
    given: Mapped[bool] = mapped_column(default=False)

    @property
    def title_link(self) -> str:
        return f"[{self.title}]({self.url})"


class Giveaway(Base):
    __tablename__ = "giveaways_giveaway"

    channel_id: Mapped[int | None]
    created_at: Mapped[datetime | None]
    game_id: Mapped[int] = mapped_column(ForeignKey("giveaways_game.id"))
    is_done: Mapped[bool] = mapped_column(default=False)
    message_id: Mapped[int | None]
    trigger_at: Mapped[datetime]

    game: Mapped["Game"] = relationship()


class Entry(Base):
    __tablename__ = "giveaways_entry"
    __table_args__ = (UniqueConstraint("giveaway_id", "user_id"),)

    user_id: Mapped[int]
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways_giveaway.id"))
