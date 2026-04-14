"""Player aggregate used by several game flows."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import random

from yuqa.shared.enums import ProfileBackgroundRarity
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.shared.value_objects.resource_wallet import ResourceWallet


@dataclass(slots=True)
class Player:
    """Telegram player profile and economy state."""

    telegram_id: int
    rating: int = 0
    is_banned: bool = False
    is_premium: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    wins: int = 0
    losses: int = 0
    draws: int = 0
    wallet: ResourceWallet = field(default_factory=ResourceWallet)
    collection_count: int = 0
    battle_deck: DeckSlots | None = None
    battle_pass_progress: list[int] = field(default_factory=list)
    clan_id: int | None = None
    last_free_card_claim_at: datetime | None = None
    last_free_resources_claim_at: datetime | None = None
    nickname: str | None = None
    title: str | None = None
    creator_points: int = 0
    owned_profile_background_ids: list[int] = field(default_factory=list)
    selected_profile_background_id: int | None = None

    def add_win(self) -> None:
        """Increase wins and rating."""

        self.wins += 1
        self.rating += 30 + random.randint(0, 5) 

    def add_loss(self) -> None:
        """Increase losses and lower rating a bit."""

        self.losses += 1
        self.rating = max(0, self.rating - 35 - random.randint(0, 5))

    def add_draw(self) -> None:
        """Increase draws and reward a small rating boost."""

        self.draws += 1
        self.rating -= random.randint(0, 5)

    def owns_profile_background(self, background_id: int) -> bool:
        """Return True when the player owns the background."""

        return background_id in self.owned_profile_background_ids

    def grant_profile_background(self, background_id: int) -> bool:
        """Grant one profile background if the player does not own it yet."""

        if self.owns_profile_background(background_id):
            return False
        self.owned_profile_background_ids.append(background_id)
        self.owned_profile_background_ids.sort()
        if self.selected_profile_background_id is None:
            self.selected_profile_background_id = background_id
        return True

    def select_profile_background(self, background_id: int | None) -> None:
        """Choose one owned background or clear the current selection."""

        if background_id is None:
            self.selected_profile_background_id = None
            return
        if not self.owns_profile_background(background_id):
            raise ValueError("player does not own this profile background")
        self.selected_profile_background_id = background_id


@dataclass(slots=True, frozen=True)
class ProfileBackgroundTemplate:
    """Static profile-background definition created by admins."""

    id: int
    rarity: ProfileBackgroundRarity
    media: ImageRef


@dataclass(slots=True, frozen=True)
class PlayerTopEntry:
    """One leaderboard row."""

    rank: int
    player: Player
    value: int
