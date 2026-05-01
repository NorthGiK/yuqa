"""Battle pass text renderers."""

from src.battle_pass.domain.entities import BattlePassSeason
from src.players.domain.entities import Player


def battle_pass_text(season: BattlePassSeason | None, player: Player) -> str:
    """Render the current battle pass and player progress."""

    points = sum(player.battle_pass_progress)
    if season is None:
        return "🏁 <b>Battle Pass</b>\n<i>Сезон пока не активен.</i>"
    unlocked = (
        ", ".join(
            str(level.level_number)
            for level in season.levels
            if points >= level.required_points
        )
        or "—"
    )
    return (
        f"🏁 <b>{season.name}</b>\n"
        f"📅 <b>Период:</b> <code>{season.start_at.date()} → {season.end_at.date()}</code>\n"
        f"⭐ <b>Твои очки:</b> <code>{points}</code>\n"
        f"🎁 <b>Открыты уровни:</b> <code>{unlocked}</code>\n\n"
        "<i>Очки Battle Pass приходят за квесты и события. Можно купить следующий уровень за 250 монет.</i>"
    )


def premium_battle_pass_text(season: BattlePassSeason | None, player: Player) -> str:
    """Render the current premium battle pass and player progress."""

    if not player.is_premium:
        return (
            "💎 <b>Premium Battle Pass</b>\n"
            "<i>Доступно только для игроков с премиум-статусом.</i>"
        )
    points = sum(player.battle_pass_progress)
    if season is None:
        return "💎 <b>Premium Battle Pass</b>\n<i>Сезон пока не активен.</i>"
    unlocked = (
        ", ".join(
            str(level.level_number)
            for level in season.levels
            if points >= level.required_points
        )
        or "—"
    )
    return (
        f"💎 <b>{season.name}</b>\n"
        f"📅 <b>Период:</b> <code>{season.start_at.date()} → {season.end_at.date()}</code>\n"
        f"⭐ <b>Твои очки:</b> <code>{points}</code>\n"
        f"🎁 <b>Открыты уровни:</b> <code>{unlocked}</code>\n\n"
        "<i>Премиум-ветка Battle Pass доступна только премиум-игрокам. Можно купить следующий уровень за 250 монет.</i>"
    )


def battle_pass_admin_text(season: BattlePassSeason | None) -> str:
    """Render the current admin view for battle pass levels."""

    if season is None:
        return "🏁 <b>Battle Pass</b>\n<i>Активный сезон не найден.</i>"
    if not season.levels:
        levels = "<i>Пока уровней нет.</i>"
    else:
        levels = "\n".join(
            f"• <b>Уровень {level.level_number}</b> — <code>{level.required_points}</code> очков, награда: "
            f"<code>{level.reward.coins}</code>🪙 <code>{level.reward.crystals}</code>💎 <code>{level.reward.orbs}</code>🔮"
            for level in season.levels
        )
    return (
        f"🏁 <b>{season.name}</b>\n"
        f"📅 <b>Период:</b> <code>{season.start_at.date()} → {season.end_at.date()}</code>\n"
        f"🎚️ <b>Уровней:</b> <code>{len(season.levels)}</code>\n\n"
        f"{levels}"
    )


def premium_battle_pass_admin_text(season: BattlePassSeason | None) -> str:
    """Render the current admin view for premium battle pass levels."""

    if season is None:
        return "💎 <b>Premium Battle Pass</b>\n<i>Активный сезон не найден.</i>"
    if not season.levels:
        levels = "<i>Пока уровней нет.</i>"
    else:
        levels = "\n".join(
            f"• <b>Уровень {level.level_number}</b> — <code>{level.required_points}</code> очков, награда: "
            f"<code>{level.reward.coins}</code>🪙 <code>{level.reward.crystals}</code>💎 <code>{level.reward.orbs}</code>🔮"
            for level in season.levels
        )
    return (
        f"💎 <b>{season.name}</b>\n"
        f"📅 <b>Период:</b> <code>{season.start_at.date()} → {season.end_at.date()}</code>\n"
        f"🎚️ <b>Уровней:</b> <code>{len(season.levels)}</code>\n\n"
        f"{levels}"
    )


def battle_pass_seasons_text(seasons: list[BattlePassSeason]) -> str:
    """Render the admin battle pass season list."""

    if not seasons:
        return "🏁 <b>Battle Pass</b>\n<i>Сезонов пока нет.</i>"
    lines = ["🏁 <b>Battle Pass</b>"]
    for season in seasons:
        status = "активен" if season.is_active else "архив"
        lines.append(
            f"• <b>{season.name}</b> — <code>{season.start_at.date()} → {season.end_at.date()}</code> · {status}"
        )
    return "\n".join(lines)


def premium_battle_pass_seasons_text(seasons: list[BattlePassSeason]) -> str:
    """Render the admin premium battle pass season list."""

    if not seasons:
        return "💎 <b>Premium Battle Pass</b>\n<i>Сезонов пока нет.</i>"
    lines = ["💎 <b>Premium Battle Pass</b>"]
    for season in seasons:
        status = "активен" if season.is_active else "архив"
        lines.append(
            f"• <b>{season.name}</b> — <code>{season.start_at.date()} → {season.end_at.date()}</code> · {status}"
        )
    return "\n".join(lines)


def battle_pass_level_wizard_text(step: str, draft: dict) -> str:
    """Render the battle pass level creation wizard."""

    return (
        "🏁 <b>Добавление уровня Battle Pass</b>\n"
        f"<i>Текущий шаг:</i> <code>{step}</code>\n\n"
        f"<b>Уровень:</b> {draft.get('level_number', '—')}\n"
        f"<b>Нужно очков:</b> {draft.get('required_points', '—')}\n"
        f"<b>Награда:</b> {draft.get('reward', '—')}\n\n"
        "<i>Пиши по одному полю за раз. На любом шаге можно нажать <b>Сбросить</b>.</i>\n"
        "<i>Награду вводи как:</i> <code>coins crystals orbs</code>\n"
        "<i>Пример:</i> <code>100 5 1</code>"
    )


def battle_pass_season_wizard_text(step: str, draft: dict) -> str:
    """Render the battle pass season creation wizard."""

    return (
        "🏁 <b>Создание Battle Pass</b>\n"
        f"<i>Текущий шаг:</i> <code>{step}</code>\n\n"
        f"<b>Название:</b> {draft.get('name', '—')}\n"
        f"<b>Старт:</b> {draft.get('start_at', '—')}\n"
        f"<b>Финиш:</b> {draft.get('end_at', '—')}\n\n"
        "<i>Даты вводи в ISO-формате, например <code>2026-04-10T12:00:00+00:00</code>.</i>"
    )


__all__ = [
    "battle_pass_admin_text",
    "battle_pass_level_wizard_text",
    "battle_pass_season_wizard_text",
    "battle_pass_seasons_text",
    "battle_pass_text",
    "premium_battle_pass_admin_text",
    "premium_battle_pass_seasons_text",
    "premium_battle_pass_text",
]
