"""Reward and progression keyboards."""

from yuqa.telegram.callbacks import (
    BattlePassCallback,
    FreeRewardCallback,
    PremiumBattlePassCallback,
)
from yuqa.telegram.compat import InlineKeyboardMarkup
from yuqa.telegram.ui_helpers import _markup


def battle_pass_markup(*, can_buy_level: bool = False) -> InlineKeyboardMarkup:
    """Return a minimal battle pass keyboard."""

    buttons = []
    if can_buy_level:
        buttons.append(
            ("💰 Купить уровень за 250", BattlePassCallback(action="buy_level"))
        )
    return _markup(buttons, (1, 1) if can_buy_level else (1,))


def premium_battle_pass_markup(*, can_buy_level: bool = False) -> InlineKeyboardMarkup:
    """Return a minimal premium battle pass keyboard."""

    buttons = []
    if can_buy_level:
        buttons.append(
            ("💰 Купить уровень за 250", PremiumBattlePassCallback(action="buy_level"))
        )
    return _markup(buttons, (1, 1) if can_buy_level else (1,))


def free_rewards_markup() -> InlineKeyboardMarkup:
    """Return the free rewards screen keyboard."""

    return _markup(
        [
            ("🎴 Забрать карту", FreeRewardCallback(action="claim_card")),
            ("💰 Забрать ресурсы", FreeRewardCallback(action="claim_resources")),
        ],
        (1, 1),
    )


__all__ = [
    "battle_pass_markup",
    "free_rewards_markup",
    "premium_battle_pass_markup",
]
