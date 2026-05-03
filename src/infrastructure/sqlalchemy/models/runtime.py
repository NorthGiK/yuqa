"""Runtime and maintenance ORM models."""

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.sqlalchemy.base import Base


class StandardCardORM(Base):
    """Ordered starter-card reference."""

    __tablename__ = "standard_cards"

    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_template_id: Mapped[int] = mapped_column(Integer, nullable=False)


class UniverseORM(Base):
    """Ordered universe catalog value."""

    __tablename__ = "universes"

    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class FreeRewardConfigORM(Base):
    """Free reward configuration row."""

    __tablename__ = "free_reward_config"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class SearchQueueORM(Base):
    """Matchmaking queue row."""

    __tablename__ = "search_queue"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)


class DeckDraftCardORM(Base):
    """Ordered deck draft card row."""

    __tablename__ = "deck_draft_cards"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)


class ActionEventORM(Base):
    """Recent action event row."""

    __tablename__ = "action_events"

    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
