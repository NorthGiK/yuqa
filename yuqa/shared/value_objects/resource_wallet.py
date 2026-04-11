"""Wallet with the game's resource counters."""

from dataclasses import dataclass

from yuqa.shared.enums import ResourceType
from yuqa.shared.errors import NotEnoughResourcesError, ValidationError


@dataclass(slots=True)
class ResourceWallet:
    """Mutable wallet that stores all currencies in one place."""

    coins: int = 0
    crystals: int = 0
    orbs: int = 0
    silver_tickets: int = 0
    gold_tickets: int = 0

    def __post_init__(self) -> None:
        for name in ("coins", "crystals", "orbs", "silver_tickets", "gold_tickets"):
            if getattr(self, name) < 0:
                raise ValidationError(f"{name} must be a non-negative int")

    def get(self, resource: ResourceType) -> int:
        """Return the current amount of one resource."""

        return getattr(self, resource.value)

    def can_spend(self, resource: ResourceType, amount: int) -> bool:
        """Check that the wallet can pay the requested amount."""

        return amount >= 0 and self.get(resource) >= amount

    def add(self, resource: ResourceType, amount: int) -> None:
        """Increase a resource counter."""

        if amount < 0:
            raise ValidationError("amount must be >= 0")
        setattr(self, resource.value, self.get(resource) + amount)

    def spend(self, resource: ResourceType, amount: int) -> None:
        """Decrease a resource counter."""

        if amount < 0:
            raise ValidationError("amount must be >= 0")
        current = self.get(resource)
        if current < amount:
            raise NotEnoughResourcesError(f"Не достаточно {resource.value}")
        setattr(self, resource.value, current - amount)
