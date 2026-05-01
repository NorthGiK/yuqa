"""Orchestration layer used by Telegram handlers."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory

from src.banners.domain.services import BannerRollService
from src.battle_pass.domain.entities import BattlePassLevel, BattlePassSeason
from src.battles.domain.actions import BattleAction
from src.battles.domain.engine import BattleEngine
from src.cards.domain.services import CardProgressionService
from src.clans.domain.services import ClanService
from src.infrastructure.local import (
    CatalogStore,
    LocalBannerRepository,
    LocalBattlePassSeasonRepository,
    LocalCardTemplateRepository,
    LocalIdeaRepository,
    LocalPremiumBattlePassSeasonRepository,
    LocalProfileBackgroundRepository,
    LocalShopRepository,
)
from src.infrastructure.sqlalchemy.repositories import (
    PersistentBannerRepository,
    PersistentBattlePassProgressRepository,
    PersistentBattlePassSeasonRepository,
    PersistentBattleRepository,
    PersistentCardTemplateRepository,
    PersistentClanRepository,
    PersistentIdeaRepository,
    PersistentPlayerCardRepository,
    PersistentPlayerRepository,
    PersistentPremiumBattlePassProgressRepository,
    PersistentPremiumBattlePassSeasonRepository,
    PersistentProfileBackgroundRepository,
    PersistentQuestRepository,
    PersistentShopRepository,
    PersistentStateStore,
)
from src.ideas.domain.services import IdeaService
from src.quests.domain.entities import QuestReward
from src.quests.domain.services import QuestService
from src.shared.enums import IdeaStatus, Rarity, ResourceType
from src.shop.domain.services import ShopService
from src.telegram.services.contracts import (
    BannerRepositoryLike,
    BattlePassProgressRepositoryLike,
    BattlePassSeasonRepositoryLike,
    BattleRepositoryLike,
    BattleTimeoutNotifier,
    CardTemplateRepositoryLike,
    CatalogStoreLike,
    ClanRepositoryLike,
    IdeaRepositoryLike,
    PlayerCardRepositoryLike,
    PlayerRepositoryLike,
    ProfileBackgroundRepositoryLike,
    QuestRepositoryLike,
    ShopRepositoryLike,
)
from src.telegram.services.battle_pass import BattlePassServiceMixin
from src.telegram.services.battles import BattleServiceMixin
from src.telegram.services.content import ContentAdminServiceMixin
from src.telegram.services.players import (
    PlayerProfileServiceMixin,
    _FREE_CARD_RARITIES,
    _FREE_RESOURCE_TYPES,
)
from src.telegram.services.quests import QuestServiceMixin
from src.telegram.services.social import SocialServiceMixin


_DEFAULT_FREE_CARD_WEIGHTS = {
    Rarity.COMMON: 50,
    Rarity.RARE: 25,
    Rarity.EPIC: 15,
    Rarity.MYTHIC: 5,
    Rarity.LEGENDARY: 4,
    Rarity.GODLY: 1,
}
_DEFAULT_FREE_RESOURCE_WEIGHTS = {
    ResourceType.COINS: 50,
    ResourceType.CRYSTALS: 30,
    ResourceType.ORBS: 20,
}
_DEFAULT_FREE_RESOURCE_VALUES = {
    ResourceType.COINS: 1_000,
    ResourceType.CRYSTALS: 25,
    ResourceType.ORBS: 1,
}
_MAX_ACTION_EVENTS = 1_000


def _sqlite_url(path: Path) -> str:
    """Build a SQLite URL from a local filesystem path."""

    return f"sqlite:///{path.expanduser().resolve().as_posix()}"


class TelegramServices(
    BattleServiceMixin,
    BattlePassServiceMixin,
    PlayerProfileServiceMixin,
    SocialServiceMixin,
    ContentAdminServiceMixin,
    QuestServiceMixin,
):
    """Bundle repositories and domain services for the bot."""

    store: PersistentStateStore | None
    catalog: CatalogStoreLike | None
    players: PlayerRepositoryLike
    player_cards: PlayerCardRepositoryLike
    profile_backgrounds: ProfileBackgroundRepositoryLike
    clans: ClanRepositoryLike
    battles: BattleRepositoryLike
    card_templates: CardTemplateRepositoryLike
    banners: BannerRepositoryLike
    shop: ShopRepositoryLike
    ideas: IdeaRepositoryLike
    battle_pass_seasons: BattlePassSeasonRepositoryLike
    premium_battle_pass_seasons: BattlePassSeasonRepositoryLike
    battle_pass_progress: BattlePassProgressRepositoryLike
    premium_battle_pass_progress: BattlePassProgressRepositoryLike
    quests: QuestRepositoryLike
    quest_service: QuestService
    search_queue: dict[int, int]
    deck_drafts: dict[int, list[int]]
    action_events: list[tuple[int, str]]
    battle_action_drafts: dict[tuple[int, int, int], list[BattleAction]]
    battle_bonus_carryover: dict[tuple[int, int], int]
    battle_current_turn_player_ids: dict[int, int]
    battle_action_locks: dict[int, asyncio.Lock]
    battle_round_started_at: dict[int, datetime]
    battle_timeout_tasks: dict[int, asyncio.Task[None]]
    battle_inactive_rounds: dict[tuple[int, int], int]
    battle_round_timeout_seconds: float
    battle_inactive_round_limit: int
    enable_background_battle_timers: bool
    battle_timeout_notifier: BattleTimeoutNotifier | None
    free_card_weights: dict[Rarity, int]
    free_resource_weights: dict[ResourceType, int]
    free_resource_values: dict[ResourceType, int]
    _universes: list[str]
    _standard_cards: list[int]

    def __init__(
        self,
        content_path: str | Path | None = None,
        *,
        database_url: str | None = None,
    ) -> None:
        self._temporary_store_dir: TemporaryDirectory[str] | None = None
        content_file = Path(content_path) if content_path is not None else None
        runtime_database_url = database_url
        if runtime_database_url is None:
            self._temporary_store_dir = TemporaryDirectory(prefix="yuqa-services-")
            runtime_database_url = _sqlite_url(
                Path(self._temporary_store_dir.name) / "yuqa.db"
            )

        self.store = PersistentStateStore(
            runtime_database_url,
            content_file if database_url is not None else None,
        )
        self.catalog = (
            self.store
            if content_file is None or database_url is not None
            else CatalogStore(content_file)
        )
        content_is_database_backed = self.catalog is self.store

        self.players = PersistentPlayerRepository(self.store)
        self.player_cards = PersistentPlayerCardRepository(self.store)
        self.profile_backgrounds = (
            PersistentProfileBackgroundRepository(self.store)
            if content_is_database_backed
            else LocalProfileBackgroundRepository(self.catalog)
        )
        self.clans = PersistentClanRepository(self.store)
        self.battles = PersistentBattleRepository(self.store)
        self.card_progression = CardProgressionService()
        self.clan_service = ClanService()
        self.idea_service = IdeaService()
        self.shop_service = ShopService()
        self.banner_service = BannerRollService(rng=Random())
        self.battle_engine = BattleEngine()
        self.battle_pass_seasons = (
            PersistentBattlePassSeasonRepository(self.store)
            if content_is_database_backed
            else LocalBattlePassSeasonRepository(self.catalog)
        )
        self.premium_battle_pass_seasons = (
            PersistentPremiumBattlePassSeasonRepository(self.store)
            if content_is_database_backed
            else LocalPremiumBattlePassSeasonRepository(self.catalog)
        )
        self.battle_pass_progress = PersistentBattlePassProgressRepository(self.store)
        self.premium_battle_pass_progress = (
            PersistentPremiumBattlePassProgressRepository(self.store)
        )
        self.quests = PersistentQuestRepository(self.store)
        self.quest_service = QuestService()
        self.search_queue: dict[int, int] = self.store.search_queue
        self.deck_drafts: dict[int, list[int]] = self.store.deck_drafts
        self.action_events: list[tuple[int, str]] = self.store.action_events
        self.battle_action_drafts: dict[tuple[int, int, int], list[BattleAction]] = {}
        self.battle_bonus_carryover: dict[tuple[int, int], int] = {}
        self.battle_current_turn_player_ids: dict[int, int] = {}
        self.battle_action_locks: dict[int, asyncio.Lock] = {}
        self.battle_round_started_at: dict[int, datetime] = {}
        self.battle_timeout_tasks: dict[int, asyncio.Task[None]] = {}
        self.battle_inactive_rounds: dict[tuple[int, int], int] = {}
        self.battle_round_timeout_seconds = 15.0
        self.battle_inactive_round_limit = 10
        self.enable_background_battle_timers = False
        self.battle_timeout_notifier = None
        self.rng = Random()
        self.ideas = (
            PersistentIdeaRepository(self.store)
            if content_is_database_backed
            else LocalIdeaRepository(self.catalog)
        )
        self._clear_all_battles()
        self._universes = []
        self._standard_cards = []
        if content_is_database_backed:
            self.card_templates = PersistentCardTemplateRepository(self.store)
            self.banners = PersistentBannerRepository(self.store)
            self.shop = PersistentShopRepository(self.store)
        else:
            self.card_templates = LocalCardTemplateRepository(self.catalog)
            self.banners = LocalBannerRepository(self.catalog)
            self.shop = LocalShopRepository(self.catalog)
        self.free_card_weights = {
            rarity: _DEFAULT_FREE_CARD_WEIGHTS.get(rarity, 0)
            for rarity in _FREE_CARD_RARITIES
        }
        self.free_resource_weights = {
            resource: _DEFAULT_FREE_RESOURCE_WEIGHTS.get(resource, 0)
            for resource in _FREE_RESOURCE_TYPES
        }
        self.free_resource_values = {
            resource: _DEFAULT_FREE_RESOURCE_VALUES.get(resource, 0)
            for resource in _FREE_RESOURCE_TYPES
        }
        self._load_free_reward_settings()
        self._seed_battle_pass()
        self._seed_premium_battle_pass()

    async def flush(self) -> None:
        """Persist the current runtime and catalog state."""

        self.store.save()
        if self.catalog is not self.store and hasattr(self.catalog, "save"):
            self.catalog.save()

    async def shutdown(self) -> None:
        """Flush state and release storage resources."""

        self._clear_all_battles()
        await self.flush()
        self.store.close()
        if self._temporary_store_dir is not None:
            self._temporary_store_dir.cleanup()

    def configure_battle_timeout_notifier(
        self,
        notifier: BattleTimeoutNotifier,
    ) -> None:
        """Enable automatic round timers and use a notifier for timeout updates."""

        self.battle_timeout_notifier = notifier
        self.enable_background_battle_timers = True

    async def admin_counts(self) -> dict[str, int]:
        """Return a small admin dashboard snapshot."""

        ideas = await self.ideas.list_all()
        return {
            "players": len(self.players.items),
            "cards": len(self.card_templates.items),
            "profile_backgrounds": len(self.profile_backgrounds.items),
            "banners": len(self.banners.items),
            "shop": len(self.shop.items),
            "clans": len(self.clans.items),
            "standard_cards": len(await self.list_standard_cards()),
            "universes": len(await self.list_universes()),
            "battle_pass_levels": len(await self.list_battle_pass_levels()),
            "premium_battle_pass_levels": len(
                await self.list_premium_battle_pass_levels()
            ),
            "ideas_pending": sum(
                1 for idea in ideas if idea.status == IdeaStatus.PENDING
            ),
            "ideas_public": sum(
                1 for idea in ideas if idea.status == IdeaStatus.PUBLISHED
            ),
            "ideas_collection": sum(
                1 for idea in ideas if idea.status == IdeaStatus.COLLECTED
            ),
            "ideas_rejected": sum(
                1 for idea in ideas if idea.status == IdeaStatus.REJECTED
            ),
        }

    async def record_action(self, player_id: int, action: str) -> None:
        """Remember that a player performed an action."""

        self.action_events.append((player_id, action))
        self.action_events[:] = self.action_events[-_MAX_ACTION_EVENTS:]
        self._persist_runtime_state()
        await self.process_matchmaking()

    def _seed_battle_pass(self) -> None:
        """Create a default active battle pass season."""

        now = datetime.now(timezone.utc)
        season = BattlePassSeason(
            id=1,
            name="Сезон 1",
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=30),
            levels=[
                BattlePassLevel(1, 10, QuestReward(coins=50)),
                BattlePassLevel(2, 20, QuestReward(crystals=5)),
                BattlePassLevel(3, 30, QuestReward(orbs=1)),
            ],
        )
        if not self.battle_pass_seasons.items:
            self.battle_pass_seasons.items[1] = season
            self.store.save()

    def _seed_premium_battle_pass(self) -> None:
        """Create a default active premium battle pass season."""

        now = datetime.now(timezone.utc)
        season = BattlePassSeason(
            id=1,
            name="Премиум сезон 1",
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=30),
            levels=[
                BattlePassLevel(1, 10, QuestReward(coins=150)),
                BattlePassLevel(2, 20, QuestReward(crystals=15)),
                BattlePassLevel(3, 30, QuestReward(orbs=3)),
            ],
        )
        if not self.premium_battle_pass_seasons.items:
            self.premium_battle_pass_seasons.items[1] = season
            self.store.save()

    def _persist_runtime_state(self) -> None:
        """Flush runtime state to the backing store."""

        self.store.save()
