"""Battle screen text renderers."""

from html import escape

from yuqa.battles.domain.entities import Battle
from yuqa.players.domain.entities import Player


def battle_text(player: Player | None = None, searching: bool = False) -> str:
    """Explain how to start or cancel a battle search."""

    header = "⚔️ <b>Арена PvP</b>\n<i>Пора показать, кто тут главный!</i>\n\n"
    body = (
        "• для боя нужна колода из <b>5 разных карт</b>\n"
        "• сначала собери колоду в конструкторе\n"
        "• поиск соперника подбирает игрока с разницей рейтинга <b>±100</b>\n"
        "• можно остановить поиск в любой момент\n"
    )
    if player is None:
        return header + body
    line = f"👤 <b>Твой ID:</b> <code>{player.telegram_id}</code>\n"
    line += f"🔎 <b>Статус:</b> <i>{'ищем соперника' if searching else 'готов к бою'}</i>\n\n"
    return header + line + body


def battle_started_text(battle: Battle) -> str:
    """Render a short message after battle creation."""

    return (
        "💥 <b>Бой начался!</b>\n"
        f"🆔 <b>Бой:</b> <code>{battle.id}</code>\n"
        f"🎲 <b>Первый ход:</b> <code>{battle.first_turn_player_id}</code>\n"
        f"📍 <i>Раунд {battle.current_round}</i>\n"
    )


def _battle_card_line(card, *, active: bool = False) -> str:
    """Render one battle card row."""

    marker = "✅" if active else ""
    return f"•{marker}{escape(card.template.name)} |♥️{card.current_health}| |⚔️{card.damage}| |🛡️{card.defense}|"


def battle_status_text(
    battle: Battle,
    player_id: int,
    *,
    opponent_spent_action_points: int,
    available_action_points: int,
    total_action_points: int,
    attack_count: int,
    block_count: int,
    bonus_count: int,
    ability_used: bool,
) -> str:
    """Render the battle accessibility screen for one player."""

    opponent_side = battle.opponent_side_for(player_id)
    player_side = battle.side_for(player_id)
    opponent_cards = "\n".join(
        _battle_card_line(
            card, active=card.player_card_id == opponent_side.active_card_id
        )
        for card in opponent_side.cards.values()
        if card.alive
    )
    player_cards = "\n".join(
        _battle_card_line(
            card, active=card.player_card_id == player_side.active_card_id
        )
        for card in player_side.cards.values()
    )
    return (
        "🪖Колода Оппонента:\n"
        f"Потрачено ОД в раунде {opponent_spent_action_points}\n"
        f"{opponent_cards}\n\n"
        "🫪Твоя Колода:\n"
        f"Очки действия {available_action_points}/{total_action_points}\n"
        f"{player_cards}\n\n"
        "Текущий выбор:\n"
        f"⚔️ {attack_count}\n"
        f"🛡️ {block_count}\n"
        f"🌟 {bonus_count}\n"
        f"🔥 {'✅' if ability_used else '❌'}"
    )


__all__ = [
    "battle_started_text",
    "battle_status_text",
    "battle_text",
]
