"""Shared helpers for Telegram service mixins."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class AsyncReentrantLock:
    """Async lock that can be re-entered by the same task."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner: asyncio.Task[Any] | None = None
        self._depth = 0

    async def __aenter__(self) -> None:
        task = asyncio.current_task()
        if task is not None and task is self._owner:
            self._depth += 1
            return
        await self._lock.acquire()
        self._owner = task
        self._depth = 1

    async def __aexit__(self, *_exc_info: object) -> None:
        self._depth -= 1
        if self._depth > 0:
            return
        self._owner = None
        self._lock.release()


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


__all__ = ["AsyncReentrantLock", "BattleRoundSummary", "_next_id"]
