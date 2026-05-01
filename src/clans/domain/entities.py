"""Clan aggregate with membership and blacklist rules."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

MAX_CLAN_MEMBERS = 25


@dataclass(slots=True)
class Clan:
    """Clan state kept small on purpose."""

    id: int
    owner_player_id: int
    name: str
    icon: str
    rating: int = 0
    min_entry_rating: int = 0
    members: set[int] = field(default_factory=set)
    blacklist: set[int] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.members.add(self.owner_player_id)

    def is_full(self) -> bool:
        """Return True when the clan already reached the member cap."""

        return len(self.members) >= MAX_CLAN_MEMBERS

    def can_join(
        self, player_id: int, player_rating: int, player_clan_id: int | None
    ) -> bool:
        """Check whether a player may enter the clan."""

        return (
            player_clan_id is None
            and player_rating >= self.min_entry_rating
            and player_id not in self.blacklist
            and not self.is_full()
        )

    def add_member(self, player_id: int) -> None:
        """Add a member unless the clan is full."""

        if self.is_full():
            raise ValueError("clan is full")
        self.members.add(player_id)

    def remove_member(self, player_id: int) -> None:
        """Remove a member from the set."""

        self.members.discard(player_id)

    def add_to_blacklist(self, player_id: int) -> None:
        """Ban a player from joining the clan."""

        self.blacklist.add(player_id)

    def remove_from_blacklist(self, player_id: int) -> None:
        """Allow a player to join the clan again."""

        self.blacklist.discard(player_id)
