"""Profile and leaderboard text renderers."""

from src.clans.domain.entities import Clan
from src.players.domain.entities import (
    Player,
    PlayerTopEntry,
    ProfileBackgroundTemplate,
)
from src.telegram.texts.shared import (
    _background_label,
    _player_name,
    _wallet,
)


def profile_text(
    player: Player,
    clan: Clan | None,
    selected_background: ProfileBackgroundTemplate | None = None,
) -> str:
    """Build the player profile screen."""

    clan_line = f"<b>{clan.name}</b>" if clan else "<i>нет клана</i>"
    return (
        "👤 <b>Профиль бойца</b>\n\n"
        f"🏷 <b>Имя:</b> {_player_name(player)}\n"
        f"🆔 <b>ID:</b> <code>{player.telegram_id}</code>\n"
        f"📅 <b>Создан:</b> <code>{player.created_at.date()!s}</code>\n"
        f"🏆 <b>Рейтинг:</b> <code>{player.rating}</code>\n"
        f"🔥 <b>Победы/Проигрыши/Ничьи:</b> <code>{player.wins}/{player.losses}/{player.draws}</code>\n"
        f"🪄 <b>Creator Points:</b> <code>{player.creator_points}</code>\n"
        f"💎 <b>Premium:</b> <code>{'yes' if player.is_premium else 'no'}</code>\n"
        f"🏰 <b>Клан:</b> {clan_line}\n"
        f"📚 <b>Коллекция:</b> <code>{player.collection_count}</code>\n\n"
        f"🎨 <b>Активный фон:</b> {_background_label(selected_background)}\n"
        f"🖼 <b>Фонов в коллекции:</b> <code>{len(player.owned_profile_background_ids)}</code>\n\n"
        f"{_wallet(player)}"
    )


def profile_backgrounds_text(
    backgrounds: list[ProfileBackgroundTemplate], selected_id: int | None
) -> str:
    """Render the owned profile-background collection."""

    if not backgrounds:
        return (
            "🖼 <b>Фоны профиля</b>\n<i>Коллекция пока пустая. Ищи фоны в баннерах.</i>"
        )
    lines = ["🖼 <b>Фоны профиля</b>"]
    for background in backgrounds:
        selected = " · ✅ выбран" if background.id == selected_id else ""
        lines.append(
            f"• <b>Фон #{background.id}</b> — <code>{background.rarity.value}</code>{selected}"
        )
    return "\n".join(lines)


def profile_background_text(
    background: ProfileBackgroundTemplate, *, selected: bool = False
) -> str:
    """Render one profile background detail screen."""

    kind = (
        "видео" if background.media.content_type.startswith("video/") else "изображение"
    )
    selected_line = "да" if selected else "нет"
    return (
        f"🖼 <b>Фон профиля #{background.id}</b>\n"
        f"⭐ <b>Редкость:</b> <code>{background.rarity.value}</code>\n"
        f"🎞 <b>Тип медиа:</b> <code>{kind}</code>\n"
        f"✅ <b>Выбран:</b> <code>{selected_line}</code>"
    )


def admin_profile_backgrounds_text(
    backgrounds: list[ProfileBackgroundTemplate],
) -> str:
    """Build the admin profile-background catalog screen."""

    if not backgrounds:
        return "🖼 <b>Фоны профиля</b>\n<i>Пока фонов нет. Добавь первый и выдай игрокам стиль ✨</i>"
    return "\n".join(
        [
            "🖼 <b>Фоны профиля</b>",
            *[
                f"• <b>Фон #{background.id}</b> — <code>{background.rarity.value}</code>"
                for background in backgrounds
            ],
        ]
    )


def tops_text(entries: list[PlayerTopEntry], mode: str) -> str:
    """Render one users-top screen."""

    titles = {
        "rating": "🏆 <b>Топ по рейтингу</b>",
        "badenko_cards": "🃏 <b>Топ по Badenko-картам</b>",
        "creator_points": "🪄 <b>Топ по Creator Points</b>",
    }
    labels = {
        "rating": "рейтинг",
        "badenko_cards": "badenko",
        "creator_points": "creator points",
    }
    if not entries:
        return f"{titles[mode]}\n<i>Пока игроков в рейтинге нет.</i>"
    lines = [titles[mode], ""]
    for entry in entries:
        lines.append(
            f"{entry.rank}. {_player_name(entry.player)} — "
            f"<code>{entry.value}</code> {labels[mode]} · id <code>{entry.player.telegram_id}</code>"
        )
    return "\n".join(lines)


__all__ = [
    "admin_profile_backgrounds_text",
    "profile_background_text",
    "profile_backgrounds_text",
    "profile_text",
    "tops_text",
]
