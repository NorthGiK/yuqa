"""Reusable parsing and lookup helpers for the Telegram router."""

from datetime import datetime, timezone

from src.players.domain.entities import ProfileBackgroundTemplate
from src.cards.domain.entities import AbilityEffect
from src.cards.domain.entities import CardTemplate
from src.quests.domain.entities import QuestReward
from src.shared.enums import AbilityStat, AbilityTarget
from src.shared.errors import ValidationError
from src.telegram.compat import Message


def _parse_int(text: str, label: str, *, positive: bool = False) -> int:
    """Parse an integer with friendly validation errors."""

    try:
        value = int((text or "").strip())
    except ValueError as error:
        raise ValidationError(f"{label} must be an integer") from error
    if positive and value <= 0:
        raise ValidationError(f"{label} must be > 0")
    if not positive and value < 0:
        raise ValidationError(f"{label} must be >= 0")
    return value


def _parse_dt(text: str) -> datetime | None:
    """Parse ISO datetime or a blank marker."""

    text = (text or "").strip()
    if text in {"", "-", "none", "нет"}:
        return None
    value = datetime.fromisoformat(text)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _normalize_token(value: str) -> str:
    """Normalize a free-form token for enum lookup."""

    return "".join(ch for ch in value.lower() if ch.isalnum())


def _parse_effects(text: str) -> tuple[AbilityEffect, ...]:
    """Parse a readable list of ability effects."""

    text = (text or "").strip()
    if text in {"", "-", "none", "нет"}:
        return ()
    targets = {
        "self": AbilityTarget.SELF,
        "teammatesdeck": AbilityTarget.TEAMMATES_DECK,
        "teammates": AbilityTarget.TEAMMATES_DECK,
        "team": AbilityTarget.TEAMMATES_DECK,
        "allydeck": AbilityTarget.TEAMMATES_DECK,
        "opponentsdeck": AbilityTarget.OPPONENTS_DECK,
        "opponentdeck": AbilityTarget.OPPONENTS_DECK,
        "enemydeck": AbilityTarget.OPPONENTS_DECK,
        "opponent": AbilityTarget.OPPONENTS_DECK,
        "enemy": AbilityTarget.OPPONENTS_DECK,
    }
    stats = {
        "damage": AbilityStat.DAMAGE,
        "health": AbilityStat.HEALTH,
        "defense": AbilityStat.DEFENSE,
    }
    effects = []
    for chunk in text.replace("\n", ";").split(";"):
        chunk = chunk.strip().lstrip("•*- ")
        if not chunk or chunk in {"-", "none", "нет"}:
            continue
        parts = [part.strip() for part in chunk.split(":")]
        if len(parts) != 4:
            raise ValidationError(
                f"effect must have 4 parts: target:stat:duration:value, got '{chunk}'"
            )
        target_raw, stat_raw, duration_raw, value_raw = parts
        try:
            target = targets[_normalize_token(target_raw)]
        except KeyError as error:
            raise ValidationError(f"unknown target '{target_raw}'") from error
        try:
            stat = stats[_normalize_token(stat_raw)]
        except KeyError as error:
            raise ValidationError(f"unknown stat '{stat_raw}'") from error
        duration = _parse_int(duration_raw, "duration")
        try:
            value = int(value_raw)
        except ValueError as error:
            raise ValidationError("value must be an integer") from error
        if value == 0:
            raise ValidationError("value must not be 0")
        effects.append(AbilityEffect(target, stat, duration, value))
    return tuple(effects)


def _parse_reward_bundle(text: str) -> QuestReward:
    """Parse a simple battle pass reward bundle from three integers."""

    values = [part for part in (text or "").replace(",", " ").split() if part]
    if len(values) != 3:
        raise ValidationError("reward must contain three integers: coins crystals orbs")
    coins, crystals, orbs = (_parse_int(value, "reward value") for value in values)
    return QuestReward(coins=coins, crystals=crystals, orbs=orbs, battle_pass_points=0)


def _parse_mapping(
    text: str, allowed: tuple[str, ...], label: str, *, positive: bool = False
) -> dict[str, int]:
    """Parse `key=value` pairs for admin-edited settings."""

    raw_parts = [
        part.strip() for part in (text or "").replace(",", " ").split() if part.strip()
    ]
    if len(raw_parts) != len(allowed):
        raise ValidationError(f"{label} must include all values: {' '.join(allowed)}")
    result: dict[str, int] = {}
    for part in raw_parts:
        if "=" in part:
            key, value = part.split("=", 1)
        elif ":" in part:
            key, value = part.split(":", 1)
        else:
            raise ValidationError(f"{label} must use key=value pairs")
        normalized = key.strip().lower()
        if normalized not in allowed:
            raise ValidationError(f"unknown key '{key}' in {label}")
        if normalized in result:
            raise ValidationError(f"duplicate key '{key}' in {label}")
        result[normalized] = _parse_int(value.strip(), normalized, positive=positive)
    missing = [key for key in allowed if key not in result]
    if missing:
        raise ValidationError(f"{label} is missing: {' '.join(missing)}")
    return result


def _card_image_key(template) -> str:
    """Return a photo key for a card template."""

    return template.image.storage_key


def _templates(services) -> dict[int, CardTemplate]:
    """Return a template lookup map."""

    return {
        template.id: template for template in services.card_templates.items.values()
    }


def _paginate_items[T](
    items: list[T], page: int, size: int = 10
) -> tuple[list[T], int, bool, bool, int]:
    """Return a slice of items together with pagination flags."""

    if not items:
        return [], 1, False, False, 1
    total_pages = max(1, (len(items) + size - 1) // size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * size
    end = start + size
    return items[start:end], page, page > 1, page < total_pages, total_pages


def _profile_backgrounds(services) -> dict[int, ProfileBackgroundTemplate]:
    """Return a profile-background lookup map."""

    return {
        background.id: background
        for background in services.profile_backgrounds.items.values()
    }


def _admin_idea_scope_to_section(scope: str) -> str:
    """Map an idea callback scope to one admin section key."""

    mapping = {
        "admin_pending": "ideas_pending",
        "admin_public": "ideas_public",
        "admin_collection": "ideas_collection",
        "admin_rejected": "ideas_rejected",
    }
    return mapping.get(scope, "ideas_pending")


def _media_from_message(message: Message) -> tuple[str | None, str]:
    """Return a Telegram file id or URL together with a best-effort content type."""

    photo = getattr(message, "photo", None) or []
    if photo:
        return getattr(photo[-1], "file_id", None), "image/jpeg"
    video = getattr(message, "video", None)
    if video is not None:
        return getattr(video, "file_id", None), getattr(video, "mime_type", "video/mp4")
    document = getattr(message, "document", None)
    if document is not None:
        return getattr(document, "file_id", None), getattr(
            document, "mime_type", "application/octet-stream"
        )
    text = (message.text or "").strip()
    if text.lower().endswith((".mp4", ".mov", ".webm")):
        return text or None, "video/mp4"
    return text or None, "image/png"


__all__ = [
    "_admin_idea_scope_to_section",
    "_card_image_key",
    "_media_from_message",
    "_normalize_token",
    "_paginate_items",
    "_parse_dt",
    "_parse_effects",
    "_parse_int",
    "_parse_mapping",
    "_parse_reward_bundle",
    "_profile_backgrounds",
    "_templates",
]
