"""Battle pass and quest ORM models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.sqlalchemy.base import Base
from src.infrastructure.sqlalchemy.models.common import _now


class BattlePassSeasonORM(Base):
    """Free battle pass season row."""

    __tablename__ = "battle_pass_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class PremiumBattlePassSeasonORM(Base):
    """Premium battle pass season row."""

    __tablename__ = "premium_battle_pass_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class BattlePassProgressORM(Base):
    """Free battle pass progress row."""

    __tablename__ = "battle_pass_progress"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class PremiumBattlePassProgressORM(Base):
    """Premium battle pass progress row."""

    __tablename__ = "premium_battle_pass_progress"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class QuestDefinitionORM(Base):
    """Quest definition row."""

    __tablename__ = "quest_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class QuestProgressORM(Base):
    """Per-player quest progress row."""

    __tablename__ = "quest_progress"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quest_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
