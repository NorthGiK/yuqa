"""Create relational state tables.

Revision ID: 20260503_0002
Revises: 20260411_0001
Create Date: 2026-05-03 00:00:00.000000
"""

from collections.abc import Sequence
from datetime import datetime, timezone
import json

from alembic import op
import sqlalchemy as sa


revision: str = "20260503_0002"
down_revision: str | None = "20260411_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _updated_at_column() -> sa.Column[sa.DateTime]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def _payload_column() -> sa.Column[sa.JSON]:
    return sa.Column("payload", sa.JSON(), nullable=False)


def _json_payload(value):
    """Decode JSON values returned as strings by some database drivers."""

    if isinstance(value, str):
        return json.loads(value)
    return value


def _datetime(value):
    """Parse serialized datetimes before inserting DateTime columns."""

    if value is None or isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _table(name: str, *columns: str) -> sa.Table:
    typed_columns = []
    for column in columns:
        if column == "payload":
            typed_columns.append(sa.column(column, sa.JSON()))
        elif column in {"start_at", "end_at", "cooldown_until"}:
            typed_columns.append(sa.column(column, sa.DateTime(timezone=True)))
        elif column.startswith("is_") or column in {"completed"}:
            typed_columns.append(sa.column(column, sa.Boolean()))
        else:
            typed_columns.append(sa.column(column))
    return sa.table(name, *typed_columns)


def _bulk(table: sa.Table, rows: list[dict]) -> None:
    if rows:
        op.bulk_insert(table, rows)


