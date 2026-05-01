"""Shop purchase flow."""

from dataclasses import dataclass

from src.players.domain.entities import Player
from src.shop.domain.entities import ShopItem
from src.shared.errors import ForbiddenActionError, NotEnoughResourcesError


@dataclass(slots=True)
class ShopService:
    """Buy one shop item for a player."""

    def purchase(self, player: Player, item: ShopItem) -> None:
        """Transfer the cost and reward between wallets."""

        if not item.is_active:
            raise ForbiddenActionError("item is inactive")
        if not player.wallet.can_spend(item.buy_resource_type, item.price):
            raise NotEnoughResourcesError("Не достаточно ресурсов")
        player.wallet.spend(item.buy_resource_type, item.price)
        player.wallet.add(item.sell_resource_type, item.quantity)
