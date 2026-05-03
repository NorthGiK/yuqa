"""Catalog and content ORM models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.sqlalchemy.base import Base
from src.infrastructure.sqlalchemy.models.common import _now


class CardTemplateORM(Base):
    """Admin-created card template row."""

    __tablename__ = "card_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    universe: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rarity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class BannerORM(Base):
    """Banner row with queryable availability columns."""

    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    banner_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    cost_resource: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class ShopItemORM(Base):
    """Shop item row."""

    __tablename__ = "shop_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sell_resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    buy_resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class IdeaORM(Base):
    """Player-submitted idea row."""

    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
