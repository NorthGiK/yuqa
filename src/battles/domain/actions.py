"""Battle action objects."""

from dataclasses import dataclass

from src.shared.enums import BattleActionType


@dataclass(frozen=True, slots=True)
class BattleAction:
    """Base combat action."""

    action_type: BattleActionType
    ap_cost: int
    power_spent: int = 1


@dataclass(frozen=True, slots=True)
class AttackAction(BattleAction):
    """Attack the opponent's active card."""

    target_card_id: int | None = None


@dataclass(frozen=True, slots=True)
class BlockAction(BattleAction):
    """Increase defense for one round."""


@dataclass(frozen=True, slots=True)
class BonusAction(BattleAction):
    """Spend action points on a bonus move."""


@dataclass(frozen=True, slots=True)
class UseAbilityAction(BattleAction):
    """Trigger a card ability."""

    player_card_id: int | None = None


@dataclass(frozen=True, slots=True)
class SwitchCardAction(BattleAction):
    """Change the active card."""

    new_active_card_id: int | None = None
