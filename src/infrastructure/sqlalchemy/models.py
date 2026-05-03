"""SQLAlchemy models used by the persistent relational store."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.sqlalchemy.base import Base


def _now() -> datetime:
    """Return a timezone-aware timestamp for new rows."""

    return datetime.now(timezone.utc)


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
