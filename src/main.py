"""Application bootstrap for the Yuqa bot."""

from asyncio import run
from dataclasses import dataclass
import logging
from time import perf_counter

from aiogram import Bot

from src.battles.domain.entities import Battle
from src.infrastructure.sqlalchemy.migrations import upgrade_head
from src.infrastructure.sqlalchemy.urls import safe_database_url
from src.shared.metrics import MetricsServer
from src.shared.observability import configure_logging
from src.telegram.bot import build_bot, build_dispatcher
from src.telegram.config import Settings
from src.telegram.services import TelegramServices
from src.telegram.services.contracts import BattleTimeoutNotifier
from src.telegram.texts import battle_status_text
from src.telegram.ui import battle_actions_markup


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class App:
    """Small bundle with the runtime objects."""

    settings: Settings
    services: TelegramServices


def build_app() -> App:
    """Build the application state from environment variables."""

    settings = Settings.from_env()
    configure_logging(level=settings.log_level, log_format=settings.log_format)
    logger.info(
        "runtime settings loaded",
        extra={
            "admin_count": len(settings.admin_ids),
            "auto_migrate": settings.auto_migrate,
            "content_dir": str(settings.content_dir),
            "database_url": safe_database_url(settings.database_url),
            "log_format": settings.log_format,
            "metrics_enabled": settings.metrics_enabled,
        },
    )
    if settings.auto_migrate:
        started_at = perf_counter()
        logger.info("database migration started")
        upgrade_head(settings.database_url)
        logger.info(
            "database migration finished",
            extra={"duration_ms": round((perf_counter() - started_at) * 1000, 2)},
        )
    else:
        logger.warning("automatic database migrations are disabled")

    started_at = perf_counter()
    services = TelegramServices(
        settings.content_dir / "catalog.json",
        database_url=settings.database_url,
    )
    logger.info(
        "services initialized",
        extra={"duration_ms": round((perf_counter() - started_at) * 1000, 2)},
    )
    return App(
        settings=settings,
        services=services,
    )


async def main() -> None:
    """Start the bot in long polling mode."""

    app = build_app()
    bot = build_bot(app.settings)
    metrics_server = MetricsServer(
        enabled=app.settings.metrics_enabled,
        host=app.settings.metrics_host,
        port=app.settings.metrics_port,
    )
    app.services.configure_battle_timeout_notifier(
        _build_battle_timeout_notifier(bot, app.services)
    )
    dispatcher = build_dispatcher(app.settings, app.services)
    try:
        await metrics_server.start()
        logger.info("telegram polling started")
        await dispatcher.start_polling(bot)
        logger.info("telegram polling stopped")
    except Exception:
        logger.exception("telegram polling failed")
        raise
    finally:
        logger.info("application shutdown started")
        await metrics_server.stop()
        await app.services.shutdown()
        await bot.session.close()
        logger.info("application shutdown finished")


def entrypoint() -> int:
    """Run the asynchronous entrypoint."""

    run(main())
    return 0


def _build_battle_timeout_notifier(
    bot: Bot,
    services: TelegramServices,
) -> BattleTimeoutNotifier:
    """Build a notifier that sends one battle update after automatic timeout."""

    async def _notify(battle: Battle, *, reason: str | None = None) -> None:
        for player_id in (battle.player_one_id, battle.player_two_id):
            summary = services.battle_round_summary(battle, player_id)
            text = battle_status_text(
                battle,
                player_id,
                opponent_spent_action_points=summary.opponent_spent_action_points,
                available_action_points=summary.available_action_points,
                total_action_points=summary.total_action_points,
                attack_count=summary.attack_count,
                block_count=summary.block_count,
                bonus_count=summary.bonus_count,
                ability_used=summary.ability_used,
            )
            if reason:
                text = reason + "\n\n" + text
            markup = None
            if battle.status.value == "active" and summary.available_action_points > 0:
                markup = battle_actions_markup(
                    can_switch=summary.can_switch,
                    ability_cost=summary.ability_cost,
                    can_use_ability=(
                        not summary.ability_used
                        and summary.ability_cooldown_remaining <= 0
                        and summary.available_action_points >= summary.ability_cost
                    ),
                )
            await bot.send_message(player_id, text, reply_markup=markup)

    return _notify
