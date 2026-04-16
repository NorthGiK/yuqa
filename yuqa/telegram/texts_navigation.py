"""Navigation and home screen text renderers."""

from yuqa.players.domain.entities import Player
from yuqa.telegram.texts_shared import _player_name, _wallet


def menu_text(player: Player) -> str:
    """Build the friendly home screen text."""

    return (
        "🎮 <b>Добро пожаловать в Yuqa!</b>\n"
        "<i>Здесь карты не лежат в пыли — они дерутся, качаются и сияют.</i> ✨\n\n"
        f"👋 <b>Игрок:</b> {_player_name(player)}\n"
        f"🆔 <b>Твой Telegram ID:</b> <code>{player.telegram_id}</code>\n"
        f"🏆 <b>Рейтинг:</b> <code>{player.rating}</code>\n"
        f"🔥 <b>Победы:</b> <code>{player.wins}</code>  "
        f"⚔️ <b>Поражения:</b> <code>{player.losses}</code>  "
        f"🤝 <b>Ничьи:</b> <code>{player.draws}</code>\n\n"
        f"{_wallet(player)}"
    )


def collection_text(player: Player) -> str:
    """Build the collection hub screen."""

    return (
        "📚 <b>Коллекция</b>\n"
        "<i>Выбери, что открыть дальше.</i>\n\n"
        f"🎴 <b>Карт в коллекции:</b> <code>{player.collection_count}</code>"
    )


__all__ = ["collection_text", "menu_text"]
