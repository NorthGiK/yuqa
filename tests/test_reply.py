"""Tests for Telegram reply helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from src.telegram.compat import CallbackQuery, Message, TelegramBadRequest, User
from src.telegram.reply import safe_edit, send_alert, send_notice


@pytest.mark.asyncio
async def test_safe_edit_falls_back_when_message_has_no_text() -> None:
    """safe_edit should not crash on media messages with no text body."""

    message = Message(text=None)
    with patch.object(
        Message,
        "edit_text",
        new=AsyncMock(
            side_effect=TelegramBadRequest(
                method=None,
                message="Bad Request: there is no text in the message to edit",
            )
        ),
    ):
        await safe_edit(message, "Новый экран")

    assert message.answered_text == "Новый экран"


@pytest.mark.asyncio
async def test_send_notice_writes_a_chat_message_for_callbacks() -> None:
    """Callback notices should become chat messages instead of popup alerts."""

    message = Message(from_user=User(1), text="old")
    callback = CallbackQuery(from_user=User(1), message=message)

    result = await send_notice(callback, "Ошибка")

    assert result is message
    assert message.answered_text == "Ошибка"
    assert callback.answered_text is None
    assert callback.alert is False


@pytest.mark.asyncio
async def test_send_notice_does_not_answer_callback_when_message_exists() -> None:
    """A visible callback notice should not also trigger a callback toast."""

    message = Message(from_user=User(1), text="old")
    callback = CallbackQuery(from_user=User(1), message=message)

    with patch.object(
        CallbackQuery, "answer", new=AsyncMock(return_value=None)
    ) as callback_answer:
        await send_notice(callback, "Ошибка")

    callback_answer.assert_not_called()


@pytest.mark.asyncio
async def test_send_alert_uses_a_callback_popup() -> None:
    """Callback alerts should surface as popups instead of chat messages."""

    message = Message(from_user=User(1), text="old")
    callback = CallbackQuery(from_user=User(1), message=message)

    result = await send_alert(callback, "⛔️ Колода не полностью собрана")

    assert result is None
    assert callback.answered_text == "⛔️ Колода не полностью собрана"
    assert callback.alert is True
    assert message.answered_text is None
