"""Quest completion and reset helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone

from src.players.domain.entities import Player
from src.quests.domain.entities import (
    QuestCompletionResult,
    QuestDefinition,
    QuestProgress,
    QuestReward,
)
from src.shared.enums import ResourceType


@dataclass(slots=True)
class QuestService:
    """Complete a quest and apply its reward."""

    def complete_if_ready(
        self,
        player: Player,
        quest: QuestDefinition,
        progress: QuestProgress,
        *,
        completed_at: datetime | None = None,
    ) -> QuestCompletionResult:
        """Complete the quest only when its player cooldown has expired."""
        
        moment = aware_utc(completed_at)
        if not progress.can_complete_at(moment):
            return QuestCompletionResult(
                player_id=player.telegram_id,
                quest_id=quest.id,
                action_type=quest.action_type,
                completed=False,
                reward=QuestReward(),
                completed_at=progress.completed_at,
                cooldown_until=progress.cooldown_until,
            )
        
        reward = self.complete(player, quest, progress, completed_at=moment)
        return QuestCompletionResult(
            player_id=player.telegram_id,
            quest_id=quest.id,
            action_type=quest.action_type,
            completed=True,
            reward=reward,
            completed_at=progress.completed_at,
            cooldown_until=progress.cooldown_until,
        )

    def complete(
        self,
        player: Player,
        quest: QuestDefinition,
        progress: QuestProgress,
        *,
        completed_at: datetime | None = None,
    ) -> QuestReward:
        """Mark the quest as done and pay the reward."""

        moment: datetime = aware_utc(completed_at)
        reward: QuestReward = quest.reward
        progress.completed = True
        progress.completed_count += 1
        progress.completed_at = moment
        progress.cooldown_until = moment + quest.cooldown

        if reward.coins:
            player.wallet.add(ResourceType.COINS, reward.coins)
        if reward.crystals:
            player.wallet.add(ResourceType.CRYSTALS, reward.crystals)
        if reward.orbs:
            player.wallet.add(ResourceType.ORBS, reward.orbs)
        if reward.battle_pass_points:
            player.battle_pass_progress.append(reward.battle_pass_points)
        return reward


@dataclass(slots=True)
class QuestResetService:
    """Reset quest progress lists after the refresh time."""

    def reset_daily(self, progresses: list[QuestProgress]) -> None:
        """Reset daily progress."""

        self._reset(progresses)

    def reset_weekly(self, progresses: list[QuestProgress]) -> None:
        """Reset weekly progress."""

        self._reset(progresses)

    @staticmethod
    def _reset(progresses: list[QuestProgress]) -> None:
        for progress in progresses:
            progress.completed = False
            progress.completed_count = 0
            progress.completed_at = None


def aware_utc(value: datetime | None) -> datetime:
    """Normalize optional datetimes for quest cooldown calculations."""

    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
