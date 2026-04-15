"""Orchestration layer used by Telegram handlers."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random

from yuqa.banners.domain.entities import Banner, BannerReward
from yuqa.banners.domain.services import BannerRollService
from yuqa.battle_pass.domain.entities import (
    BattlePassLevel,
    BattlePassProgress,
    BattlePassSeason,
)
from yuqa.battles.domain.engine import BattleEngine
from yuqa.battles.domain.actions import (
    AttackAction,
    BattleAction,
    BlockAction,
    BonusAction,
    SwitchCardAction,
    UseAbilityAction,
)
from yuqa.battles.domain.entities import Battle, BattleCardState, BattleSide
from yuqa.cards.domain.entities import Ability, CardTemplate, PlayerCard
from yuqa.cards.domain.services import CardProgressionService
from yuqa.clans.domain.entities import Clan
from yuqa.clans.domain.services import ClanService
from yuqa.infrastructure.local import (
    CatalogStore,
    LocalBannerRepository,
    LocalBattlePassSeasonRepository,
    LocalPremiumBattlePassSeasonRepository,
    LocalCardTemplateRepository,
    LocalIdeaRepository,
    LocalShopRepository,
)
from yuqa.infrastructure.local import LocalProfileBackgroundRepository
from yuqa.infrastructure.memory import (
    InMemoryBannerRepository,
    InMemoryBattlePassProgressRepository,
    InMemoryBattlePassSeasonRepository,
    InMemoryPremiumBattlePassProgressRepository,
    InMemoryPremiumBattlePassSeasonRepository,
    InMemoryBattleRepository,
    InMemoryCardTemplateRepository,
    InMemoryClanRepository,
    InMemoryIdeaRepository,
    InMemoryProfileBackgroundRepository,
    InMemoryPlayerCardRepository,
    InMemoryPlayerRepository,
    InMemoryShopRepository,
)
from yuqa.infrastructure.sqlalchemy.repositories import (
    PersistentBannerRepository,
    PersistentBattlePassProgressRepository,
    PersistentBattlePassSeasonRepository,
    PersistentPremiumBattlePassProgressRepository,
    PersistentPremiumBattlePassSeasonRepository,
    PersistentBattleRepository,
    PersistentCardTemplateRepository,
    PersistentClanRepository,
    PersistentIdeaRepository,
    PersistentPlayerCardRepository,
    PersistentPlayerRepository,
    PersistentProfileBackgroundRepository,
    PersistentShopRepository,
    PersistentStateStore,
)
from yuqa.ideas.domain.entities import Idea
from yuqa.ideas.domain.services import IdeaService
from yuqa.players.domain.entities import (
    Player,
    PlayerTopEntry,
    ProfileBackgroundTemplate,
)
from yuqa.quests.domain.entities import QuestReward
from yuqa.shared.enums import (
    BannerType,
    BattleActionType,
    CardClass,
    CardForm,
    IdeaStatus,
    ProfileBackgroundRarity,
    Rarity,
    ResourceType,
    RewardType,
    Universe,
)
from yuqa.shared.errors import (
    BattleRuleViolationError,
    EntityNotFoundError,
    ForbiddenActionError,
    ValidationError,
)
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.shared.value_objects.date_range import DateRange
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.shop.domain.entities import ShopItem
from yuqa.shop.domain.services import ShopService


_FREE_CARD_RARITIES = (
    Rarity.COMMON,
    Rarity.RARE,
    Rarity.EPIC,
    Rarity.MYTHIC,
    Rarity.LEGENDARY,
    Rarity.GODLY,
)
_FREE_RESOURCE_TYPES = (
    ResourceType.COINS,
    ResourceType.CRYSTALS,
    ResourceType.ORBS,
)
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
_FREE_REWARD_COOLDOWN = timedelta(hours=2)
_NICKNAME_RE = re.compile(r"^[\w]{3,24}$", re.UNICODE)
_MAX_TITLE_LENGTH = 60
_TOP_MODES = {"rating", "badenko_cards", "creator_points"}
_MAX_ACTION_EVENTS = 1_000


@dataclass(slots=True)
class BattleRoundSummary:
    """Compact snapshot of a player's current battle choices."""

    attack_count: int
    block_count: int
    bonus_count: int
    ability_used: bool
    available_action_points: int
    opponent_action_points: int
    ability_cost: int
    can_switch: bool


def _next_id(items) -> int:
    """Return the next numeric identifier for a repository mapping."""

    return max(items, default=0) + 1


