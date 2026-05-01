"""Battle-related keyboards."""

from src.telegram.callbacks import BattleCallback, BattleQueueCallback, MenuCallback
from src.telegram.compat import InlineKeyboardMarkup
from src.telegram.ui.helpers import _markup


def battle_markup(searching: bool = False) -> InlineKeyboardMarkup:
    """Return the battle screen keyboard."""

    button = "⏳ Отменить поиск" if searching else "🔍 Поиск соперника"
    action = "cancel_search" if searching else "search"
    return _markup(
        [
            (button, BattleQueueCallback(action=action)),
            ("🧱 Конструктор колоды", MenuCallback(section="deck")),
        ],
        (1, 1),
    )


def battle_actions_markup(
    *, can_switch: bool, ability_cost: int, can_use_ability: bool = True
) -> InlineKeyboardMarkup:
    """Return the battle round action keyboard."""

    buttons = [
        ("⚔️Атака", BattleCallback(action="attack")),
        ("🛡️Блок", BattleCallback(action="block")),
        ("🌟Бонус", BattleCallback(action="bonus")),
    ]
    if can_switch:
        buttons.append(("🦹‍♂️Сменить карту", BattleCallback(action="switch")))
    if can_use_ability:
        buttons.append(
            (f"🔥Способность {ability_cost}", BattleCallback(action="ability"))
        )
    if len(buttons) == 1:
        sizes = (1,)
    elif len(buttons) == 2:
        sizes = (2,)
    elif len(buttons) == 3:
        sizes = (2, 1)
    elif len(buttons) == 4:
        sizes = (2, 2)
    else:
        sizes = (2, 2, 1)
    return _markup(buttons, sizes)


def battle_switch_markup(
    cards: list[tuple[int, str]], *, back_action: str = "back"
) -> InlineKeyboardMarkup:
    """Return the card picker for a battle switch action."""

    buttons = [
        (label, BattleCallback(action="switch_choose", card_id=card_id))
        for card_id, label in cards
    ]
    buttons.append(("⬅️ Назад", BattleCallback(action=back_action)))
    return _markup(buttons, (1,) * len(buttons))


__all__ = ["battle_actions_markup", "battle_markup", "battle_switch_markup"]
