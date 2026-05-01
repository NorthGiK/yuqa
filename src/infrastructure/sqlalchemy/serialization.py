"""Serialization helpers for the persistent document store."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from src.battle_pass.domain.entities import (
    BattlePassProgress,
)
from src.battles.domain.entities import (
    Battle,
    BattleCardState,
    BattleSide,
    StatModifier,
)
from src.cards.domain.entities import PlayerCard
from src.clans.domain.entities import Clan
from src.infrastructure.local import (
    _banner_from_dict,
    _banner_to_dict,
    _battle_pass_season_from_dict,
    _battle_pass_season_to_dict,
    _card_from_dict,
    _card_to_dict,
    _dt,
    _idea_from_dict,
    _idea_to_dict,
    _parse_dt,
    _profile_background_from_dict,
    _profile_background_to_dict,
    _shop_from_dict,
    _shop_to_dict,
)
from src.players.domain.entities import Player
from src.shared.enums import AbilityStat, BattleStatus, CardForm
from src.shared.value_objects.deck_slots import DeckSlots
from src.shared.value_objects.resource_wallet import ResourceWallet


@dataclass(frozen=True, slots=True)
class SectionCodec:
    """Encode and decode one named document."""

    dump: Callable[[Any], Any]
    load: Callable[[Any], Any]


def _dt_or_now(value: str | None) -> datetime:
    """Parse a serialized timestamp or use the current UTC time."""

    return _parse_dt(value) or datetime.now(timezone.utc)


def _mapping_codec(
    dump_item: Callable[[Any], dict[str, Any]],
    load_item: Callable[[dict[str, Any]], Any],
    dump_key: Callable[[Any], str] = lambda value: str(value),
    load_key: Callable[[str], Any] = lambda value: int(value),
) -> SectionCodec:
    """Build a codec for mapping-based sections."""

    def dump(items: dict[Any, Any]) -> dict[str, Any]:
        return {dump_key(key): dump_item(item) for key, item in items.items()}

    def load(payload: Any) -> dict[Any, Any]:
        data = payload or {}
        return {load_key(key): load_item(value) for key, value in dict(data).items()}

    return SectionCodec(dump=dump, load=load)


def _list_codec(
    dump_item: Callable[[Any], Any] | None = None,
    load_item: Callable[[Any], Any] | None = None,
) -> SectionCodec:
    """Build a codec for list-based sections."""

    def dump(items: list[Any]) -> list[Any]:
        if dump_item is None:
            return list(items)
        return [dump_item(item) for item in items]

    def load(payload: Any) -> list[Any]:
        data = list(payload or [])
        if load_item is None:
            return data
        return [load_item(item) for item in data]

    return SectionCodec(dump=dump, load=load)


def _identity_dict_codec() -> SectionCodec:
    """Build a codec for plain dictionary payloads."""

    def dump(payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload)

    def load(payload: Any) -> dict[str, Any]:
        return dict(payload or {})

    return SectionCodec(dump=dump, load=load)


def _player_to_dict(player: Player) -> dict[str, Any]:
    """Serialize a player aggregate."""

    return {
        "telegram_id": player.telegram_id,
        "rating": player.rating,
        "is_banned": player.is_banned,
        "is_premium": player.is_premium,
        "created_at": _dt(player.created_at),
        "wins": player.wins,
        "losses": player.losses,
        "draws": player.draws,
        "wallet": {
            "coins": player.wallet.coins,
            "crystals": player.wallet.crystals,
            "orbs": player.wallet.orbs,
            "silver_tickets": player.wallet.silver_tickets,
            "gold_tickets": player.wallet.gold_tickets,
        },
        "collection_count": player.collection_count,
        "battle_deck": (
            list(player.battle_deck.card_ids)
            if player.battle_deck is not None
            else None
        ),
        "battle_pass_progress": list(player.battle_pass_progress),
        "clan_id": player.clan_id,
        "last_free_card_claim_at": _dt(player.last_free_card_claim_at),
        "last_free_resources_claim_at": _dt(player.last_free_resources_claim_at),
        "nickname": player.nickname,
        "title": player.title,
        "creator_points": player.creator_points,
        "owned_profile_background_ids": list(player.owned_profile_background_ids),
        "selected_profile_background_id": player.selected_profile_background_id,
    }


def _player_from_dict(data: dict[str, Any]) -> Player:
    """Deserialize a player aggregate."""

    wallet = data.get("wallet", {})
    deck = data.get("battle_deck")
    return Player(
        telegram_id=data["telegram_id"],
        rating=data.get("rating", 0),
        is_banned=data.get("is_banned", False),
        is_premium=data.get("is_premium", False),
        created_at=_dt_or_now(data.get("created_at")),
        wins=data.get("wins", 0),
        losses=data.get("losses", 0),
        draws=data.get("draws", 0),
        wallet=ResourceWallet(
            coins=wallet.get("coins", 0),
            crystals=wallet.get("crystals", 0),
            orbs=wallet.get("orbs", 0),
            silver_tickets=wallet.get("silver_tickets", 0),
            gold_tickets=wallet.get("gold_tickets", 0),
        ),
        collection_count=data.get("collection_count", 0),
        battle_deck=None if deck is None else DeckSlots(tuple(deck)),
        battle_pass_progress=list(data.get("battle_pass_progress", [])),
        clan_id=data.get("clan_id"),
        last_free_card_claim_at=_parse_dt(data.get("last_free_card_claim_at")),
        last_free_resources_claim_at=_parse_dt(
            data.get("last_free_resources_claim_at")
        ),
        nickname=data.get("nickname"),
        title=data.get("title"),
        creator_points=data.get("creator_points", 0),
        owned_profile_background_ids=list(data.get("owned_profile_background_ids", [])),
        selected_profile_background_id=data.get("selected_profile_background_id"),
    )


def _player_card_to_dict(card: PlayerCard) -> dict[str, Any]:
    """Serialize an owned card."""

    return {
        "id": card.id,
        "owner_player_id": card.owner_player_id,
        "template_id": card.template_id,
        "level": card.level,
        "copies_owned": card.copies_owned,
        "is_ascended": card.is_ascended,
        "current_form": card.current_form.value,
        "created_at": _dt(card.created_at),
        "updated_at": _dt(card.updated_at),
    }


def _player_card_from_dict(data: dict[str, Any]) -> PlayerCard:
    """Deserialize an owned card."""

    return PlayerCard(
        id=data["id"],
        owner_player_id=data["owner_player_id"],
        template_id=data["template_id"],
        level=data.get("level", 1),
        copies_owned=data.get("copies_owned", 1),
        is_ascended=data.get("is_ascended", False),
        current_form=CardForm(data.get("current_form", CardForm.BASE.value)),
        created_at=_dt_or_now(data.get("created_at")),
        updated_at=_dt_or_now(data.get("updated_at")),
    )


def _clan_to_dict(clan: Clan) -> dict[str, Any]:
    """Serialize a clan aggregate."""

    return {
        "id": clan.id,
        "owner_player_id": clan.owner_player_id,
        "name": clan.name,
        "icon": clan.icon,
        "rating": clan.rating,
        "min_entry_rating": clan.min_entry_rating,
        "members": sorted(clan.members),
        "blacklist": sorted(clan.blacklist),
        "created_at": _dt(clan.created_at),
    }


def _clan_from_dict(data: dict[str, Any]) -> Clan:
    """Deserialize a clan aggregate."""

    return Clan(
        id=data["id"],
        owner_player_id=data["owner_player_id"],
        name=data["name"],
        icon=data["icon"],
        rating=data.get("rating", 0),
        min_entry_rating=data.get("min_entry_rating", 0),
        members=set(data.get("members", [])),
        blacklist=set(data.get("blacklist", [])),
        created_at=_dt_or_now(data.get("created_at")),
    )


def _stat_modifier_to_dict(modifier: StatModifier) -> dict[str, Any]:
    """Serialize a battle modifier."""

    return {
        "stat": modifier.stat.value,
        "value": modifier.value,
        "remaining_rounds": modifier.remaining_rounds,
        "source_player_card_id": modifier.source_player_card_id,
    }


def _stat_modifier_from_dict(data: dict[str, Any]) -> StatModifier:
    """Deserialize a battle modifier."""

    return StatModifier(
        stat=AbilityStat(data["stat"]),
        value=data["value"],
        remaining_rounds=data["remaining_rounds"],
        source_player_card_id=data.get("source_player_card_id"),
    )


def _battle_card_state_to_dict(card: BattleCardState) -> dict[str, Any]:
    """Serialize one card snapshot inside a battle."""

    return {
        "player_card_id": card.player_card_id,
        "template": _card_to_dict(card.template),
        "form": card.form.value,
        "max_health": card.max_health,
        "current_health": card.current_health,
        "damage": card.damage,
        "defense": card.defense,
        "alive": card.alive,
        "effect_modifiers": [
            _stat_modifier_to_dict(item) for item in card.effect_modifiers
        ],
    }


def _battle_card_state_from_dict(data: dict[str, Any]) -> BattleCardState:
    """Deserialize one card snapshot inside a battle."""

    return BattleCardState(
        player_card_id=data["player_card_id"],
        template=_card_from_dict(data["template"]),
        form=CardForm(data["form"]),
        max_health=data["max_health"],
        current_health=data["current_health"],
        damage=data["damage"],
        defense=data["defense"],
        alive=data.get("alive", True),
        effect_modifiers=[
            _stat_modifier_from_dict(item) for item in data.get("effect_modifiers", [])
        ],
    )


def _battle_side_to_dict(side: BattleSide) -> dict[str, Any]:
    """Serialize a battle side."""

    return {
        "player_id": side.player_id,
        "active_card_id": side.active_card_id,
        "cards": [
            _battle_card_state_to_dict(card) for _, card in sorted(side.cards.items())
        ],
    }


def _battle_side_from_dict(data: dict[str, Any]) -> BattleSide:
    """Deserialize a battle side."""

    cards = [_battle_card_state_from_dict(item) for item in data.get("cards", [])]
    return BattleSide(
        player_id=data["player_id"],
        cards={card.player_card_id: card for card in cards},
        active_card_id=data["active_card_id"],
    )


def _battle_to_dict(battle: Battle) -> dict[str, Any]:
    """Serialize a battle aggregate."""

    return {
        "id": battle.id,
        "player_one_id": battle.player_one_id,
        "player_two_id": battle.player_two_id,
        "player_one_side": _battle_side_to_dict(battle.player_one_side),
        "player_two_side": _battle_side_to_dict(battle.player_two_side),
        "current_round": battle.current_round,
        "first_turn_player_id": battle.first_turn_player_id,
        "current_turn_player_id": battle.current_turn_player_id,
        "status": battle.status.value,
        "winner_id": battle.winner_id,
        "created_at": _dt(battle.created_at),
        "finished_at": _dt(battle.finished_at),
        "pending_enemy_effects": [
            {
                "target_card_id": target_card_id,
                "modifier": _stat_modifier_to_dict(modifier),
            }
            for target_card_id, modifier in battle.pending_enemy_effects
        ],
    }


def _battle_from_dict(data: dict[str, Any]) -> Battle:
    """Deserialize a battle aggregate."""

    return Battle(
        id=data["id"],
        player_one_id=data["player_one_id"],
        player_two_id=data["player_two_id"],
        player_one_side=_battle_side_from_dict(data["player_one_side"]),
        player_two_side=_battle_side_from_dict(data["player_two_side"]),
        current_round=data.get("current_round", 1),
        first_turn_player_id=data.get("first_turn_player_id"),
        current_turn_player_id=data.get("current_turn_player_id"),
        status=BattleStatus(data.get("status", BattleStatus.WAITING.value)),
        winner_id=data.get("winner_id"),
        created_at=_dt_or_now(data.get("created_at")),
        finished_at=_parse_dt(data.get("finished_at")),
        pending_enemy_effects=[
            (
                item["target_card_id"],
                _stat_modifier_from_dict(item["modifier"]),
            )
            for item in data.get("pending_enemy_effects", [])
        ],
    )


def _battle_pass_progress_key_to_str(value: tuple[int, int]) -> str:
    """Serialize a compound battle-pass-progress key."""

    return f"{value[0]}:{value[1]}"


def _battle_pass_progress_key_from_str(value: str) -> tuple[int, int]:
    """Deserialize a compound battle-pass-progress key."""

    player_id, season_id = value.split(":", maxsplit=1)
    return int(player_id), int(season_id)


def _battle_pass_progress_to_dict(progress: BattlePassProgress) -> dict[str, Any]:
    """Serialize battle pass progress."""

    return {
        "player_id": progress.player_id,
        "season_id": progress.season_id,
        "points": progress.points,
        "claimed_levels": sorted(progress.claimed_levels),
    }


def _battle_pass_progress_from_dict(data: dict[str, Any]) -> BattlePassProgress:
    """Deserialize battle pass progress."""

    return BattlePassProgress(
        player_id=data["player_id"],
        season_id=data["season_id"],
        points=data.get("points", 0),
        claimed_levels=set(data.get("claimed_levels", [])),
    )


def _search_queue_codec() -> SectionCodec:
    """Build a codec for the matchmaking queue."""

    def dump(items: dict[int, int]) -> dict[str, int]:
        return {str(player_id): rating for player_id, rating in items.items()}

    def load(payload: Any) -> dict[int, int]:
        return {
            int(player_id): int(rating)
            for player_id, rating in dict(payload or {}).items()
        }

    return SectionCodec(dump=dump, load=load)


def _deck_drafts_codec() -> SectionCodec:
    """Build a codec for deck draft state."""

    def dump(items: dict[int, list[int]]) -> dict[str, list[int]]:
        return {str(player_id): list(cards) for player_id, cards in items.items()}

    def load(payload: Any) -> dict[int, list[int]]:
        return {
            int(player_id): list(cards)
            for player_id, cards in dict(payload or {}).items()
        }

    return SectionCodec(dump=dump, load=load)


def _action_events_codec() -> SectionCodec:
    """Build a codec for recent player actions."""

    def dump(events: list[tuple[int, str]]) -> list[dict[str, Any]]:
        return [
            {"player_id": player_id, "action": action} for player_id, action in events
        ]

    def load(payload: Any) -> list[tuple[int, str]]:
        return [
            (int(item["player_id"]), str(item["action"]))
            for item in list(payload or [])
        ]

    return SectionCodec(dump=dump, load=load)


SECTION_CODECS: dict[str, SectionCodec] = {
    "players": _mapping_codec(_player_to_dict, _player_from_dict),
    "player_cards": _mapping_codec(_player_card_to_dict, _player_card_from_dict),
    "cards": _mapping_codec(_card_to_dict, _card_from_dict),
    "profile_backgrounds": _mapping_codec(
        _profile_background_to_dict,
        _profile_background_from_dict,
    ),
    "clans": _mapping_codec(_clan_to_dict, _clan_from_dict),
    "banners": _mapping_codec(_banner_to_dict, _banner_from_dict),
    "shop_items": _mapping_codec(_shop_to_dict, _shop_from_dict),
    "battle_pass_seasons": _mapping_codec(
        _battle_pass_season_to_dict,
        _battle_pass_season_from_dict,
    ),
    "premium_battle_pass_seasons": _mapping_codec(
        _battle_pass_season_to_dict,
        _battle_pass_season_from_dict,
    ),
    "battle_pass_progress": _mapping_codec(
        _battle_pass_progress_to_dict,
        _battle_pass_progress_from_dict,
        dump_key=_battle_pass_progress_key_to_str,
        load_key=_battle_pass_progress_key_from_str,
    ),
    "premium_battle_pass_progress": _mapping_codec(
        _battle_pass_progress_to_dict,
        _battle_pass_progress_from_dict,
        dump_key=_battle_pass_progress_key_to_str,
        load_key=_battle_pass_progress_key_from_str,
    ),
    "battles": _mapping_codec(_battle_to_dict, _battle_from_dict),
    "ideas": _mapping_codec(_idea_to_dict, _idea_from_dict),
    "standard_cards": _list_codec(),
    "universes": _list_codec(),
    "free_rewards": _identity_dict_codec(),
    "search_queue": _search_queue_codec(),
    "deck_drafts": _deck_drafts_codec(),
    "action_events": _action_events_codec(),
}

CATALOG_SECTIONS = (
    "cards",
    "profile_backgrounds",
    "banners",
    "shop_items",
    "battle_pass_seasons",
    "premium_battle_pass_seasons",
    "ideas",
    "standard_cards",
    "universes",
    "free_rewards",
)

RUNTIME_SECTIONS = (
    "players",
    "player_cards",
    "clans",
    "battle_pass_progress",
    "premium_battle_pass_progress",
    "battles",
    "search_queue",
    "deck_drafts",
    "action_events",
)
