"""Banner definition and its reward pools."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from yuqa.shared.enums import (
    BannerType,
    ProfileBackgroundRarity,
    Rarity,
    ResourceType,
    RewardType,
)
from yuqa.shared.value_objects.date_range import DateRange


@dataclass(frozen=True, slots=True)
class BannerReward:
    """Single weighted entry inside a banner pool."""

    reward_type: RewardType
    resource_type: ResourceType | None = None
    card_template_id: int | None = None
    profile_background_id: int | None = None
    quantity: int = 0
    rarity: Rarity | None = None
    profile_background_rarity: ProfileBackgroundRarity | None = None
    weight: int = 1
    guaranteed_for_10_pull: bool = False


@dataclass(slots=True)
class Banner:
    """Banner with a date window and a weighted reward pool."""

    id: int
    name: str
    banner_type: BannerType
    cost_resource: ResourceType
    pools: list[BannerReward] = field(default_factory=list)
    date_range: DateRange = field(default_factory=DateRange)
    is_active: bool = True

    def is_available(self, moment: datetime | None = None) -> bool:
        """Return True when the banner is visible to players."""

        return self.is_active and self.date_range.contains(
            moment or datetime.now(timezone.utc)
        )

    def can_edit(self, moment: datetime | None = None) -> bool:
        """Return True while the banner has not started yet."""

        moment = moment or datetime.now(timezone.utc)
        return self.date_range.start_at is None or moment < self.date_range.start_at
