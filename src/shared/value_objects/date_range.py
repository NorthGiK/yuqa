"""Simple half-open date range helper."""

from dataclasses import dataclass
from datetime import datetime, timezone

from src.shared.errors import ValidationError


def _plain(moment: datetime) -> datetime:
    """Normalize to comparable naive UTC while preserving absolute time."""

    if moment.tzinfo is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True, slots=True)
class DateRange:
    """Date range that can be open on either side."""

    start_at: datetime | None = None
    end_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            self.start_at
            and self.end_at
            and _plain(self.start_at) >= _plain(self.end_at)
        ):
            raise ValidationError("start_at must be before end_at")

    def contains(self, moment: datetime) -> bool:
        """Return True when a moment is inside the range."""

        moment = _plain(moment)
        if self.start_at and moment < _plain(self.start_at):
            return False
        if self.end_at and moment > _plain(self.end_at):
            return False
        return True
