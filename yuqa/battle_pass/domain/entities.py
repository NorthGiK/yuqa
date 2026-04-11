"""Battle pass season and progress entities."""

from dataclasses import dataclass, field
from datetime import datetime

from yuqa.quests.domain.entities import QuestReward


@dataclass(slots=True)
class BattlePassLevel:
    """A single rewarded level."""

    level_number: int
    required_points: int
    reward: QuestReward


@dataclass(slots=True)
class BattlePassSeason:
    """A finite battle pass season."""

    id: int
    name: str
    start_at: datetime
    end_at: datetime
    levels: list[BattlePassLevel] = field(default_factory=list)
    is_active: bool = True


@dataclass(slots=True)
class BattlePassProgress:
    """Per-player season progress."""

    player_id: int
    season_id: int
    points: int = 0
    claimed_levels: set[int] = field(default_factory=set)
