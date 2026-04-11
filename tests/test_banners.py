"""Tests for banner availability and pulls."""

from datetime import datetime, timedelta, timezone

from yuqa.banners.domain.entities import Banner, BannerReward
from yuqa.banners.domain.services import BannerRollService
from yuqa.players.domain.entities import Player
from yuqa.shared.enums import BannerType, Rarity, ResourceType, RewardType
from yuqa.shared.value_objects.date_range import DateRange
from yuqa.shared.value_objects.resource_wallet import ResourceWallet


def test_banner_roll_and_availability():
    now = datetime.now(timezone.utc)
    banner = Banner(
        id=1,
        name="Standard",
        banner_type=BannerType.NORMAL,
        cost_resource=ResourceType.SILVER_TICKETS,
        date_range=DateRange(now - timedelta(days=1), now + timedelta(days=1)),
        pools=[
            BannerReward(reward_type=RewardType.RESOURCE, resource_type=ResourceType.COINS, quantity=100, weight=10),
            BannerReward(reward_type=RewardType.CARD, card_template_id=1, rarity=Rarity.EPIC, weight=1),
        ],
    )
    player = Player(telegram_id=1, wallet=ResourceWallet(silver_tickets=10))
    pulls = BannerRollService().pull(player, banner, count=10)
    assert len(pulls) == 11 and player.wallet.silver_tickets == 0


def test_banner_starts_correctly_with_timezone_offsets():
    """Availability should honor absolute time across timezone-aware datetimes."""

    start_local = datetime(2026, 4, 10, 12, 0, tzinfo=timezone(timedelta(hours=5)))
    banner = Banner(
        id=2,
        name="TZ Banner",
        banner_type=BannerType.EVENT,
        cost_resource=ResourceType.GOLD_TICKETS,
        date_range=DateRange(start_local, start_local + timedelta(hours=2)),
    )

    assert not banner.is_available(datetime(2026, 4, 10, 6, 59, tzinfo=timezone.utc))
    assert banner.is_available(datetime(2026, 4, 10, 7, 0, tzinfo=timezone.utc))
