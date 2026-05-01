"""Small immutable block with battle stats."""

from dataclasses import dataclass

from src.shared.errors import ValidationError


@dataclass(frozen=True, slots=True)
class StatBlock:
    """Damage, health, and defense bundle."""

    damage: int
    health: int
    defense: int

    def __post_init__(self) -> None:
        for name, value in (
            ("damage", self.damage),
            ("health", self.health),
            ("defense", self.defense),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValidationError(f"{name} must be a non-negative int")
