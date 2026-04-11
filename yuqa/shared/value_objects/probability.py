"""Lightweight weight object for random pools."""

from dataclasses import dataclass

from yuqa.shared.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ProbabilityWeight:
    """Strictly positive selection weight."""

    weight: int

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValidationError("weight must be an int > 0")
