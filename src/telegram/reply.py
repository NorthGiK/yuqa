"""Helpers that keep handler bodies short."""

from os import getenv
from pathlib import Path
from urllib.parse import urlparse

from src.telegram.compat import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    Message,
    TelegramBadRequest,
)


def _markup_signature(markup: object | None) -> tuple:
    """Return a comparable representation of an inline keyboard."""

    if markup is None:
        return ()
    keyboard = getattr(markup, "inline_keyboard", None)
    if keyboard is None:
        return (repr(markup),)
    signature = []
    for row in keyboard:
        row_signature = []
        for button in row:
            if isinstance(button, tuple):
                row_signature.append(button[:2])
            elif isinstance(button, list):
                row_signature.append(tuple(button[:2]))
            else:
                row_signature.append(
                    (
                        getattr(button, "text", None),
                        getattr(button, "callback_data", None),
                    )
                )
        signature.append(tuple(row_signature))
    return tuple(signature)


async def safe_edit(
    message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> Message:
    """Edit a message and ignore duplicate-content Telegram errors."""

    if getattr(message, "text", None) == text and _markup_signature(
        getattr(message, "reply_markup", None)
    ) == _markup_signature(reply_markup):
        return message
    try:
        return await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        description = str(error).lower()
        if "message is not modified" in description:
            return message
        if "there is no text in the message to edit" in description:
            # A media message has caption but no editable text body.
            # Fall back to sending a new text message instead of crashing.
            return await message.answer(text, reply_markup=reply_markup)
        raise


async def send_or_edit(
    event: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message | None:
    """Send a new message or update the current callback message."""

    if getattr(event, "message", None) is not None and hasattr(event, "answer"):
        await safe_edit(event.message, text, reply_markup)
        return await event.answer()

    if hasattr(event, "answer"):
        return await event.answer(text, reply_markup=reply_markup)
    return None


async def send_notice(
    event: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message | None:
    """Send a visible chat message from a callback flow."""

    if isinstance(event, CallbackQuery):
        if event.message is not None:
            # The chat message is the user-facing notice; avoid an extra
            # callback answer so Telegram does not render a transient toast.
            return await event.message.answer(text, reply_markup=reply_markup)
        return await event.answer(text)
    return await event.answer(text, reply_markup=reply_markup)


async def send_alert(event: Message | CallbackQuery, text: str) -> Message | None:
    """Show a popup alert for callbacks and fall back to a message otherwise."""

    if isinstance(event, CallbackQuery):
        return await event.answer(text, show_alert=True)
    return await event.answer(text)


def _telegram_media(media_key: str) -> object:
    """Return a Telegram media value for a file id, URL, or local file path."""

    parsed = urlparse(media_key)
    if parsed.scheme in {"http", "https"}:
        return media_key
    if parsed.scheme == "file":
        paths = [Path(parsed.path)]
    else:
        path = Path(media_key).expanduser()
        paths = [path]
        if not path.is_absolute():
            data_dir = Path(getenv("YUQA_DATA_DIR", "data/yuqa")).expanduser()
            paths.append(data_dir / path)

    for path in paths:
        if path.exists() and path.is_file():
            return FSInputFile(path)
    return media_key


async def _send_media_with_fallback(
    event: Message | CallbackQuery,
    media_key: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    content_type: str = "image/png",
) -> Message | None:
    """Send media when possible and degrade to a text detail screen."""

    sender: Message | CallbackQuery
    if isinstance(event, CallbackQuery) and event.message:
        sender = event.message
    else:
        sender = event

    if isinstance(event, CallbackQuery):
        await event.answer()
    media = _telegram_media(media_key)
    if content_type.startswith("video/") and hasattr(sender, "answer_video"):
        try:
            return await sender.answer_video(
                video=media,
                caption=caption,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest:
            return await send_or_edit(event, caption, reply_markup)
    if hasattr(sender, "answer_photo"):
        try:
            return await sender.answer_photo(
                photo=media, caption=caption, reply_markup=reply_markup
            )
        except TelegramBadRequest:
            if hasattr(sender, "answer_document"):
                try:
                    return await sender.answer_document(
                        document=media, caption=caption, reply_markup=reply_markup
                    )
                except TelegramBadRequest:
                    return await send_or_edit(event, caption, reply_markup)
            return await send_or_edit(event, caption, reply_markup)
    return await send_or_edit(event, caption, reply_markup)


async def send_card_preview(
    event: Message | CallbackQuery,
    photo: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    content_type: str = "image/png",
) -> Message | None:
    """Send a card preview with an image when possible."""

    return await _send_media_with_fallback(
        event,
        photo,
        caption,
        reply_markup,
        content_type=content_type,
    )


async def send_media_preview(
    event: Message | CallbackQuery,
    media_key: str,
    caption: str,
    *,
    content_type: str = "image/png",
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message | None:
    """Send an image or video preview depending on the content type."""

    return await _send_media_with_fallback(
        event,
        media_key,
        caption,
        reply_markup,
        content_type=content_type,
    )
