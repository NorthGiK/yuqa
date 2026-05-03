"""Player-related ORM models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.sqlalchemy.base import Base
from src.infrastructure.sqlalchemy.models.common import _now


class PlayerORM(Base):
    """Player profile row."""

    __tablename__ = "players"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str | None] = mapped_column(String(24), unique=True, index=True)
    rating: Mapped[int] = mapped_column(Integer, index=True, nullable=False, default=0)
    clan_id: Mapped[int | None] = mapped_column(Integer, index=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class PlayerCardORM(Base):
    """Player-owned card row."""

    __tablename__ = "player_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_player_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    template_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    copies_owned: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class ProfileBackgroundORM(Base):
    """Profile background template row."""

    __tablename__ = "profile_backgrounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rarity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class ClanORM(Base):
    """Clan aggregate row."""

    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_player_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, index=True, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
