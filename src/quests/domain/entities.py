"""Daily and weekly quests."""

from dataclasses import dataclass

from src.shared.enums import QuestActionType, QuestPeriod


@dataclass(frozen=True, slots=True)
class QuestReward:
    """Reward bundle for a quest or battle pass level."""

    coins: int = 0
    crystals: int = 0
    orbs: int = 0
    battle_pass_points: int = 0


@dataclass(slots=True)
class QuestDefinition:
    """Quest metadata configured by the admin panel."""

    id: int
    period: QuestPeriod
    action_type: QuestActionType
    reward: QuestReward
    is_active: bool = True


@dataclass(slots=True)
class QuestProgress:
    """Boolean progress for one player and one quest."""

    player_id: int
    quest_id: int
    completed: bool = False
