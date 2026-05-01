"""Idea entities for player-created game mechanics."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.shared.enums import IdeaStatus


@dataclass(slots=True)
class Idea:
    """Player-submitted mechanic idea with one-shot voting."""

    id: int
    player_id: int
    title: str
    description: str
    status: IdeaStatus = IdeaStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    votes: dict[int, int] = field(default_factory=dict)

    @property
    def upvotes(self) -> int:
        """Return the number of positive votes."""

        return sum(1 for value in self.votes.values() if value > 0)

    @property
    def downvotes(self) -> int:
        """Return the number of negative votes."""

        return sum(1 for value in self.votes.values() if value < 0)

    def vote_of(self, player_id: int) -> int | None:
        """Return the current player's vote, if any."""

        return self.votes.get(player_id)
