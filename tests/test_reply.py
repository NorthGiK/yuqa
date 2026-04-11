"""Tests for Telegram reply helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from yuqa.telegram.compat import Message, TelegramBadRequest
from yuqa.telegram.reply import safe_edit


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
