"""Factory helpers for the Telegram bot runtime."""

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.telegram.config import Settings
from src.telegram.router import build_router
from src.telegram.services.services import TelegramServices


class ActionRecorderMiddleware(BaseMiddleware):
    """Record incoming Telegram actions and keep matchmaking warm."""

    def __init__(self, services) -> None:
        self.services = services

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None) or getattr(
            getattr(event, "message", None), "from_user", None
        )
        if user is not None and hasattr(self.services, "record_action"):
            action = (
                getattr(event, "data", None)
                or getattr(event, "text", None)
                or type(event).__name__.lower()
            )
            await self.services.record_action(user.id, str(action))
        return await handler(event, data)


def build_bot(settings: Settings) -> Bot:
    """Build a bot with HTML as the default parse mode."""

    return Bot(settings.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def build_dispatcher(settings: Settings, services: TelegramServices) -> Dispatcher:
    """Build a dispatcher with the application router attached."""

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(build_router(services, settings))
    if hasattr(dispatcher, "update") and hasattr(dispatcher.update, "outer_middleware"):
        dispatcher.update.outer_middleware(ActionRecorderMiddleware(services))
    return dispatcher
