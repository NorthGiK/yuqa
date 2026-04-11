"""Quest completion and reset helpers."""

from dataclasses import dataclass

from yuqa.players.domain.entities import Player
from yuqa.quests.domain.entities import QuestDefinition, QuestProgress, QuestReward
from yuqa.shared.enums import ResourceType


@dataclass(slots=True)
class QuestService:
    """Complete a quest and apply its reward."""

    def complete(
        self, player: Player, quest: QuestDefinition, progress: QuestProgress
    ) -> QuestReward:
        """Mark the quest as done and pay the reward."""

        progress.completed = True
        reward = quest.reward
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
