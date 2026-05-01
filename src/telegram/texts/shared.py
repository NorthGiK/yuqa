"""Shared text-rendering helpers for Telegram screens."""

from datetime import datetime, timezone
from html import escape

from src.players.domain.entities import Player, ProfileBackgroundTemplate
from src.shared.enums import IdeaStatus
from src.shared.value_objects.stat_block import StatBlock


def _wallet(player: Player) -> str:
    """Render player resources in a compact block."""

    wallet = player.wallet
    return (
        f"🪙 <b>Монеты:</b> <code>{wallet.coins}</code>\n"
        f"💎 <b>Кристаллы:</b> <code>{wallet.crystals}</code>\n"
        f"🔮 <b>Орбы:</b> <code>{wallet.orbs}</code>\n"
        f"🎫 <b>Серебряные билеты:</b> <code>{wallet.silver_tickets}</code>\n"
        f"🎟️ <b>Золотые билеты:</b> <code>{wallet.gold_tickets}</code>"
    )


def _stats(stats: StatBlock | None) -> str:
    """Render a compact stat block or a blank marker."""

    return "—" if stats is None else f"{stats.damage}/{stats.health}/{stats.defense}"


def _player_name(player: Player) -> str:
    """Render the player's public name without HTML breakage."""

    if player.nickname:
        base = escape(player.nickname)
    else:
        base = f"Игрок <code>{player.telegram_id}</code>"
    if player.title:
        return f"{base} <b>{escape(player.title)}</b>"
    return base


def _background_label(background: ProfileBackgroundTemplate | None) -> str:
    """Render a compact profile-background label."""

    if background is None:
        return "<i>не выбран</i>"
    kind = "video" if background.media.content_type.startswith("video/") else "image"
    return (
        f"<code>#{background.id}</code> · "
        f"<code>{background.rarity.value}</code> · <code>{kind}</code>"
    )


def _idea_status_label(status: IdeaStatus) -> str:
    """Render a human-readable idea status."""

    labels = {
        IdeaStatus.PENDING: "на модерации",
        IdeaStatus.PUBLISHED: "на странице идей",
        IdeaStatus.COLLECTED: "в коллекции",
        IdeaStatus.REJECTED: "отклонена",
    }
    return labels[status]


def _cooldown_line(ready_at: datetime, now: datetime | None = None) -> str:
    """Render time remaining until a reward is ready."""

    current = now or datetime.now(timezone.utc)
    if ready_at <= current:
        return "✅ <b>Готово</b>"
    remaining = ready_at - current
    total_seconds = int(remaining.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"⏳ <b>Через:</b> <code>{hours:02d}:{minutes:02d}:{seconds:02d}</code>"


__all__ = [
    "_background_label",
    "_cooldown_line",
    "_idea_status_label",
    "_player_name",
    "_stats",
    "_wallet",
]
