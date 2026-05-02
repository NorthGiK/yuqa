"""Daily and weekly quests."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

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
    cooldown: timedelta = field(default_factory=timedelta)
    is_active: bool = True


@dataclass(slots=True)
class QuestProgress:
    """Cooldown-aware progress for one player and one quest."""
    
    player_id: int
    quest_id: int
    completed: bool = False
    completed_count: int = 0
    completed_at: datetime | None = None
    cooldown_until: datetime | None = None
    
    def can_complete_at(self, moment: datetime) -> bool:
        """Return True when this quest can be completed at the given time."""
        
        if self.cooldown_until is None:
            return True
        cooldown_until = aware_utc(self.cooldown_until)
        return cooldown_until <= aware_utc(moment)


@dataclass(frozen=True, slots=True)
class QuestCompletionResult:
    """Result returned when an action tries to complete a quest."""
    
    player_id: int
    quest_id: int
    action_type: QuestActionType
    completed: bool
    reward: QuestReward
    completed_at: datetime | None
    cooldown_until: datetime | None


def aware_utc(value: datetime) -> datetime:
    """Normalize possibly naive datetimes before cooldown comparisons."""
    
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
