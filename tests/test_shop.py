"""Tests for shop purchases."""

import pytest

from src.players.domain.entities import Player
from src.shop.domain.entities import ShopItem
from src.shop.domain.services import ShopService
from src.shared.enums import ResourceType
from src.shared.errors import NotEnoughResourcesError, ValidationError
from src.shared.value_objects.resource_wallet import ResourceWallet


def test_shop_purchase():
    player = Player(telegram_id=1, wallet=ResourceWallet(coins=100))
    item = ShopItem(
        id=1,
        sell_resource_type=ResourceType.CRYSTALS,
        buy_resource_type=ResourceType.COINS,
        price=50,
        quantity=3,
    )
    ShopService().purchase(player, item)
    assert player.wallet.coins == 50 and player.wallet.crystals == 3


def test_shop_item_validation():
    with pytest.raises(ValidationError):
        ShopItem(
            id=1,
            sell_resource_type=ResourceType.CRYSTALS,
            buy_resource_type=ResourceType.COINS,
            price=0,
            quantity=1,
        )
    with pytest.raises(NotEnoughResourcesError):
        ShopService().purchase(
            Player(telegram_id=1),
            ShopItem(
                id=1,
                sell_resource_type=ResourceType.CRYSTALS,
                buy_resource_type=ResourceType.COINS,
                price=50,
                quantity=1,
            ),
        )
