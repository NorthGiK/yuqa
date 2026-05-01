"""Battle deck with exactly five unique card ids."""

from dataclasses import dataclass

from src.shared.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DeckSlots:
    """Immutable deck representation for five cards."""

    card_ids: tuple[int, int, int, int, int]

    def __post_init__(self) -> None:
        if len(self.card_ids) != 5:
            raise ValidationError("battle deck must contain exactly 5 cards")
        if len(set(self.card_ids)) != 5:
            raise ValidationError("battle deck cards must be unique")
        if any(card_id <= 0 for card_id in self.card_ids):
            raise ValidationError("card ids must be positive ints")
