"""Quest completion helpers for TelegramServices."""

from datetime import datetime, timedelta

from src.quests import (
    QuestService,
    QuestCompletionResult,
    QuestDefinition,
    QuestProgress,
    QuestReward,
    aware_utc,
)
from src.shared.enums import QuestActionType, QuestPeriod
from src.shared.errors import ValidationError
from src.telegram.services.contracts import TelegramServiceContext


class QuestServiceMixin(TelegramServiceContext, QuestService):
    """Cooldown-aware quest completion helpers."""
    
    async def complete_action_quest(
        self,
        quest: QuestDefinition,
        player_id: int,
        now: datetime | None = None,
    ) -> QuestCompletionResult:
        """Complete an action quest when the player's cooldown has expired."""
        
        if quest.cooldown.total_seconds() < 0:
            raise ValidationError("quest cooldown must be >= 0")
        
        moment = aware_utc(now)
        player = await self.get_or_create_player(player_id)
        await self.quests.save_definition(quest)
        
        progress = await self.quests.get_progress(player.telegram_id, quest.id)
        if progress is None:
            progress = QuestProgress(player_id=player.telegram_id, quest_id=quest.id)
        
        result = self.quest_service.complete_if_ready(
            player,
            quest,
            progress,
            completed_at=moment,
        )
        if not result.completed:
            return result
        
        await self.players.save(player)
        await self.quests.save_progress(progress)
        return result


__all__ = ["QuestServiceMixin"]
