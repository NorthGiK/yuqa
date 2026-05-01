"""Navigation keyboards."""

from src.telegram.callbacks import MenuCallback
from src.telegram.compat import ReplyKeyboardMarkup
from src.telegram.ui.helpers import _markup, _reply_markup


_PREMIUM_MENU_BUTTON = "💎 Premium Battle Pass"
COLLECTION_MENU_BUTTON = "🐦‍🔥 Коллекция"
MAIN_MENU_BUTTON_ROWS: tuple[tuple[str, ...], ...] = (
    ("👤 Профиль", COLLECTION_MENU_BUTTON),
    ("📖 Галерея", "💡 Идеи"),
    ("🏆 Топы", "⚔️ Бой"),
    ("🛒 Магазин", "🎁 Баннеры"),
    ("🏁 Battle Pass", "🏰 Клан"),
)
MAIN_MENU_BUTTON_TEXTS = {text for row in MAIN_MENU_BUTTON_ROWS for text in row} | {
    _PREMIUM_MENU_BUTTON,
    "🛠 Админка",
}


def main_menu_markup(
    *, is_admin: bool = False, is_premium: bool = False
) -> ReplyKeyboardMarkup:
    """Return the main navigation keyboard."""

    rows = list(MAIN_MENU_BUTTON_ROWS)
    if is_premium:
        rows.insert(5, (_PREMIUM_MENU_BUTTON,))
    if is_admin:
        rows.append(("🛠 Админка",))
    return _reply_markup(tuple(rows))


def collection_markup():
    """Return the collection hub keyboard."""

    return _markup(
        [
            ("🎴 Мои Карты", MenuCallback(section="cards")),
            ("💡 Мои идеи", MenuCallback(section="idea_collection")),
        ],
        (1, 1),
    )


__all__ = [
    "COLLECTION_MENU_BUTTON",
    "MAIN_MENU_BUTTON_ROWS",
    "MAIN_MENU_BUTTON_TEXTS",
    "_PREMIUM_MENU_BUTTON",
    "collection_markup",
    "main_menu_markup",
]
