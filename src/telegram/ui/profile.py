"""Profile, clan, leaderboard, and profile-background keyboards."""

from aiogram.types import InlineKeyboardMarkup

from src.telegram.callbacks import (
    ClanCallback,
    MenuCallback,
    ProfileCallback,
    TopCallback,
)
from src.telegram.ui.helpers import _markup


def clan_markup(has_clan: bool) -> InlineKeyboardMarkup:
    """Return the clan screen keyboard."""

    return _markup(
        [
            (
                "🚪 Покинуть клан" if has_clan else "➕ Создать клан",
                ClanCallback(action="leave" if has_clan else "create"),
            ),
        ],
        (1,),
    )


def profile_markup(
    *,
    is_owner: bool,
    has_nickname: bool,
) -> InlineKeyboardMarkup:
    """Return the profile screen keyboard."""

    buttons = []
    if is_owner:
        buttons.append(("✏️ Никнейм", ProfileCallback(action="edit_nickname")))
        buttons.append(("🖼️ Фоны профиля", MenuCallback(section="profile_backgrounds")))
        if has_nickname:
            buttons.append(
                ("🧹 Сбросить ник", ProfileCallback(action="clear_nickname"))
            )
    if not buttons:
        return _markup(buttons, ())
    return _markup(buttons, (2, 1) if is_owner and has_nickname else (2,))


def tops_markup(current_mode: str) -> InlineKeyboardMarkup:
    """Return the users-top keyboard."""

    icons = {
        "rating": "🏆",
        "badenko_cards": "🃏",
        "creator_points": "🪄",
    }
    labels = {
        "rating": "Рейтинг",
        "badenko_cards": "Badenko",
        "creator_points": "Creator Points",
    }
    buttons = [
        (
            f"{icons[mode]} {'• ' if mode == current_mode else ''}{labels[mode]}",
            TopCallback(mode=mode),
        )
        for mode in ("rating", "badenko_cards", "creator_points")
    ]
    return _markup(buttons, (1, 1, 1))


def profile_backgrounds_markup(background_ids: list[int]) -> InlineKeyboardMarkup:
    """Return the owned profile-background collection keyboard."""

    buttons = [
        (
            f"🖼 Фон #{background_id}",
            ProfileCallback(action="open_background", background_id=background_id),
        )
        for background_id in background_ids
    ]
    buttons.append(("🧹 Снять фон", ProfileCallback(action="clear_background")))
    rows = [2] * (len(background_ids) // 2)
    if len(background_ids) % 2:
        rows.append(1)
    rows.append(1)
    return _markup(buttons, tuple(rows))


def profile_background_markup(
    background_id: int, *, selected: bool
) -> InlineKeyboardMarkup:
    """Return one profile-background detail keyboard."""

    buttons = []
    if not selected:
        buttons.append(
            (
                "✅ Установить",
                ProfileCallback(action="set_background", background_id=background_id),
            )
        )
    return _markup(buttons, (1, 1))


__all__ = [
    "clan_markup",
    "profile_background_markup",
    "profile_backgrounds_markup",
    "profile_markup",
    "tops_markup",
]