class TelegramServices:
    """Bundle repositories and domain services for the bot."""

    def __init__(
        self,
        content_path: str | Path | None = None,
        *,
        database_url: str | None = None,
    ) -> None:
        self.store = (
            PersistentStateStore(database_url, content_path) if database_url else None
        )
        self.catalog = (
            self.store
            if self.store is not None
            else CatalogStore(Path(content_path))
            if content_path
            else None
        )
        self.players = (
            PersistentPlayerRepository(self.store)
            if self.store is not None
            else InMemoryPlayerRepository()
        )
        self.player_cards = (
            PersistentPlayerCardRepository(self.store)
            if self.store is not None
            else InMemoryPlayerCardRepository()
        )
        self.profile_backgrounds = (
            PersistentProfileBackgroundRepository(self.store)
            if self.store is not None
            else LocalProfileBackgroundRepository(self.catalog)
            if self.catalog
            else InMemoryProfileBackgroundRepository()
        )
        self.clans = (
            PersistentClanRepository(self.store)
            if self.store is not None
            else InMemoryClanRepository()
        )
        self.battles = (
            PersistentBattleRepository(self.store)
            if self.store is not None
            else InMemoryBattleRepository()
        )
        self.card_progression = CardProgressionService()
        self.clan_service = ClanService()
        self.idea_service = IdeaService()
        self.shop_service = ShopService()
        self.banner_service = BannerRollService(rng=Random())
        self.battle_engine = BattleEngine()
        self.battle_pass_seasons = (
            PersistentBattlePassSeasonRepository(self.store)
            if self.store is not None
            else LocalBattlePassSeasonRepository(self.catalog)
            if self.catalog
            else InMemoryBattlePassSeasonRepository()
        )
        self.premium_battle_pass_seasons = (
            PersistentPremiumBattlePassSeasonRepository(self.store)
            if self.store is not None
            else LocalPremiumBattlePassSeasonRepository(self.catalog)
            if self.catalog
            else InMemoryPremiumBattlePassSeasonRepository()
        )
        self.battle_pass_progress = (
            PersistentBattlePassProgressRepository(self.store)
            if self.store is not None
            else InMemoryBattlePassProgressRepository()
        )
        self.premium_battle_pass_progress = (
            PersistentPremiumBattlePassProgressRepository(self.store)
            if self.store is not None
            else InMemoryPremiumBattlePassProgressRepository()
        )
        self.search_queue: dict[int, int] = (
            self.store.search_queue if self.store is not None else {}
        )
        self.deck_drafts: dict[int, list[int]] = (
            self.store.deck_drafts if self.store is not None else {}
        )
        self.action_events: list[tuple[int, str]] = (
            self.store.action_events if self.store is not None else []
        )
        self.battle_action_drafts: dict[tuple[int, int, int], list[BattleAction]] = {}
        self.rng = Random()
        self.ideas = (
            PersistentIdeaRepository(self.store)
            if self.store is not None
            else LocalIdeaRepository(self.catalog)
            if self.catalog
            else InMemoryIdeaRepository()
        )
        self._clear_all_battles()
        if self.store is not None:
            self.card_templates = PersistentCardTemplateRepository(self.store)
            self.banners = PersistentBannerRepository(self.store)
            self.shop = PersistentShopRepository(self.store)
        elif self.catalog is None:
            self.card_templates = InMemoryCardTemplateRepository()
            self.banners = InMemoryBannerRepository()
            self.shop = InMemoryShopRepository()
            self._universes = [
                item.value
                for item in Universe
                if item.value not in {"unknown", "other"}
            ]
        else:
            self.card_templates = LocalCardTemplateRepository(self.catalog)
            self.banners = LocalBannerRepository(self.catalog)
            self.shop = LocalShopRepository(self.catalog)
        self.free_card_weights = dict(_DEFAULT_FREE_CARD_WEIGHTS)
        self.free_resource_weights = dict(_DEFAULT_FREE_RESOURCE_WEIGHTS)
        self.free_resource_values = dict(_DEFAULT_FREE_RESOURCE_VALUES)
        self._load_free_reward_settings()
        self._seed_battle_pass()
        self._seed_premium_battle_pass()

    # Public lookups -----------------------------------------------------

    async def flush(self) -> None:
        """Persist the current in-memory state when durable storage is active."""

        if self.store is not None:
            self.store.save()
        elif self.catalog is not None and hasattr(self.catalog, "save"):
            self.catalog.save()

    async def shutdown(self) -> None:
        """Flush state and release storage resources."""

        self._clear_all_battles()
        await self.flush()
        if self.store is not None:
            self.store.close()

    async def get_or_create_player(self, telegram_id: int) -> Player:
        """Return an existing player or create a fresh one."""

        player = await self.players.get_by_telegram_id(telegram_id)
        if player is None:
            player = Player(telegram_id=telegram_id)
            await self.players.add(player)
            await self._grant_standard_cards(player)
            await self.players.save(player)
        return player

    async def get_player(self, telegram_id: int) -> Player | None:
        """Return a player without creating one."""

        return await self.players.get_by_id(telegram_id)

    async def player_clan(self, player: Player) -> Clan | None:
        """Return the clan that belongs to the player."""

        return (
            None
            if player.clan_id is None
            else await self.clans.get_by_id(player.clan_id)
        )

    async def clan_members(self, clan: Clan | None) -> list[Player]:
        """Return resolved clan members ordered by telegram id."""

        if clan is None:
            return []
        members: list[Player] = []
        for member_id in sorted(clan.members):
            player = await self.players.get_by_id(member_id)
            if player is not None:
                members.append(player)
        return members

    async def list_player_cards(self, telegram_id: int) -> list[PlayerCard]:
        """Return every card owned by a player."""

        return await self.player_cards.list_by_owner(telegram_id)

    async def get_profile_background(
        self, background_id: int
    ) -> ProfileBackgroundTemplate | None:
        """Return a profile background template by id."""

        return await self.profile_backgrounds.get_by_id(background_id)

    async def list_profile_backgrounds(self) -> list[ProfileBackgroundTemplate]:
        """Return every stored profile background template."""

        return list(await self.profile_backgrounds.list_all())

    async def list_player_profile_backgrounds(
        self, telegram_id: int
    ) -> list[ProfileBackgroundTemplate]:
        """Return the profile backgrounds owned by a player."""

        player = await self.get_or_create_player(telegram_id)
        items: list[ProfileBackgroundTemplate] = []
        for background_id in player.owned_profile_background_ids:
            background = await self.profile_backgrounds.get_by_id(background_id)
            if background is not None:
                items.append(background)
        return items

    async def selected_profile_background_for_player(
        self, player: Player
    ) -> ProfileBackgroundTemplate | None:
        """Resolve the active profile background for a player."""

        if player.selected_profile_background_id is None:
            return None
        return await self.profile_backgrounds.get_by_id(
            player.selected_profile_background_id
        )

    async def list_active_shop_items(self) -> list[ShopItem]:
        """Return the visible shop catalog."""

        return await self.shop.list_active()

    async def list_available_banners(self) -> list[Banner]:
        """Return the banners that are currently available."""

        return await self.banners.list_available()

    async def list_card_templates(self) -> list[CardTemplate]:
        """Return every stored card template."""

        return list(self.card_templates.items.values())

    async def list_universes(self) -> list[str]:
        """Return the current universe catalog."""

        if self.catalog is None:
            return list(self._universes)
        return list(self.catalog.universes)

    async def list_standard_cards(self) -> list[int]:
        """Return the starter card template ids."""

        return list(self._read_standard_cards())

    async def active_battle_pass(self) -> BattlePassSeason | None:
        """Return the currently active battle pass season."""

        now = datetime.now(timezone.utc)
        seasons = [
            season
            for season in await self.battle_pass_seasons.list_active()
            if season.is_active and season.start_at <= now <= season.end_at
        ]
        if not seasons:
            return None
        return sorted(seasons, key=lambda season: (season.start_at, season.id))[-1]

    async def list_battle_pass_seasons(self) -> list[BattlePassSeason]:
        """Return every stored battle pass season sorted by dates."""

        seasons: list[BattlePassSeason] = list(
            getattr(self.battle_pass_seasons, "items", {}).values()
        )
        return sorted(
            seasons, key=lambda season: (season.start_at, season.id), reverse=True
        )

    async def create_battle_pass_season(
        self,
        name: str,
        start_at: datetime,
        end_at: datetime,
    ) -> BattlePassSeason:
        """Create a new battle pass season with explicit dates."""

        if not name.strip():
            raise ValidationError("battle pass name must not be empty")
        if start_at >= end_at:
            raise ValidationError("start_at must be before end_at")
        seasons = await self.list_battle_pass_seasons()
        for season in seasons:
            if start_at <= season.end_at and end_at >= season.start_at:
                raise ForbiddenActionError(
                    "battle pass dates overlap with an existing season"
                )
        season = BattlePassSeason(
            id=_next_id(getattr(self.battle_pass_seasons, "items", {})),
            name=name.strip(),
            start_at=start_at,
            end_at=end_at,
            levels=[],
            is_active=True,
        )
        await self.battle_pass_seasons.save(season)
        return season

    async def delete_battle_pass_season(self, season_id: int) -> None:
        """Delete an ended battle pass season."""

        season = await self.battle_pass_seasons.get_by_id(season_id)
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        if season.end_at > datetime.now(timezone.utc):
            raise ForbiddenActionError("battle pass is not finished yet")
        await self.battle_pass_seasons.delete(season_id)

    async def active_premium_battle_pass(self) -> BattlePassSeason | None:
        """Return the currently active premium battle pass season."""

        now = datetime.now(timezone.utc)
        seasons = [
            season
            for season in await self.premium_battle_pass_seasons.list_active()
            if season.is_active and season.start_at <= now <= season.end_at
        ]
        if not seasons:
            return None
        return sorted(seasons, key=lambda season: (season.start_at, season.id))[-1]

    async def list_premium_battle_pass_seasons(self) -> list[BattlePassSeason]:
        """Return every stored premium battle pass season sorted by dates."""

        seasons: list[BattlePassSeason] = list(
            getattr(self.premium_battle_pass_seasons, "items", {}).values()
        )
        return sorted(
            seasons, key=lambda season: (season.start_at, season.id), reverse=True
        )

    async def create_premium_battle_pass_season(
        self,
        name: str,
        start_at: datetime,
        end_at: datetime,
    ) -> BattlePassSeason:
        """Create a new premium battle pass season with explicit dates."""

        if not name.strip():
            raise ValidationError("battle pass name must not be empty")
        if start_at >= end_at:
            raise ValidationError("start_at must be before end_at")
        seasons = await self.list_premium_battle_pass_seasons()
        for season in seasons:
            if start_at <= season.end_at and end_at >= season.start_at:
                raise ForbiddenActionError(
                    "battle pass dates overlap with an existing season"
                )
        season = BattlePassSeason(
            id=_next_id(getattr(self.premium_battle_pass_seasons, "items", {})),
            name=name.strip(),
            start_at=start_at,
            end_at=end_at,
            levels=[],
            is_active=True,
        )
        await self.premium_battle_pass_seasons.save(season)
        return season

    async def delete_premium_battle_pass_season(self, season_id: int) -> None:
        """Delete an ended premium battle pass season."""

        season = await self.premium_battle_pass_seasons.get_by_id(season_id)
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        if season.end_at > datetime.now(timezone.utc):
            raise ForbiddenActionError("battle pass is not finished yet")
        await self.premium_battle_pass_seasons.delete(season_id)

    async def free_rewards_status(self, telegram_id: int) -> dict[str, object]:
        """Return cooldown and configuration data for the free rewards screen."""

        player = await self.get_or_create_player(telegram_id)
        now = datetime.now(timezone.utc)
        card_ready_at = self._next_free_reward_time(player.last_free_card_claim_at)
        resource_ready_at = self._next_free_reward_time(
            player.last_free_resources_claim_at
        )
        return {
            "card_ready_at": card_ready_at,
            "resource_ready_at": resource_ready_at,
            "card_ready": card_ready_at <= now,
            "resource_ready": resource_ready_at <= now,
            "settings": self.free_reward_settings(),
        }

    def free_reward_settings(self) -> dict[str, dict[str, int]]:
        """Return the current free reward settings in a text-friendly shape."""

        return {
            "card_weights": {
                rarity.value: self.free_card_weights.get(rarity, 0)
                for rarity in _FREE_CARD_RARITIES
            },
            "resource_weights": {
                resource.value: self.free_resource_weights.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
            "resource_values": {
                resource.value: self.free_resource_values.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
            "cooldown_seconds": {"value": int(_FREE_REWARD_COOLDOWN.total_seconds())},
        }

    async def claim_free_card(
        self, telegram_id: int
    ) -> tuple[PlayerCard, CardTemplate]:
        """Grant one free random card if the cooldown is ready."""

        player = await self.get_or_create_player(telegram_id)
        self._ensure_free_reward_ready(player.last_free_card_claim_at)
        templates = await self.card_templates.list_active()
        templates_by_rarity = {
            rarity: [template for template in templates if template.rarity == rarity]
            for rarity in _FREE_CARD_RARITIES
        }
        available_weights = {
            rarity: self.free_card_weights[rarity]
            for rarity, items in templates_by_rarity.items()
            if items and self.free_card_weights.get(rarity, 0) > 0
        }
        if not available_weights:
            raise ValidationError("нет доступных карт для бесплатной награды")
        chosen_rarity = self._pick_weighted(available_weights)
        template = self.rng.choice(templates_by_rarity[chosen_rarity])
        card = await self._grant_template_to_player(player, template)
        player.last_free_card_claim_at = datetime.now(timezone.utc)
        await self.players.save(player)
        return card, template

    async def claim_free_resources(self, telegram_id: int) -> tuple[ResourceType, int]:
        """Grant one free random resource if the cooldown is ready."""

        player = await self.get_or_create_player(telegram_id)
        self._ensure_free_reward_ready(player.last_free_resources_claim_at)
        weights = {
            resource: self.free_resource_weights[resource]
            for resource in _FREE_RESOURCE_TYPES
            if self.free_resource_weights.get(resource, 0) > 0
        }
        if not weights:
            raise ValidationError("нет доступных ресурсов для бесплатной награды")
        resource = self._pick_weighted(weights)
        amount = self.free_resource_values.get(resource, 0)
        if amount <= 0:
            raise ValidationError(f"value for {resource.value} must be > 0")
        player.wallet.add(resource, amount)
        player.last_free_resources_claim_at = datetime.now(timezone.utc)
        await self.players.save(player)
        return resource, amount

    async def set_player_nickname(
        self, telegram_id: int, nickname: str | None
    ) -> Player:
        """Set or clear the player's unique nickname."""

        player = await self.get_or_create_player(telegram_id)
        nickname = self._normalize_nickname(nickname)
        if nickname is not None:
            other = await self.players.get_by_nickname(nickname)
            if other is not None and other.telegram_id != player.telegram_id:
                raise ValidationError("nickname is already taken")
        player.nickname = nickname
        await self.players.save(player)
        return player

    async def set_player_title(self, telegram_id: int, title: str | None) -> Player:
        """Set or clear the player's title."""

        player = await self.get_or_create_player(telegram_id)
        player.title = self._normalize_title(title)
        await self.players.save(player)
        return player

    async def add_creator_points(self, telegram_id: int, amount: int) -> Player:
        """Increase creator points for a player by id."""

        if amount <= 0:
            raise ValidationError("creator points amount must be > 0")
        player = await self.get_or_create_player(telegram_id)
        player.creator_points += amount
        await self.players.save(player)
        return player

    async def set_player_premium(self, telegram_id: int, is_premium: bool) -> Player:
        """Set premium status for an existing player."""

        player = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")
        player.is_premium = is_premium
        await self.players.save(player)
        return player

    async def toggle_player_premium(self, telegram_id: int) -> Player:
        """Toggle premium status for an existing player."""

        player = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")
        player.is_premium = not player.is_premium
        await self.players.save(player)
        return player

    async def delete_player(self, telegram_id: int) -> Player:
        """Delete a player and clean up related runtime state."""

        player: Player | None = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")

        clan: Clan | None = await self.player_clan(player)
        if clan is not None:
            clan.remove_member(telegram_id)
            if clan.owner_player_id == telegram_id:
                for member_id in list(clan.members):
                    if member_id == telegram_id:
                        continue
                    member: Player | None = await self.players.get_by_id(member_id)
                    if member is not None:
                        member.clan_id = None
                        await self.players.save(member)
                await self.clans.delete(clan.id)
            else:
                await self.clans.save(clan)

        for card_id, player_card in list(self.player_cards.items.items()):
            if player_card.owner_player_id == telegram_id:
                await self.player_cards.delete(card_id)

        for battle_pass_key in list(self.battle_pass_progress.items):
            if battle_pass_key[0] == telegram_id:
                await self.battle_pass_progress.delete(battle_pass_key)
        for battle_pass_key in list(self.premium_battle_pass_progress.items):
            if battle_pass_key[0] == telegram_id:
                await self.premium_battle_pass_progress.delete(battle_pass_key)

        for battle_id, battle in list(self.battles.items.items()):
            if telegram_id in {battle.player_one_id, battle.player_two_id}:
                await self.battles.delete(battle_id)
                self._clear_battle_round_drafts(battle_id)

        self.search_queue.pop(telegram_id, None)
        self.deck_drafts.pop(telegram_id, None)
        self.action_events[:] = [
            event for event in self.action_events if event[0] != telegram_id
        ]

        await self.players.delete(telegram_id)
        self._persist_runtime_state()
        return player

    async def propose_idea(
        self, telegram_id: int, title: str, description: str
    ) -> Idea:
        """Create a new player proposal that waits for admin review."""

        player = await self.get_or_create_player(telegram_id)
        idea = self.idea_service.create(
            _next_id(self.ideas.items),
            player.telegram_id,
            title,
            description,
        )
        await self.ideas.add(idea)
        return idea

    async def get_idea(self, idea_id: int) -> Idea:
        """Return one idea or raise when it is missing."""

        idea = await self.ideas.get_by_id(idea_id)
        if idea is None:
            raise EntityNotFoundError("idea not found")
        return idea

    async def list_ideas(
        self,
        status: IdeaStatus,
        *,
        page: int = 1,
        page_size: int = 10,
        player_id: int | None = None,
    ) -> tuple[list[Idea], bool, bool]:
        """Return one paginated idea slice for the requested status."""

        if page < 1:
            page = 1
        ideas = [
            idea
            for idea in await self.ideas.list_all()
            if idea.status == status
            and (player_id is None or idea.player_id == player_id)
        ]
        ideas = self._sort_ideas(ideas)
        start = (page - 1) * page_size
        end = start + page_size
        return ideas[start:end], page > 1, end < len(ideas)

    async def idea_author(self, idea: Idea) -> Player | None:
        """Resolve the player who proposed the idea."""

        return await self.get_player(idea.player_id)

    async def player_vote_for_idea(self, idea_id: int, telegram_id: int) -> int | None:
        """Return the player's recorded vote for an idea."""

        idea = await self.get_idea(idea_id)
        return idea.vote_of(telegram_id)

    async def vote_for_idea(
        self, telegram_id: int, idea_id: int, direction: int
    ) -> Idea:
        """Cast one upvote or downvote for a published idea."""

        await self.get_or_create_player(telegram_id)
        idea = await self.get_idea(idea_id)
        self.idea_service.vote(idea, telegram_id, direction)
        await self.ideas.save(idea)
        return idea

    async def publish_idea(self, idea_id: int) -> Idea:
        """Accept a pending idea onto the public ideas page."""

        idea = await self.get_idea(idea_id)
        self.idea_service.publish(idea)
        await self.ideas.save(idea)
        return idea

    async def collect_idea(self, idea_id: int) -> Idea:
        """Accept a public idea into the author's collection."""

        idea = await self.get_idea(idea_id)
        self.idea_service.collect(idea)
        await self.ideas.save(idea)
        return idea

    async def reject_idea(self, idea_id: int) -> Idea:
        """Archive an idea away from the public ideas page."""

        idea = await self.get_idea(idea_id)
        self.idea_service.reject(idea)
        await self.ideas.save(idea)
        return idea

    async def create_profile_background(
        self,
        rarity: ProfileBackgroundRarity,
        media_key: str,
        *,
        content_type: str = "image/png",
        original_name: str | None = None,
    ) -> ProfileBackgroundTemplate:
        """Create and persist a new profile background template."""

        background = ProfileBackgroundTemplate(
            id=_next_id(self.profile_backgrounds.items),
            rarity=rarity,
            media=ImageRef(
                media_key,
                content_type=content_type,
                original_name=original_name,
            ),
        )
        await self.profile_backgrounds.add(background)
        return background

    async def select_profile_background(
        self, telegram_id: int, background_id: int | None
    ) -> Player:
        """Choose one owned profile background or clear the selection."""

        player = await self.get_or_create_player(telegram_id)
        if background_id is not None:
            background = await self.profile_backgrounds.get_by_id(background_id)
            if background is None:
                raise EntityNotFoundError("profile background not found")
        try:
            player.select_profile_background(background_id)
        except ValueError as error:
            raise ForbiddenActionError(
                "profile background is not in your collection"
            ) from error
        await self.players.save(player)
        return player

    async def list_top_players(
        self, mode: str, limit: int = 10
    ) -> list[PlayerTopEntry]:
        """Return a leaderboard sorted by the requested metric."""

        if mode not in _TOP_MODES:
            raise ValidationError("unknown top mode")
        players = await self.players.list_all()
        values: dict[int, int] = {}
        for player in players:
            if mode == "rating":
                values[player.telegram_id] = player.rating
            elif mode == "creator_points":
                values[player.telegram_id] = player.creator_points
            else:
                values[player.telegram_id] = await self._badenko_card_count(
                    player.telegram_id
                )
        ranked = sorted(
            players,
            key=lambda player: (
                values[player.telegram_id],
                player.rating,
                -player.telegram_id,
            ),
            reverse=True,
        )[:limit]
        return [
            PlayerTopEntry(rank=index, player=player, value=values[player.telegram_id])
            for index, player in enumerate(ranked, start=1)
        ]

    async def set_free_card_weights(
        self, weights: dict[Rarity, int]
    ) -> dict[str, dict[str, int]]:
        """Persist card-rarity weights for the free reward."""

        self._validate_weight_map(weights, "card weights")
        self.free_card_weights = {
            rarity: weights.get(rarity, 0) for rarity in _FREE_CARD_RARITIES
        }
        self._save_free_reward_settings()
        return self.free_reward_settings()

    async def set_free_resource_weights(
        self, weights: dict[ResourceType, int]
    ) -> dict[str, dict[str, int]]:
        """Persist resource-type weights for the free reward."""

        self._validate_weight_map(weights, "resource weights")
        self.free_resource_weights = {
            resource: weights.get(resource, 0) for resource in _FREE_RESOURCE_TYPES
        }
        self._save_free_reward_settings()
        return self.free_reward_settings()

    async def set_free_resource_values(
        self, values: dict[ResourceType, int]
    ) -> dict[str, dict[str, int]]:
        """Persist resource values for the free reward."""

        if any(value <= 0 for value in values.values()):
            raise ValidationError("resource values must be > 0")
        self.free_resource_values = {
            resource: values.get(resource, 0) for resource in _FREE_RESOURCE_TYPES
        }
        self._save_free_reward_settings()
        return self.free_reward_settings()

    # Deck constructor ---------------------------------------------------

    async def deck_draft(self, telegram_id: int) -> list[int]:
        """Return or initialize the editable deck draft for a player."""

        player = await self.get_or_create_player(telegram_id)
        draft = self.deck_drafts.get(
            telegram_id,
            list(player.battle_deck.card_ids) if player.battle_deck else [],
        )
        owned = {card.id for card in await self.list_player_cards(telegram_id)}
        draft = [card_id for card_id in draft if card_id in owned]
        self.deck_drafts[telegram_id] = draft
        self._persist_runtime_state()
        return list(draft)

    async def toggle_deck_draft_card(self, telegram_id: int, card_id: int) -> list[int]:
        """Toggle one owned card in the editable deck draft."""

        await self.get_card(card_id, telegram_id)
        draft = await self.deck_draft(telegram_id)
        if card_id in draft:
            draft.remove(card_id)
        else:
            if len(draft) >= 5:
                raise ValidationError("в колоде можно выбрать не больше 5 карт")
            draft.append(card_id)
        self.deck_drafts[telegram_id] = draft
        self._persist_runtime_state()
        return list(draft)

    async def clear_deck_draft(self, telegram_id: int) -> list[int]:
        """Clear the editable deck draft."""

        await self.get_or_create_player(telegram_id)
        self.deck_drafts[telegram_id] = []
        self._persist_runtime_state()
        return []

    async def save_deck_draft(self, telegram_id: int) -> DeckSlots:
        """Persist the current draft as the player's battle deck."""

        player = await self.get_or_create_player(telegram_id)
        draft = await self.deck_draft(telegram_id)
        if len(draft) != 5:
            raise ValidationError("для сохранения колоды нужно выбрать ровно 5 карт")
        player.battle_deck = DeckSlots(tuple(draft))
        await self.players.save(player)
        return player.battle_deck

    # Admin content ------------------------------------------------------

    async def get_card(self, card_id: int, player_id: int) -> PlayerCard:
        """Return an owned card or raise an error."""

        card = await self.player_cards.get_by_id(card_id)
        if card is None or card.owner_player_id != player_id:
            raise EntityNotFoundError("card not found")
        return card

    async def level_up_card(self, telegram_id: int, card_id: int) -> PlayerCard:
        """Level up one owned card and persist the wallet change."""

        player = await self.get_or_create_player(telegram_id)
        card = await self.get_card(card_id, telegram_id)
        self.card_progression.level_up(card, player.wallet)
        await self.player_cards.save(card)
        await self.players.save(player)
        return card

    async def ascend_card(self, telegram_id: int, card_id: int) -> PlayerCard:
        """Ascend one owned card and persist the wallet change."""

        player = await self.get_or_create_player(telegram_id)
        card = await self.get_card(card_id, telegram_id)
        self.card_progression.ascend(card, player.wallet)
        await self.player_cards.save(card)
        await self.players.save(player)
        return card

    async def toggle_card_form(self, telegram_id: int, card_id: int) -> PlayerCard:
        """Toggle the visible form of an ascended card."""

        card = await self.get_card(card_id, telegram_id)
        self.card_progression.toggle_form(card)
        await self.player_cards.save(card)
        return card

    async def get_template(self, template_id: int) -> CardTemplate | None:
        """Return a card template by id."""

        return await self.card_templates.get_by_id(template_id)

    async def add_universe(self, value: str) -> list[str]:
        """Append a new universe name if it does not exist yet."""

        value = self._normalize_universe(value)
        universes = await self.list_universes()
        if value not in universes:
            universes.append(value)
            self._set_universes(universes)
        return universes

    async def remove_universe(self, value: str) -> list[str]:
        """Remove a universe name from the catalog."""

        value = self._normalize_universe(value)
        universes = [item for item in await self.list_universes() if item != value]
        self._set_universes(universes)
        return universes

    async def create_card_template(
        self,
        name: str,
        universe: Universe | str,
        rarity: Rarity,
        image_key: str,
        card_class: CardClass,
        base_stats: StatBlock,
        ascended_stats: StatBlock,
        ability: Ability,
        ascended_ability: Ability | None = None,
        is_available: bool = True,
    ) -> CardTemplate:
        """Create and persist a new card template."""

        await self.add_universe(getattr(universe, "value", universe))
        template = CardTemplate(
            id=_next_id(self.card_templates.items),
            name=name,
            universe=getattr(universe, "value", universe),
            rarity=rarity,
            image=ImageRef(image_key),
            card_class=card_class,
            base_stats=base_stats,
            ascended_stats=ascended_stats,
            ability=ability,
            ascended_ability=ascended_ability,
            is_available=is_available,
        )
        await self.card_templates.add(template)
        return template

    async def delete_profile_background(self, background_id: int) -> None:
        """Delete a profile background and remove it from players and banners."""

        if await self.get_profile_background(background_id) is None:
            raise EntityNotFoundError("profile background not found")
        await self.profile_backgrounds.delete(background_id)
        for banner in list(self.banners.items.values()):
            banner.pools = [
                item
                for item in banner.pools
                if item.profile_background_id != background_id
            ]
            await self.banners.save(banner)
        for player in self.players.items.values():
            player.owned_profile_background_ids = [
                item
                for item in player.owned_profile_background_ids
                if item != background_id
            ]
            if player.selected_profile_background_id == background_id:
                player.selected_profile_background_id = None
            await self.players.save(player)

    async def delete_card_template(self, template_id: int) -> None:
        """Delete a card template and every dependent reference."""

        if await self.get_template(template_id) is None:
            raise EntityNotFoundError("card template not found")
        await self.card_templates.delete(template_id)
        for card_id, card in list(self.player_cards.items.items()):
            if card.template_id == template_id:
                await self.player_cards.delete(card_id)
        for banner in list(self.banners.items.values()):
            banner.pools = [
                item for item in banner.pools if item.card_template_id != template_id
            ]
            await self.banners.save(banner)
        await self.set_standard_cards(
            [item for item in await self.list_standard_cards() if item != template_id]
        )
        for player in self.players.items.values():
            player.collection_count = len(
                await self.player_cards.list_by_owner(player.telegram_id)
            )
            await self.players.save(player)

    async def create_banner(
        self,
        name: str,
        banner_type: BannerType,
        cost_resource: ResourceType,
        start_at,
        end_at=None,
        is_active: bool = True,
    ) -> Banner:
        """Create and persist a new banner."""

        banner = Banner(
            id=_next_id(self.banners.items),
            name=name,
            banner_type=banner_type,
            cost_resource=cost_resource,
            date_range=DateRange(start_at, end_at),
            is_active=is_active,
        )
        await self.banners.add(banner)
        return banner

    async def delete_banner(self, banner_id: int) -> None:
        """Delete a banner if it has not started yet."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        await self.banners.delete(banner_id)

    async def add_banner_reward_card(
        self,
        banner_id: int,
        template_id: int,
        weight: int,
        guaranteed_for_10_pull: bool,
    ) -> Banner:
        """Add a card reward to a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        template = await self.get_template(template_id)
        if template is None:
            raise EntityNotFoundError("card template not found")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.CARD
                and reward.card_template_id == template_id
            )
        ]
        banner.pools.append(
            BannerReward(
                RewardType.CARD,
                card_template_id=template.id,
                quantity=1,
                rarity=template.rarity,
                weight=weight,
                guaranteed_for_10_pull=guaranteed_for_10_pull,
            )
        )
        await self.banners.save(banner)
        return banner

    async def add_banner_reward_profile_background(
        self,
        banner_id: int,
        background_id: int,
        weight: int,
        guaranteed_for_10_pull: bool,
    ) -> Banner:
        """Add a profile-background reward to a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        background = await self.get_profile_background(background_id)
        if background is None:
            raise EntityNotFoundError("profile background not found")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.PROFILE_BACKGROUND
                and reward.profile_background_id == background_id
            )
        ]
        banner.pools.append(
            BannerReward(
                RewardType.PROFILE_BACKGROUND,
                profile_background_id=background.id,
                quantity=1,
                profile_background_rarity=background.rarity,
                weight=weight,
                guaranteed_for_10_pull=guaranteed_for_10_pull,
            )
        )
        await self.banners.save(banner)
        return banner

    async def remove_banner_reward_card(
        self, banner_id: int, template_id: int
    ) -> Banner:
        """Remove a card reward from a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.CARD
                and reward.card_template_id == template_id
            )
        ]
        await self.banners.save(banner)
        return banner

    async def remove_banner_reward_profile_background(
        self, banner_id: int, background_id: int
    ) -> Banner:
        """Remove a profile-background reward from a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.PROFILE_BACKGROUND
                and reward.profile_background_id == background_id
            )
        ]
        await self.banners.save(banner)
        return banner

    async def create_shop_item(
        self,
        sell_resource_type: ResourceType,
        buy_resource_type: ResourceType,
        price: int,
        quantity: int,
        is_active: bool = True,
    ) -> ShopItem:
        """Create and persist a new shop item."""

        item = ShopItem(
            id=_next_id(self.shop.items),
            sell_resource_type=sell_resource_type,
            buy_resource_type=buy_resource_type,
            price=price,
            quantity=quantity,
            is_active=is_active,
        )
        await self.shop.add(item)
        return item

    async def remove_shop_item(self, item_id: int) -> None:
        """Remove an existing shop item from the catalog."""

        if await self.shop.get_by_id(item_id) is None:
            raise EntityNotFoundError("shop item not found")
        await self.shop.delete(item_id)

    async def set_standard_cards(self, template_ids: list[int]) -> list[int]:
        """Persist the full list of standard cards."""

        await self._validate_standard_cards(template_ids)
        ids = list(dict.fromkeys(template_ids))
        if self.catalog is None:
            self._write_standard_cards(ids)
        else:
            self.catalog.standard_cards = ids
            self.catalog.save()
        return ids

    async def add_standard_card(self, template_id: int) -> list[int]:
        """Append one card to the standard list."""

        current = await self.list_standard_cards()
        current.append(template_id)
        return await self.set_standard_cards(current)

    async def remove_standard_card(self, template_id: int) -> list[int]:
        """Remove one card from the standard list."""

        return await self.set_standard_cards(
            [item for item in await self.list_standard_cards() if item != template_id]
        )

    async def purchase_shop_item(self, telegram_id: int, item_id: int) -> ShopItem:
        """Buy one shop item for the player."""

        player = await self.get_or_create_player(telegram_id)
        item = await self.shop.get_by_id(item_id)
        if item is None:
            raise EntityNotFoundError("shop item not found")
        self.shop_service.purchase(player, item)
        await self.players.save(player)
        return item

    async def pull_banner(
        self, telegram_id: int, banner_id: int, count: int
    ) -> list[str]:
        """Roll rewards from a banner."""

        player = await self.get_or_create_player(telegram_id)
        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        rewards = self.banner_service.pull(player, banner, count=count)
        descriptions = [
            await self._apply_banner_reward(player, reward) for reward in rewards
        ]
        await self.players.save(player)
        return descriptions

    async def create_clan(self, telegram_id: int, name: str, icon: str) -> Clan:
        """Create a clan for the player who started the flow."""

        owner = await self.get_or_create_player(telegram_id)
        if owner.clan_id is not None:
            raise ForbiddenActionError("player is already in a clan")
        clan = Clan(
            id=await self._next_clan_id(),
            owner_player_id=owner.telegram_id,
            name=name,
            icon=icon,
        )
        self.clan_service.create_clan(clan, owner)
        await self.clans.add(clan)
        await self.players.save(owner)
        return clan

    async def join_clan(self, telegram_id: int, clan_id: int) -> Clan:
        """Join an existing clan."""

        player = await self.get_or_create_player(telegram_id)
        clan = await self.clans.get_by_id(clan_id)
        if clan is None:
            raise EntityNotFoundError("clan not found")
        self.clan_service.join_clan(clan, player)
        await self.clans.save(clan)
        await self.players.save(player)
        return clan

    async def leave_clan(self, telegram_id: int) -> None:
        """Leave the current clan."""

        player = await self.get_or_create_player(telegram_id)
        clan = await self.player_clan(player)
        if clan is None:
            raise EntityNotFoundError("clan not found")
        self.clan_service.leave_clan(clan, player)
        await self.clans.save(clan)
        await self.players.save(player)

    # Battles ------------------------------------------------------------

    async def start_battle(self, player_one_id: int, player_two_id: int) -> Battle:
        """Create and activate a new PvP battle."""

        if player_one_id == player_two_id:
            raise ValidationError("cannot battle yourself")
        player_one = await self.get_or_create_player(player_one_id)
        player_two = await self.get_or_create_player(player_two_id)
        battle = Battle(
            id=await self._next_battle_id(),
            player_one_id=player_one.telegram_id,
            player_two_id=player_two.telegram_id,
            player_one_side=await self._battle_side_for(player_one),
            player_two_side=await self._battle_side_for(player_two),
        )
        self.battle_engine.start_battle(battle)
        await self.battles.add(battle)
        return battle

    async def get_active_battle(self, telegram_id: int) -> Battle | None:
        """Return the active battle for one player, if any."""

        getter = getattr(self.battles, "get_active_by_player", None)
        if getter is None:
            getter = getattr(self.battles, "get_active_battle_for_player", None)
        if getter is None:
            raise AttributeError("battle repository does not support active lookups")
        return await getter(telegram_id)

    def _battle_round_key(
        self, battle_id: int, round_number: int, player_id: int
    ) -> tuple[int, int, int]:
        """Return the lookup key for one round draft."""

        return battle_id, round_number, player_id

    def _battle_round_actions(
        self, battle_id: int, round_number: int, player_id: int
    ) -> list[BattleAction]:
        """Return the pending actions for one player in one round."""

        return self.battle_action_drafts.setdefault(
            self._battle_round_key(battle_id, round_number, player_id),
            [],
        )

    def _battle_round_summary(
        self, battle: Battle, player_id: int
    ) -> BattleRoundSummary:
        """Summarize one player's draft for the current round."""

        actions = self.battle_action_drafts.get(
            self._battle_round_key(battle.id, battle.current_round, player_id),
            [],
        )
        attack_count = 0
        block_count = 0
        bonus_count = 0
        ability_used = False
        spent_ap = 0
        for action in actions:
            spent_ap += action.ap_cost
            if action.action_type == BattleActionType.ATTACK:
                attack_count += 1
            elif action.action_type == BattleActionType.BLOCK:
                block_count += 1
            elif action.action_type == BattleActionType.BONUS:
                bonus_count += 1
            elif action.action_type == BattleActionType.USE_ABILITY:
                ability_used = True
        active_card = battle.side_for(player_id).active_card()
        ability_cost = active_card.template.ability_for(active_card.form).cost
        base_ap = min(5, battle.current_round)
        available_action_points = max(0, base_ap - spent_ap)
        opponent_actions = self.battle_action_drafts.get(
            self._battle_round_key(
                battle.id, battle.current_round, battle.opponent_side_for(player_id).player_id
            ),
            [],
        )
        opponent_spent_ap = 0
        for action in opponent_actions:
            opponent_spent_ap += action.ap_cost
        opponent_action_points = max(0, base_ap - opponent_spent_ap)
        return BattleRoundSummary(
            attack_count=attack_count,
            block_count=block_count,
            bonus_count=bonus_count,
            ability_used=ability_used,
            available_action_points=available_action_points,
            opponent_action_points=opponent_action_points,
            ability_cost=ability_cost,
            can_switch=not actions and available_action_points > 0,
        )

    def battle_round_summary(self, battle: Battle, player_id: int) -> BattleRoundSummary:
        """Expose the current round summary for Telegram presentation."""

        return self._battle_round_summary(battle, player_id)

    def _clear_battle_round_drafts(self, battle_id: int) -> None:
        """Drop all drafts for a battle."""

        self.battle_action_drafts = {
            key: value
            for key, value in self.battle_action_drafts.items()
            if key[0] != battle_id
        }

    def _clear_all_battles(self) -> None:
        """Remove every stored battle, queue entry, and round draft."""

        if self.battles.items:
            self.battles.items.clear()
        if self.search_queue:
            self.search_queue.clear()
        self.battle_action_drafts.clear()
        if self.store is not None:
            self.store.save()

    async def record_battle_action(
        self,
        player_id: int,
        action: str,
        *,
        card_id: int | None = None,
    ) -> Battle:
        """Append one action to the player's draft and resolve finished rounds."""

        battle = await self.get_active_battle(player_id)
        if battle is None:
            raise EntityNotFoundError("battle not found")
        summary = self._battle_round_summary(battle, player_id)
        actions = self._battle_round_actions(
            battle.id, battle.current_round, player_id
        )
        if action == "switch" and actions:
            raise BattleRuleViolationError("switch can be used only as the first choice")
        if action == "attack":
            if summary.available_action_points < 1:
                raise BattleRuleViolationError("not enough action points")
            actions.append(AttackAction(action_type=BattleActionType.ATTACK, ap_cost=1))
        elif action == "block":
            if summary.available_action_points < 1:
                raise BattleRuleViolationError("not enough action points")
            actions.append(BlockAction(action_type=BattleActionType.BLOCK, ap_cost=1))
        elif action == "bonus":
            if summary.available_action_points < 1:
                raise BattleRuleViolationError("not enough action points")
            actions.append(BonusAction(action_type=BattleActionType.BONUS, ap_cost=1))
        elif action == "ability":
            if summary.ability_used:
                raise BattleRuleViolationError("ability can be used only once per round")
            if summary.available_action_points < summary.ability_cost:
                raise BattleRuleViolationError("Не достаточно Очков Действия для способности")
            active_card = battle.side_for(player_id).active_card()
            actions.append(
                UseAbilityAction(
                    action_type=BattleActionType.USE_ABILITY,
                    ap_cost=summary.ability_cost,
                    player_card_id=active_card.player_card_id,
                )
            )
        elif action == "switch":
            if card_id is None:
                raise ValidationError("switch requires card_id")
            if summary.available_action_points < 1:
                raise BattleRuleViolationError("not enough action points")
            side = battle.side_for(player_id)
            card = side.cards.get(card_id)
            if card is None or not card.alive:
                raise BattleRuleViolationError("cannot switch to dead/unknown card")
            actions.append(
                SwitchCardAction(
                    action_type=BattleActionType.SWITCH_CARD,
                    ap_cost=1,
                    new_active_card_id=card_id,
                )
            )
        else:
            raise ValidationError("unsupported battle action")

        if self._battle_round_summary(battle, player_id).available_action_points > 0:
            await self.battles.save(battle)
            return battle

        opponent_id = battle.opponent_side_for(player_id).player_id
        opponent_summary = self._battle_round_summary(battle, opponent_id)
        if opponent_summary.available_action_points > 0:
            await self.battles.save(battle)
            return battle

        actions_by_player = {
            battle.player_one_id: list(
                self.battle_action_drafts.get(
                    self._battle_round_key(
                        battle.id, battle.current_round, battle.player_one_id
                    ),
                    [],
                )
            ),
            battle.player_two_id: list(
                self.battle_action_drafts.get(
                    self._battle_round_key(
                        battle.id, battle.current_round, battle.player_two_id
                    ),
                    [],
                )
            ),
        }
        result = self.battle_engine.resolve_round(battle, actions_by_player)
        self._clear_battle_round_drafts(battle.id)
        await self.battles.save(result.battle)
        return result.battle

    async def search_battle(self, telegram_id: int) -> Battle | None:
        """Join the matchmaking queue and start a battle when possible."""

        player = await self.get_or_create_player(telegram_id)
        if player.battle_deck is None or len(player.battle_deck.card_ids) != 5:
            raise ValidationError("Колода не полностью собрана")
        self.search_queue[player.telegram_id] = player.rating
        self._persist_runtime_state()
        return await self.process_matchmaking()

    async def cancel_battle_search(self, telegram_id: int) -> None:
        """Remove a player from the matchmaking queue."""

        self.search_queue.pop(telegram_id, None)
        self._persist_runtime_state()

    async def process_matchmaking(self) -> Battle | None:
        """Pair the first two compatible players from the queue."""

        ids = list(self.search_queue)
        for index, player_one_id in enumerate(ids):
            player_one = await self.get_or_create_player(player_one_id)
            for player_two_id in ids[index + 1 :]:
                player_two = await self.get_or_create_player(player_two_id)
                if abs(player_one.rating - player_two.rating) > 100:
                    continue
                self.search_queue.pop(player_one_id, None)
                self.search_queue.pop(player_two_id, None)
                self._persist_runtime_state()
                return await self.start_battle(player_one_id, player_two_id)
        return None

    async def is_searching(self, telegram_id: int) -> bool:
        """Return True when a player is in the queue."""

        return telegram_id in self.search_queue

    # Battle pass and counters ------------------------------------------

    async def list_battle_pass_levels(self) -> list[BattlePassLevel]:
        """Return levels from the active battle pass season."""

        season = await self.active_battle_pass()
        return [] if season is None else list(season.levels)

    async def list_premium_battle_pass_levels(self) -> list[BattlePassLevel]:
        """Return levels from the active premium battle pass season."""

        season = await self.active_premium_battle_pass()
        return [] if season is None else list(season.levels)

    async def add_battle_pass_level(
        self,
        level_number: int,
        required_points: int,
        reward: QuestReward,
    ) -> BattlePassSeason:
        """Add or replace a battle pass level in the active season."""

        season = await self.active_battle_pass()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        now = datetime.now(timezone.utc)
        if not (season.start_at <= now <= season.end_at):
            raise ForbiddenActionError("battle pass season is not active")
        season.levels = [
            level for level in season.levels if level.level_number != level_number
        ]
        season.levels.append(BattlePassLevel(level_number, required_points, reward))
        season.levels.sort(key=lambda level: level.level_number)
        await self.battle_pass_seasons.save(season)
        return season

    async def add_premium_battle_pass_level(
        self,
        level_number: int,
        required_points: int,
        reward: QuestReward,
    ) -> BattlePassSeason:
        """Add or replace a level in the active premium battle pass season."""

        season = await self.active_premium_battle_pass()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        now = datetime.now(timezone.utc)
        if not (season.start_at <= now <= season.end_at):
            raise ForbiddenActionError("battle pass season is not active")
        season.levels = [
            level for level in season.levels if level.level_number != level_number
        ]
        season.levels.append(BattlePassLevel(level_number, required_points, reward))
        season.levels.sort(key=lambda level: level.level_number)
        await self.premium_battle_pass_seasons.save(season)
        return season

    async def active_battle_pass_progress(self, player_id: int) -> BattlePassProgress:
        """Return the active season progress for a player."""

        season = await self.active_battle_pass()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        progress = await self.battle_pass_progress.get_for_player(player_id, season.id)
        if progress is None:
            progress = BattlePassProgress(player_id=player_id, season_id=season.id)
            await self.battle_pass_progress.save(progress)
        return progress

    async def active_premium_battle_pass_progress(
        self, player_id: int
    ) -> BattlePassProgress:
        """Return the active premium season progress for a player."""

        season = await self.active_premium_battle_pass()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        progress = await self.premium_battle_pass_progress.get_for_player(
            player_id, season.id
        )
        if progress is None:
            progress = BattlePassProgress(player_id=player_id, season_id=season.id)
            await self.premium_battle_pass_progress.save(progress)
        return progress

    async def buy_battle_pass_level(
        self, telegram_id: int
    ) -> tuple[BattlePassProgress, int]:
        """Buy the next unclaimed battle pass level for 250 coins."""

        season = await self.active_battle_pass()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        player = await self.get_or_create_player(telegram_id)
        progress = await self.active_battle_pass_progress(telegram_id)
        next_level = next(
            (
                level
                for level in season.levels
                if level.level_number not in progress.claimed_levels
            ),
            None,
        )
        if next_level is None:
            raise ValidationError("battle pass is already fully claimed")
        player.wallet.spend(ResourceType.COINS, 250)
        progress.points = max(progress.points, next_level.required_points)
        progress.claimed_levels.add(next_level.level_number)
        if next_level.reward.coins:
            player.wallet.add(ResourceType.COINS, next_level.reward.coins)
        if next_level.reward.crystals:
            player.wallet.add(ResourceType.CRYSTALS, next_level.reward.crystals)
        if next_level.reward.orbs:
            player.wallet.add(ResourceType.ORBS, next_level.reward.orbs)
        if next_level.reward.battle_pass_points:
            player.battle_pass_progress.append(next_level.reward.battle_pass_points)
        await self.players.save(player)
        await self.battle_pass_progress.save(progress)
        return progress, next_level.level_number

    async def buy_premium_battle_pass_level(
        self, telegram_id: int
    ) -> tuple[BattlePassProgress, int]:
        """Buy the next unclaimed premium battle pass level for 250 coins."""

        season = await self.active_premium_battle_pass()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        player = await self.get_or_create_player(telegram_id)
        if not player.is_premium:
            raise ForbiddenActionError(
                "premium battle pass is available only for premium players"
            )
        progress = await self.active_premium_battle_pass_progress(telegram_id)
        next_level = next(
            (
                level
                for level in season.levels
                if level.level_number not in progress.claimed_levels
            ),
            None,
        )
        if next_level is None:
            raise ValidationError("battle pass is already fully claimed")
        player.wallet.spend(ResourceType.COINS, 250)
        progress.points = max(progress.points, next_level.required_points)
        progress.claimed_levels.add(next_level.level_number)
        if next_level.reward.coins:
            player.wallet.add(ResourceType.COINS, next_level.reward.coins)
        if next_level.reward.crystals:
            player.wallet.add(ResourceType.CRYSTALS, next_level.reward.crystals)
        if next_level.reward.orbs:
            player.wallet.add(ResourceType.ORBS, next_level.reward.orbs)
        if next_level.reward.battle_pass_points:
            player.battle_pass_progress.append(next_level.reward.battle_pass_points)
        await self.players.save(player)
        await self.premium_battle_pass_progress.save(progress)
        return progress, next_level.level_number

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

    # Internal helpers ---------------------------------------------------

    def _load_free_reward_settings(self) -> None:
        """Load persisted free reward settings when available."""

        if self.catalog is None:
            return
        data = getattr(self.catalog, "free_rewards", {}) or {}
        self.free_card_weights = {
            rarity: int(
                data.get("card_weights", {}).get(
                    rarity.value, self.free_card_weights[rarity]
                )
            )
            for rarity in _FREE_CARD_RARITIES
        }
        self.free_resource_weights = {
            resource: int(
                data.get("resource_weights", {}).get(
                    resource.value, self.free_resource_weights[resource]
                )
            )
            for resource in _FREE_RESOURCE_TYPES
        }
        self.free_resource_values = {
            resource: int(
                data.get("resource_values", {}).get(
                    resource.value, self.free_resource_values[resource]
                )
            )
            for resource in _FREE_RESOURCE_TYPES
        }

    def _save_free_reward_settings(self) -> None:
        """Persist free reward settings when a local catalog is active."""

        if self.catalog is None:
            return
        self.catalog.free_rewards = {
            "card_weights": {
                rarity.value: self.free_card_weights.get(rarity, 0)
                for rarity in _FREE_CARD_RARITIES
            },
            "resource_weights": {
                resource.value: self.free_resource_weights.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
            "resource_values": {
                resource.value: self.free_resource_values.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
        }
        self.catalog.save()

    @staticmethod
    def _normalize_nickname(nickname: str | None) -> str | None:
        """Validate and normalize a unique nickname."""

        if nickname is None:
            return None
        value = nickname.strip()
        if value.lower() in {"", "-", "none", "нет", "null"}:
            return None
        if not _NICKNAME_RE.fullmatch(value):
            raise ValidationError("nickname must be 3-24 chars: letters, digits or _")
        return value

    @staticmethod
    def _normalize_title(title: str | None) -> str | None:
        """Validate and normalize a profile title."""

        if title is None:
            return None
        value = title.strip()
        if value.lower() in {"", "-", "none", "нет", "null"}:
            return None
        if len(value) > _MAX_TITLE_LENGTH:
            raise ValidationError(f"title must be <= {_MAX_TITLE_LENGTH} chars")
        return value

    @staticmethod
    def _validate_weight_map(weights: dict, label: str) -> None:
        """Make sure a weighted config has at least one positive entry."""

        if any(value < 0 for value in weights.values()):
            raise ValidationError(f"{label} must be >= 0")
        if sum(weights.values()) <= 0:
            raise ValidationError(f"{label} must have a positive total weight")

    def _pick_weighted(self, weights: dict) -> object:
        """Pick one key from a weighted mapping."""

        total = sum(weights.values())
        pick = self.rng.randint(1, total)
        upto = 0
        for key, weight in weights.items():
            upto += weight
            if pick <= upto:
                return key
        return next(reversed(weights))

    @staticmethod
    def _next_free_reward_time(last_claim_at: datetime | None) -> datetime:
        """Return the next moment when a reward becomes available."""

        if last_claim_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        moment = (
            last_claim_at
            if last_claim_at.tzinfo
            else last_claim_at.replace(tzinfo=timezone.utc)
        )
        return moment + _FREE_REWARD_COOLDOWN

    def _ensure_free_reward_ready(self, last_claim_at: datetime | None) -> None:
        """Raise when the reward is still on cooldown."""

        now = datetime.now(timezone.utc)
        ready_at = self._next_free_reward_time(last_claim_at)
        if ready_at > now:
            raise ValidationError("бесплатная награда еще не готова")

    async def _grant_template_to_player(
        self, player: Player, template: CardTemplate
    ) -> PlayerCard:
        """Grant a template as a new card or as an extra copy."""

        owned_cards = await self.player_cards.list_by_owner(player.telegram_id)
        for card in owned_cards:
            if card.template_id == template.id:
                card.copies_owned += 1
                await self.player_cards.save(card)
                return card
        card = PlayerCard(
            id=_next_id(self.player_cards.items),
            owner_player_id=player.telegram_id,
            template_id=template.id,
            level=1,
            copies_owned=1,
            current_form=CardForm.BASE,
        )
        await self.player_cards.add(card)
        player.collection_count = len(
            await self.player_cards.list_by_owner(player.telegram_id)
        )
        return card

    async def _grant_profile_background_to_player(
        self, player: Player, background: ProfileBackgroundTemplate
    ) -> bool:
        """Grant a profile background to a player."""

        granted = player.grant_profile_background(background.id)
        await self.players.save(player)
        return granted

    async def _apply_banner_reward(self, player: Player, reward: BannerReward) -> str:
        """Apply one banner reward to the player and return a readable summary."""

        if (
            reward.reward_type == RewardType.RESOURCE
            and reward.resource_type is not None
        ):
            player.wallet.add(reward.resource_type, reward.quantity)
            return f"<code>{reward.quantity}</code> {reward.resource_type.value}"
        if (
            reward.reward_type == RewardType.CARD
            and reward.card_template_id is not None
        ):
            template = await self.get_template(reward.card_template_id)
            if template is None:
                raise EntityNotFoundError("card template not found")
            card = await self._grant_template_to_player(player, template)
            return (
                f"карта <b>{template.name}</b> · <code>{template.rarity.value}</code>"
                f" · card_id <code>{card.id}</code>"
            )
        if (
            reward.reward_type == RewardType.PROFILE_BACKGROUND
            and reward.profile_background_id is not None
        ):
            background = await self.get_profile_background(reward.profile_background_id)
            if background is None:
                raise EntityNotFoundError("profile background not found")
            granted = await self._grant_profile_background_to_player(player, background)
            status = "новый" if granted else "уже был"
            return (
                f"фон профиля <code>#{background.id}</code> · "
                f"<code>{background.rarity.value}</code> · {status}"
            )
        raise ValidationError("unsupported banner reward")

    async def _badenko_card_count(self, telegram_id: int) -> int:
        """Return the number of Badenko cards in the player's collection."""

        count = 0
        for card in await self.player_cards.list_by_owner(telegram_id):
            template = await self.get_template(card.template_id)
            if template is not None and template.rarity == Rarity.BADENKO:
                count += 1
        return count

    @staticmethod
    def _sort_ideas(ideas: list[Idea]) -> list[Idea]:
        """Sort ideas by community support first."""

        return sorted(
            ideas,
            key=lambda idea: (idea.upvotes, -idea.downvotes, idea.id),
            reverse=True,
        )

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
            if self.store is not None:
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
            if self.store is not None:
                self.store.save()

    def _persist_runtime_state(self) -> None:
        """Flush transient runtime state when durable storage is enabled."""

        if self.store is not None:
            self.store.save()

    def _set_universes(self, values: list[str]) -> None:
        """Persist the universe list."""

        values = list(dict.fromkeys(values))
        if self.catalog is None:
            self._universes = values
        else:
            self.catalog.universes = values
            self.catalog.save()

    def _normalize_universe(self, value: str) -> str:
        """Normalize a free-form universe name."""

        return "_".join(
            part for part in value.strip().lower().replace("-", " ").split()
        )

    def _read_standard_cards(self) -> list[int]:
        """Read the starter card list."""

        return list(
            getattr(self, "_standard_cards", [])
            if self.catalog is None
            else self.catalog.standard_cards
        )

    def _write_standard_cards(self, values: list[int]) -> None:
        """Persist the starter card list."""

        if self.catalog is None:
            self._standard_cards = list(values)
            return
        self.catalog.standard_cards = list(values)
        self.catalog.save()

    async def _validate_standard_cards(self, template_ids: list[int]) -> None:
        """Make sure the standard list only contains existing templates."""

        for template_id in template_ids:
            if await self.get_template(template_id) is None:
                raise EntityNotFoundError(f"card template {template_id} not found")

    async def _grant_standard_cards(self, player: Player) -> None:
        """Give the default starter cards to a newly created player."""

        template_ids = await self.list_standard_cards()
        if not template_ids:
            return
        for template_id in template_ids:
            if await self.get_template(template_id) is None:
                continue
            await self.player_cards.add(
                PlayerCard(
                    id=_next_id(self.player_cards.items),
                    owner_player_id=player.telegram_id,
                    template_id=template_id,
                    copies_owned=1,
                    level=1,
                    current_form=CardForm.BASE,
                )
            )
        player.collection_count = len(
            await self.player_cards.list_by_owner(player.telegram_id)
        )

    async def _battle_side_for(self, player: Player) -> BattleSide:
        """Build one battle side from the player's battle deck."""

        cards = await self.list_player_cards(player.telegram_id)
        if player.battle_deck is None or len(player.battle_deck.card_ids) != 5:
            raise ValidationError("Колода не полностью собрана")
        deck_ids = player.battle_deck.card_ids
        by_id = {card.id: card for card in cards}
        selected: list[BattleCardState] = []
        for card_id in deck_ids:
            card = by_id.get(card_id)
            if card is None:
                raise ValidationError("battle deck contains unknown card")
            template = await self.get_template(card.template_id)
            if template is None:
                raise EntityNotFoundError("card template not found")
            stats = template.stats_for(card.current_form)
            selected.append(
                BattleCardState(
                    card.id,
                    template,
                    card.current_form,
                    stats.health,
                    stats.health,
                    stats.damage,
                    stats.defense,
                )
            )
        return BattleSide(
            player.telegram_id,
            {card.player_card_id: card for card in selected},
            selected[0].player_card_id,
        )

    async def _next_clan_id(self) -> int:
        return _next_id(self.clans.items)

    async def _next_battle_id(self) -> int:
        return _next_id(self.battles.items)
