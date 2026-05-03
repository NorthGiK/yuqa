"""Battle ORM models."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.sqlalchemy.base import Base
from src.infrastructure.sqlalchemy.models.common import _now


class BattleORM(Base):
    """Persisted battle row."""

    __tablename__ = "battles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_one_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    player_two_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    winner_id: Mapped[int | None] = mapped_column(Integer, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
