"""Application bootstrap for the Yuqa bot."""

from asyncio import run
from dataclasses import dataclass

from yuqa.infrastructure.sqlalchemy.migrations import upgrade_head
from yuqa.telegram.bot import build_bot, build_dispatcher
from yuqa.telegram.config import Settings
from yuqa.telegram.services import TelegramServices


@dataclass(slots=True)
class App:
    """Small bundle with the runtime objects."""

    settings: Settings
    services: TelegramServices


def build_app() -> App:
    """Build the application state from environment variables."""

    settings = Settings.from_env()
    if settings.auto_migrate:
        upgrade_head(settings.database_url)
    return App(
        settings=settings,
        services=TelegramServices(
            settings.content_dir / "catalog.json",
            database_url=settings.database_url,
        ),
    )


async def main() -> None:
    """Start the bot in long polling mode."""

    app = build_app()
    bot = build_bot(app.settings)
    dispatcher = build_dispatcher(app.settings, app.services)
    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await app.services.shutdown()


def entrypoint() -> int:
    """Run the asynchronous entrypoint."""

    run(main())
    return 0
