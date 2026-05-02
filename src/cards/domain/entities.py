"""Card templates and owned card progress."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.shared.enums import (
    AbilityStat,
    AbilityTarget,
    CardClass,
    CardForm,
    Rarity,
    Universe,
)
from src.shared.errors import ValidationError
from src.shared.value_objects.image_ref import ImageRef
from src.shared.value_objects.stat_block import StatBlock


@dataclass(frozen=True, slots=True)
class AbilityEffect:
    """Single stat modifier produced by an ability."""

    target: AbilityTarget
    stat: AbilityStat
    duration: int
    value: int

    def __post_init__(self) -> None:
        if self.duration < 0:
            raise ValidationError("duration must be >= 0")
        if self.value == 0:
            raise ValidationError("value must not be 0")


@dataclass(frozen=True, slots=True)
class Ability:
    """Ability with cost, cooldown, and a few effects."""

    cost: int
    cooldown: int
    effects: tuple[AbilityEffect, ...] = ()

    def __post_init__(self) -> None:
        if self.cost < 0 or self.cooldown < 0:
            raise ValidationError("cost and cooldown must be >= 0")


@dataclass(slots=True)
class CardTemplate:
    """Static template created by admins."""

    id: int
    name: str
    universe: Universe | str
    rarity: Rarity
    image: ImageRef
    card_class: CardClass
    base_stats: StatBlock
    ascended_stats: StatBlock
    ability: Ability
    ascended_ability: Ability | None = None
    is_available: bool = True

    def universe_value(self) -> str:
        """Return the universe as a plain string for presentation and storage."""

        return getattr(self.universe, "value", self.universe)

    def stats_for(self, form: CardForm) -> StatBlock:
        """Return the stat block for the requested form."""

        return self.ascended_stats if form == CardForm.ASCENDED else self.base_stats

    def ability_for(self, form: CardForm) -> Ability:
        """Return the ability for the requested form."""

        return (
            self.ascended_ability
            if form == CardForm.ASCENDED and self.ascended_ability
            else self.ability
        )


@dataclass(slots=True)
class PlayerCard:
    """Player-owned card with progression state."""

    id: int
    owner_player_id: int
    template_id: int
    level: int = 1
    copies_owned: int = 1
    is_ascended: bool = False
    current_form: CardForm = CardForm.BASE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    MAX_LEVEL = 10

    def __post_init__(self) -> None:
        if self.level < 1:
            raise ValidationError("level must be >= 1")
        if self.copies_owned < 0:
            raise ValidationError("copies_owned must be >= 0")
        if self.is_ascended and self.current_form != CardForm.ASCENDED:
            raise ValidationError("ascended card must be in ASCENDED form")

    def can_level_up(self) -> bool:
        """Return True when a level-up is available."""

        return self.level < self.MAX_LEVEL and self.copies_owned >= 1

    def can_ascend(self) -> bool:
        """Return True when the card can be ascended."""

        return (
            self.level >= self.MAX_LEVEL
            and self.copies_owned >= 1
            and not self.is_ascended
        )

    def level_up(self) -> None:
        """Spend one copy and increase the level."""

        if not self.can_level_up():
            raise ValidationError("card cannot level up")
        self.copies_owned -= 1
        self.level += 1
        self.updated_at = datetime.now(timezone.utc)

    def ascend(self) -> None:
        """Convert the card into ascended form."""

        if not self.can_ascend():
            raise ValidationError("card cannot ascend")
        self.is_ascended = True
        self.current_form = CardForm.ASCENDED
        self.updated_at = datetime.now(timezone.utc)

    def toggle_form(self) -> None:
        """Switch between base and ascended forms."""

        if not self.is_ascended:
            raise ValidationError("only ascended cards can switch form")
        self.current_form = (
            CardForm.BASE
            if self.current_form == CardForm.ASCENDED
            else CardForm.ASCENDED
        )
        self.updated_at = datetime.now(timezone.utc)
