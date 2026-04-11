"""Helpers that keep handler bodies short."""

from yuqa.telegram.compat import (
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
):
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
    event, text: str, reply_markup: InlineKeyboardMarkup | None = None
):
    """Send a new message or update the current callback message."""

    if getattr(event, "message", None) is not None and hasattr(event, "answer"):
        await safe_edit(event.message, text, reply_markup)
        return await event.answer()
    if hasattr(event, "answer"):
        return await event.answer(text, reply_markup=reply_markup)
    return None


async def send_card_preview(
    event, photo: str, caption: str, reply_markup: InlineKeyboardMarkup | None = None
):
    """Send a card preview with an image when possible."""

    if getattr(event, "message", None) is not None and hasattr(
        event.message, "answer_photo"
    ):
        if hasattr(event, "answer"):
            await event.answer()
        return await event.message.answer_photo(
            photo=photo, caption=caption, reply_markup=reply_markup
        )
    if hasattr(event, "answer_photo"):
        return await event.answer_photo(
            photo=photo, caption=caption, reply_markup=reply_markup
        )
    return await send_or_edit(event, caption, reply_markup)


async def send_media_preview(
    event,
    media_key: str,
    caption: str,
    *,
    content_type: str = "image/png",
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """Send an image or video preview depending on the content type."""

    sender = getattr(event, "message", event)
    if getattr(event, "message", None) is not None and hasattr(event, "answer"):
        await event.answer()
    if content_type.startswith("video/") and hasattr(sender, "answer_video"):
        return await sender.answer_video(
            video=media_key,
            caption=caption,
            reply_markup=reply_markup,
        )
    if hasattr(sender, "answer_photo"):
        return await sender.answer_photo(
            photo=media_key,
            caption=caption,
            reply_markup=reply_markup,
        )
    return await send_or_edit(event, caption, reply_markup)
