"""Shop item definition."""

from dataclasses import dataclass

from src.shared.enums import ResourceType
from src.shared.errors import ValidationError


@dataclass(slots=True)
class ShopItem:
    """Admin-configured item with a price and a reward."""

    id: int
    sell_resource_type: ResourceType
    buy_resource_type: ResourceType
    price: int
    quantity: int
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.price <= 0 or self.quantity <= 0:
            raise ValidationError("price and quantity must be > 0")