def _migrate_legacy_state_documents() -> None:
    """Copy old JSON sections into relational tables before dropping them."""

    bind = op.get_bind()
    if not sa.inspect(bind).has_table("state_documents"):
        return

    documents = {
        row["name"]: _json_payload(row["payload"])
        for row in bind.execute(
            sa.text("SELECT name, payload FROM state_documents")
        ).mappings()
    }
    if not documents:
        return

    players = documents.get("players") or {}
    _bulk(
        _table(
            "players",
            "telegram_id",
            "nickname",
            "rating",
            "clan_id",
            "is_banned",
            "is_premium",
            "payload",
        ),
        [
            {
                "telegram_id": int(player_id),
                "nickname": data.get("nickname"),
                "rating": data.get("rating", 0),
                "clan_id": data.get("clan_id"),
                "is_banned": data.get("is_banned", False),
                "is_premium": data.get("is_premium", False),
                "payload": data,
            }
            for player_id, data in dict(players).items()
        ],
    )

    player_cards = documents.get("player_cards") or {}
    _bulk(
        _table(
            "player_cards",
            "id",
            "owner_player_id",
            "template_id",
            "level",
            "copies_owned",
            "payload",
        ),
        [
            {
                "id": int(card_id),
                "owner_player_id": data["owner_player_id"],
                "template_id": data["template_id"],
                "level": data.get("level", 1),
                "copies_owned": data.get("copies_owned", 1),
                "payload": data,
            }
            for card_id, data in dict(player_cards).items()
        ],
    )

    cards = documents.get("cards") or {}
    _bulk(
        _table(
            "card_templates",
            "id",
            "name",
            "universe",
            "rarity",
            "is_available",
            "payload",
        ),
        [
            {
                "id": int(template_id),
                "name": data["name"],
                "universe": data["universe"],
                "rarity": data["rarity"],
                "is_available": data.get("is_available", True),
                "payload": data,
            }
            for template_id, data in dict(cards).items()
        ],
    )

    backgrounds = documents.get("profile_backgrounds") or {}
    _bulk(
        _table("profile_backgrounds", "id", "rarity", "storage_key", "payload"),
        [
            {
                "id": int(background_id),
                "rarity": data["rarity"],
                "storage_key": data["media"]["storage_key"],
                "payload": data,
            }
            for background_id, data in dict(backgrounds).items()
        ],
    )

    clans = documents.get("clans") or {}
    _bulk(
        _table("clans", "id", "owner_player_id", "name", "rating", "payload"),
        [
            {
                "id": int(clan_id),
                "owner_player_id": data["owner_player_id"],
                "name": data["name"],
                "rating": data.get("rating", 0),
                "payload": data,
            }
            for clan_id, data in dict(clans).items()
        ],
    )

    banners = documents.get("banners") or {}
    _bulk(
        _table(
            "banners",
            "id",
            "name",
            "banner_type",
            "cost_resource",
            "is_active",
            "start_at",
            "end_at",
            "payload",
        ),
        [
            {
                "id": int(banner_id),
                "name": data["name"],
                "banner_type": data["banner_type"],
                "cost_resource": data["cost_resource"],
                "is_active": data.get("is_active", True),
                "start_at": _datetime(data.get("date_range", {}).get("start_at")),
                "end_at": _datetime(data.get("date_range", {}).get("end_at")),
                "payload": data,
            }
            for banner_id, data in dict(banners).items()
        ],
    )

    shop_items = documents.get("shop_items") or {}
    _bulk(
        _table(
            "shop_items",
            "id",
            "sell_resource_type",
            "buy_resource_type",
            "price",
            "quantity",
            "is_active",
            "payload",
        ),
        [
            {
                "id": int(item_id),
                "sell_resource_type": data["sell_resource_type"],
                "buy_resource_type": data["buy_resource_type"],
                "price": data["price"],
                "quantity": data["quantity"],
                "is_active": data.get("is_active", True),
                "payload": data,
            }
            for item_id, data in dict(shop_items).items()
        ],
    )

    ideas = documents.get("ideas") or {}
    _bulk(
        _table(
            "ideas",
            "id",
            "player_id",
            "status",
            "upvotes",
            "downvotes",
            "payload",
        ),
        [
            {
                "id": int(idea_id),
                "player_id": data["player_id"],
                "status": data.get("status", "pending"),
                "upvotes": sum(
                    1 for value in dict(data.get("votes", {})).values() if value > 0
                ),
                "downvotes": sum(
                    1 for value in dict(data.get("votes", {})).values() if value < 0
                ),
                "payload": data,
            }
            for idea_id, data in dict(ideas).items()
        ],
    )

    for section, table_name in (
        ("battle_pass_seasons", "battle_pass_seasons"),
        ("premium_battle_pass_seasons", "premium_battle_pass_seasons"),
    ):
        seasons = documents.get(section) or {}
        _bulk(
            _table(
                table_name,
                "id",
                "name",
                "start_at",
                "end_at",
                "is_active",
                "payload",
            ),
            [
                {
                    "id": int(season_id),
                    "name": data["name"],
                    "start_at": _datetime(data["start_at"]),
                    "end_at": _datetime(data["end_at"]),
                    "is_active": data.get("is_active", True),
                    "payload": data,
                }
                for season_id, data in dict(seasons).items()
            ],
        )

    for section, table_name in (
        ("battle_pass_progress", "battle_pass_progress"),
        ("premium_battle_pass_progress", "premium_battle_pass_progress"),
    ):
        progress_items = documents.get(section) or {}
        _bulk(
            _table(table_name, "player_id", "season_id", "points", "payload"),
            [
                {
                    "player_id": data["player_id"],
                    "season_id": data["season_id"],
                    "points": data.get("points", 0),
                    "payload": data,
                }
                for data in dict(progress_items).values()
            ],
        )

    definitions = documents.get("quest_definitions") or {}
    _bulk(
        _table(
            "quest_definitions",
            "id",
            "period",
            "action_type",
            "cooldown_seconds",
            "is_active",
            "payload",
        ),
        [
            {
                "id": int(definition_id),
                "period": data.get("period", "daily"),
                "action_type": data["action_type"],
                "cooldown_seconds": data.get("cooldown_seconds", 0),
                "is_active": data.get("is_active", True),
                "payload": data,
            }
            for definition_id, data in dict(definitions).items()
        ],
    )

    quest_progress = documents.get("quest_progress") or {}
    _bulk(
        _table(
            "quest_progress",
            "player_id",
            "quest_id",
            "completed",
            "completed_count",
            "cooldown_until",
            "payload",
        ),
        [
            {
                "player_id": data["player_id"],
                "quest_id": data["quest_id"],
                "completed": data.get("completed", False),
                "completed_count": data.get("completed_count", 0),
                "cooldown_until": _datetime(data.get("cooldown_until")),
                "payload": data,
            }
            for data in dict(quest_progress).values()
        ],
    )

    battles = documents.get("battles") or {}
    _bulk(
        _table(
            "battles",
            "id",
            "player_one_id",
            "player_two_id",
            "status",
            "winner_id",
            "payload",
        ),
        [
            {
                "id": int(battle_id),
                "player_one_id": data["player_one_id"],
                "player_two_id": data["player_two_id"],
                "status": data.get("status", "waiting"),
                "winner_id": data.get("winner_id"),
                "payload": data,
            }
            for battle_id, data in dict(battles).items()
        ],
    )

    _bulk(
        _table("standard_cards", "position", "card_template_id"),
        [
            {"position": position, "card_template_id": card_id}
            for position, card_id in enumerate(documents.get("standard_cards") or [])
        ],
    )
    _bulk(
        _table("universes", "position", "value"),
        [
            {"position": position, "value": value}
            for position, value in enumerate(
                dict.fromkeys(documents.get("universes") or [])
            )
        ],
    )
    free_rewards = documents.get("free_rewards") or {}
    _bulk(
        _table("free_reward_config", "name", "payload"),
        [{"name": "free_rewards", "payload": free_rewards}] if free_rewards else [],
    )
    _bulk(
        _table("search_queue", "player_id", "rating"),
        [
            {"player_id": int(player_id), "rating": int(rating)}
            for player_id, rating in dict(documents.get("search_queue") or {}).items()
        ],
    )
    deck_rows = []
    for player_id, card_ids in dict(documents.get("deck_drafts") or {}).items():
        for position, card_id in enumerate(card_ids):
            deck_rows.append(
                {
                    "player_id": int(player_id),
                    "position": position,
                    "card_id": card_id,
                }
            )
    _bulk(_table("deck_draft_cards", "player_id", "position", "card_id"), deck_rows)
    _bulk(
        _table("action_events", "position", "player_id", "action"),
        [
            {
                "position": position,
                "player_id": event["player_id"],
                "action": event["action"],
            }
            for position, event in enumerate(documents.get("action_events") or [])
        ],
    )


