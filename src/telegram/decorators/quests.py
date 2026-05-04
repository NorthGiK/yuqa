"""Quest completion decorators for Telegram handlers."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, Protocol, TypeVar

from aiogram.types import CallbackQuery, Message

from src.quests.domain.entities import QuestCompletionResult, QuestDefinition


class QuestCompletionService(Protocol):
    """Service surface needed by the quest decorator."""

    async def complete_action_quest(
        self,
        *,
        player_id: int,
        quest: QuestDefinition,
    ) -> QuestCompletionResult: ...


_P = ParamSpec("_P")
_R = TypeVar("_R")


def quest_init(
    services: QuestCompletionService,
    quest: QuestDefinition,
) -> Callable[
    [Callable[_P, Awaitable[_R]]],
    Callable[_P, Awaitable[_R]],
]:
    """Complete one quest before running a Telegram handler."""

    def decorator(handler: Callable[_P, Awaitable[_R]]) -> Callable[_P, Awaitable[_R]]:
        @wraps(handler)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            player_id = _player_id_from_handler_args(args)
            if player_id is not None:
                await services.complete_action_quest(
                    player_id=player_id,
                    quest=quest,
                )
            return await handler(*args, **kwargs)

        return wrapper

    return decorator


def _player_id_from_handler_args(args: tuple[object, ...]) -> int | None:
    """Extract the Telegram user id from a message or callback argument."""

    for item in args:
        from_user = None
        if isinstance(item, Message | CallbackQuery):
            from_user = item.from_user
        elif hasattr(item, "from_user"):
            from_user = getattr(item, "from_user")
        if from_user is not None:
            return from_user.id
    return None


__all__ = ["quest_init"]
