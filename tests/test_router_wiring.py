"""Regression checks for aiogram handler signatures."""

from inspect import signature
from pathlib import Path

from src.telegram.config import Settings
from src.telegram.router import build_router
from src.telegram.services.services import TelegramServices


def _message_callbacks(router) -> list:
    """Return callbacks attached to message events for both router backends."""

    if hasattr(router, "observers"):
        return [handler.callback for handler in router.observers["message"].handlers]
    return [
        callback
        for event_type, _filters, callback in getattr(router, "handlers", [])
        if event_type == "message"
    ]


def test_message_handlers_do_not_require_services_dependency() -> None:
    """Message handlers should use closed-over services, not DI injection."""

    settings = Settings(
        token="test-token",
        admin_ids={1},
        content_dir=Path("data/yuqa"),
        database_url="data/yuqa",
        auto_migrate=True,
    )
    callbacks = _message_callbacks(build_router(TelegramServices(), settings))

    for callback in callbacks:
        assert "services" not in signature(callback).parameters