def upgrade() -> None:
    """Create normalized runtime and catalog tables."""

    op.create_table(
        "players",
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("nickname", sa.String(length=24), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("clan_id", sa.Integer(), nullable=True),
        sa.Column("is_banned", sa.Boolean(), nullable=False),
        sa.Column("is_premium", sa.Boolean(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("telegram_id"),
        sa.UniqueConstraint("nickname"),
    )
    op.create_index("ix_players_rating", "players", ["rating"])
    op.create_index("ix_players_clan_id", "players", ["clan_id"])

    op.create_table(
        "player_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_player_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("copies_owned", sa.Integer(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_cards_owner_player_id", "player_cards", ["owner_player_id"])
    op.create_index("ix_player_cards_template_id", "player_cards", ["template_id"])

    op.create_table(
        "card_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("universe", sa.String(length=64), nullable=False),
        sa.Column("rarity", sa.String(length=32), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_templates_universe", "card_templates", ["universe"])
    op.create_index("ix_card_templates_rarity", "card_templates", ["rarity"])
    op.create_index("ix_card_templates_is_available", "card_templates", ["is_available"])

    op.create_table(
        "profile_backgrounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rarity", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profile_backgrounds_rarity", "profile_backgrounds", ["rarity"])

    op.create_table(
        "clans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_player_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clans_owner_player_id", "clans", ["owner_player_id"])
    op.create_index("ix_clans_rating", "clans", ["rating"])

    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("banner_type", sa.String(length=32), nullable=False),
        sa.Column("cost_resource", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banners_banner_type", "banners", ["banner_type"])
    op.create_index("ix_banners_is_active", "banners", ["is_active"])

    op.create_table(
        "shop_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sell_resource_type", sa.String(length=32), nullable=False),
        sa.Column("buy_resource_type", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shop_items_is_active", "shop_items", ["is_active"])

    op.create_table(
        "ideas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("upvotes", sa.Integer(), nullable=False),
        sa.Column("downvotes", sa.Integer(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ideas_player_id", "ideas", ["player_id"])
    op.create_index("ix_ideas_status", "ideas", ["status"])

    for table_name in ("battle_pass_seasons", "premium_battle_pass_seasons"):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            _payload_column(),
            _updated_at_column(),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(f"ix_{table_name}_start_at", table_name, ["start_at"])
        op.create_index(f"ix_{table_name}_end_at", table_name, ["end_at"])
        op.create_index(f"ix_{table_name}_is_active", table_name, ["is_active"])

    for table_name in ("battle_pass_progress", "premium_battle_pass_progress"):
        op.create_table(
            table_name,
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season_id", sa.Integer(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False),
            _payload_column(),
            _updated_at_column(),
            sa.PrimaryKeyConstraint("player_id", "season_id"),
        )

    op.create_table(
        "quest_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quest_definitions_period", "quest_definitions", ["period"])
    op.create_index(
        "ix_quest_definitions_action_type",
        "quest_definitions",
        ["action_type"],
    )
    op.create_index(
        "ix_quest_definitions_is_active",
        "quest_definitions",
        ["is_active"],
    )

    op.create_table(
        "quest_progress",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("quest_id", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("player_id", "quest_id"),
    )
    op.create_index("ix_quest_progress_cooldown_until", "quest_progress", ["cooldown_until"])

    op.create_table(
        "battles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_one_id", sa.Integer(), nullable=False),
        sa.Column("player_two_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        _payload_column(),
        _updated_at_column(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_battles_player_one_id", "battles", ["player_one_id"])
    op.create_index("ix_battles_player_two_id", "battles", ["player_two_id"])
    op.create_index("ix_battles_status", "battles", ["status"])
    op.create_index("ix_battles_winner_id", "battles", ["winner_id"])

    op.create_table(
        "standard_cards",
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("card_template_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("position"),
    )
    op.create_table(
        "universes",
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("position"),
        sa.UniqueConstraint("value"),
    )
    op.create_table(
        "free_reward_config",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "search_queue",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("player_id"),
    )
    op.create_table(
        "deck_draft_cards",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("player_id", "position"),
    )
    op.create_table(
        "action_events",
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("position"),
    )

    _migrate_legacy_state_documents()
    if sa.inspect(op.get_bind()).has_table("state_documents"):
        op.drop_table("state_documents")


def downgrade() -> None:
    """Drop relational runtime and catalog tables."""

    for table_name in (
        "action_events",
        "deck_draft_cards",
        "search_queue",
        "free_reward_config",
        "universes",
        "standard_cards",
        "battles",
        "quest_progress",
        "quest_definitions",
        "premium_battle_pass_progress",
        "battle_pass_progress",
        "premium_battle_pass_seasons",
        "battle_pass_seasons",
        "ideas",
        "shop_items",
        "banners",
        "clans",
        "profile_backgrounds",
        "card_templates",
        "player_cards",
        "players",
    ):
        op.drop_table(table_name)

    op.create_table(
        "state_documents",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("name"),
    )
