"""Weighted banner rolls."""

from dataclasses import dataclass
from random import Random

from src.banners.domain.entities import Banner, BannerReward
from src.players.domain.entities import Player
from src.shared.enums import ProfileBackgroundRarity, Rarity, RewardType
from src.shared.errors import NotEnoughResourcesError, ValidationError

_EPIC_AND_HIGHER = {
    Rarity.EPIC,
    Rarity.MYTHIC,
    Rarity.LEGENDARY,
    Rarity.GODLY,
    Rarity.BADENKO,
}
_EPIC_AND_HIGHER_BACKGROUNDS = {
    ProfileBackgroundRarity.EPIC,
    ProfileBackgroundRarity.LEGENDARY,
    ProfileBackgroundRarity.LIMITED,
}


@dataclass(slots=True)
class BannerRollService:
    """Roll rewards from a banner and charge the correct ticket type."""

    rng: Random = Random()

    def _pick(self, rewards: list[BannerReward]) -> BannerReward:
        """Select one reward by weight."""

        if not rewards:
            raise ValidationError("no rewards available")
        total = sum(reward.weight for reward in rewards)
        pick = self.rng.randint(1, total)
        upto = 0
        for reward in rewards:
            upto += reward.weight
            if pick <= upto:
                return reward
        return rewards[-1]

    def pull(
        self, player: Player, banner: Banner, count: int = 1
    ) -> list[BannerReward]:
        """Pull one or ten rewards from a banner."""

        if not banner.is_available():
            raise ValidationError("banner is unavailable")
        if not player.wallet.can_spend(banner.cost_resource, count):
            raise NotEnoughResourcesError("Не достаточно Билетов")
        player.wallet.spend(banner.cost_resource, count)
        rewards = [self._pick(banner.pools) for _ in range(count)]
        if count == 10:
            rewards.extend(self._bonus_for_ten_pull(banner))
        return rewards

    def _bonus_for_ten_pull(self, banner: Banner) -> list[BannerReward]:
        """Add the guaranteed 10-pull bonus when possible."""

        for reward in banner.pools:
            if reward.guaranteed_for_10_pull:
                return [reward]
        for reward in banner.pools:
            if (
                reward.reward_type == RewardType.CARD
                and reward.rarity in _EPIC_AND_HIGHER
            ):
                return [reward]
            if (
                reward.reward_type == RewardType.PROFILE_BACKGROUND
                and reward.profile_background_rarity in _EPIC_AND_HIGHER_BACKGROUNDS
            ):
                return [reward]
        return []
