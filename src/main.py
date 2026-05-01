"""Application bootstrap for the Yuqa bot."""

from asyncio import run
from dataclasses import dataclass

from src.battles.domain.entities import Battle
from src.infrastructure.sqlalchemy.migrations import upgrade_head
from src.telegram.bot import build_bot, build_dispatcher
from src.telegram.compat import Bot
from src.telegram.config import Settings
from src.telegram.services import TelegramServices
from src.telegram.services.contracts import BattleTimeoutNotifier
from src.telegram.texts import battle_status_text
from src.telegram.ui import battle_actions_markup


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
    app.services.configure_battle_timeout_notifier(
        _build_battle_timeout_notifier(bot, app.services)
    )
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
