"""Quest completion helpers for TelegramServices."""

from datetime import datetime, timedelta, timezone

from src.quests.domain.entities import (
    QuestCompletionResult,
    QuestDefinition,
    QuestProgress,
    QuestReward,
)
from src.shared.enums import QuestActionType, QuestPeriod
from src.shared.errors import ValidationError
from src.telegram.services.contracts import TelegramServiceContext


class QuestServiceMixin(TelegramServiceContext):
    """Cooldown-aware quest completion helpers."""
    
    async def complete_action_quest(
        self,
        player_id: int,
        quest_id: int,
        action_type: QuestActionType,
        reward: QuestReward,
        cooldown: timedelta,
        *,
        period: QuestPeriod = QuestPeriod.DAILY,
        now: datetime | None = None,
    ) -> QuestCompletionResult:
        """Complete an action quest when the player's cooldown has expired."""
        
        if cooldown.total_seconds() < 0:
            raise ValidationError("quest cooldown must be >= 0")
        
        moment = _aware_utc(now)
        player = await self.get_or_create_player(player_id)
        definition = QuestDefinition(
            id=quest_id,
            period=period,
            action_type=action_type,
            reward=reward,
            cooldown=cooldown,
            is_active=True,
        )
        await self.quests.save_definition(definition)
        
        progress = await self.quests.get_progress(player.telegram_id, quest_id)
        if progress is None:
            progress = QuestProgress(player_id=player.telegram_id, quest_id=quest_id)
        
        result = self.quest_service.complete_if_ready(
            player,
            definition,
            progress,
            completed_at=moment,
        )
        if not result.completed:
            return result
        
        await self.players.save(player)
        await self.quests.save_progress(progress)
        return result


def _aware_utc(value: datetime | None) -> datetime:
    """Normalize optional datetimes before cooldown comparisons."""
    
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = ["QuestServiceMixin"]
