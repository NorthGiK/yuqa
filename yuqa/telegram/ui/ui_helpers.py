"""Small markup helpers shared across Telegram UI modules."""

from aiogram.types import KeyboardButton

from yuqa.telegram.callbacks import AdminCallback
from yuqa.telegram.compat import (
    InlineKeyboardBuilder,
    InlineKeyboardMarkup,
    ReplyKeyboardBuilder,
    ReplyKeyboardMarkup,
)


def _markup(buttons: list[tuple[str, KeyboardButton]], sizes: tuple[int, ...]) -> InlineKeyboardMarkup:
    """Build a markup from a list of button specs."""

    builder = InlineKeyboardBuilder()
    if not buttons:
        return builder.as_markup()

    for text, payload in buttons:
        builder.button(text=text, callback_data=payload)

    builder.adjust(*sizes)
    return builder.as_markup()


def _reply_markup(rows: tuple[tuple[str, ...], ...]) -> ReplyKeyboardMarkup:
    """Build a reply keyboard from button rows."""

    builder = ReplyKeyboardBuilder()
    for row in rows:
        for text in row:
            builder.button(text=text)
    builder.adjust(*(len(row) for row in rows))
    return builder.as_markup(resize_keyboard=True)


def _choice_markup(
    action: str, items: list[tuple[str, str]], back_value: str = "dashboard"
) -> InlineKeyboardMarkup:
    """Build a small choice keyboard."""

    buttons = [
        (text, AdminCallback(action=action, value=value)) for text, value in items
    ]
    return _markup(buttons, (2, 2, 2))


__all__ = ["_choice_markup", "_markup", "_reply_markup"]
