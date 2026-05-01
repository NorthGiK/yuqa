"""Shared helpers for Telegram service mixins."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(slots=True)
class BattleRoundSummary:
    """Compact snapshot of a player's current battle choices."""

    current_turn_player_id: int
    is_player_turn: bool
    attack_count: int
    block_count: int
    bonus_count: int
    ability_used: bool
    available_action_points: int
    total_action_points: int
    opponent_spent_action_points: int
    ability_cost: int
    ability_cooldown_remaining: int
    can_switch: bool


def _next_id(items: Mapping[int, object]) -> int:
    """Return the next numeric identifier for a repository mapping."""

    return max(items, default=0) + 1


__all__ = ["BattleRoundSummary", "_next_id"]
