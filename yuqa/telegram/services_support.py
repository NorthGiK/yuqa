"""Shared helpers for Telegram service mixins."""

from dataclasses import dataclass


@dataclass(slots=True)
class BattleRoundSummary:
    """Compact snapshot of a player's current battle choices."""

    attack_count: int
    block_count: int
    bonus_count: int
    ability_used: bool
    available_action_points: int
    opponent_action_points: int
    ability_cost: int
    can_switch: bool


def _next_id(items) -> int:
    """Return the next numeric identifier for a repository mapping."""

    return max(items, default=0) + 1


__all__ = ["BattleRoundSummary", "_next_id"]
