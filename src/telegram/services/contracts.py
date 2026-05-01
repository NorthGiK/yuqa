"""Typed contracts shared by Telegram service mixins.

The feature mixins are composed by ``TelegramServices``. These protocols keep
the mixins editor-friendly without importing the concrete service container and
creating a circular dependency.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, MutableMapping
from datetime import datetime
from random import Random
from typing import Protocol, TypedDict

from src.banners.domain.entities import Banner
from src.banners.domain.services import BannerRollService
from src.battle_pass.domain.entities import BattlePassProgress, BattlePassSeason
from src.battles.domain.actions import BattleAction
from src.battles.domain.engine import BattleEngine
from src.battles.domain.entities import Battle
from src.cards.domain.entities import CardTemplate, PlayerCard
from src.cards.domain.services import CardProgressionService
from src.clans.domain.entities import Clan
from src.clans.domain.services import ClanService
from src.ideas.domain.entities import Idea
from src.ideas.domain.services import IdeaService
from src.players.domain.entities import Player, ProfileBackgroundTemplate
from src.shared.enums import Rarity, ResourceType
from src.shared.value_objects.deck_slots import DeckSlots
from src.shop.domain.entities import ShopItem
from src.shop.domain.services import ShopService


FreeRewardSettings = dict[str, dict[str, int]]


class FreeRewardsStatus(TypedDict):
    """Computed free-reward state used by the rewards screen."""

    card_ready_at: datetime
    resource_ready_at: datetime
    card_ready: bool
    resource_ready: bool
    settings: FreeRewardSettings


class BattleTimeoutNotifier(Protocol):
    """Async callback used when a battle round times out."""

    def __call__(
        self,
        battle: Battle,
        *,
        reason: str | None = None,
    ) -> Awaitable[None]: ...


class SaveableStore(Protocol):
    """Storage object that can persist its current state."""

    def save(self) -> None: ...


class CatalogStoreLike(SaveableStore, Protocol):
    """Catalog fields used directly by Telegram service helpers."""

    universes: list[str]
    standard_cards: list[int]
    free_rewards: FreeRewardSettings


class PlayerRepositoryLike(Protocol):
    """Player repository surface used by Telegram services."""

    items: MutableMapping[int, Player]

    async def get_by_id(self, telegram_id: int) -> Player | None: ...
    async def get_by_telegram_id(self, telegram_id: int) -> Player | None: ...
    async def get_by_nickname(self, nickname: str) -> Player | None: ...
    async def list_all(self) -> list[Player]: ...
    async def add(self, player: Player) -> Player: ...
    async def save(self, player: Player) -> Player: ...
    async def delete(self, telegram_id: int) -> None: ...


class PlayerCardRepositoryLike(Protocol):
    """Owned-card repository surface used by Telegram services."""

    items: MutableMapping[int, PlayerCard]

    async def get_by_id(self, card_id: int) -> PlayerCard | None: ...
    async def list_by_owner(self, owner_player_id: int) -> list[PlayerCard]: ...
    async def add(self, card: PlayerCard) -> PlayerCard: ...
    async def save(self, card: PlayerCard) -> PlayerCard: ...
    async def delete(self, card_id: int) -> None: ...


class CardTemplateRepositoryLike(Protocol):
    """Card-template repository surface used by Telegram services."""

    items: MutableMapping[int, CardTemplate]

    async def get_by_id(self, template_id: int) -> CardTemplate | None: ...
    async def list_active(self) -> list[CardTemplate]: ...
    async def add(self, template: CardTemplate) -> CardTemplate: ...
    async def save(self, template: CardTemplate) -> CardTemplate: ...
    async def delete(self, template_id: int) -> None: ...


class ProfileBackgroundRepositoryLike(Protocol):
    """Profile-background repository surface used by Telegram services."""

    items: MutableMapping[int, ProfileBackgroundTemplate]

    async def get_by_id(
        self,
        background_id: int,
    ) -> ProfileBackgroundTemplate | None: ...
    async def list_all(self) -> list[ProfileBackgroundTemplate]: ...
    async def add(
        self,
        background: ProfileBackgroundTemplate,
    ) -> ProfileBackgroundTemplate: ...
    async def save(
        self,
        background: ProfileBackgroundTemplate,
    ) -> ProfileBackgroundTemplate: ...
    async def delete(self, background_id: int) -> None: ...


class ClanRepositoryLike(Protocol):
    """Clan repository surface used by Telegram services."""

    items: MutableMapping[int, Clan]

    async def get_by_id(self, clan_id: int) -> Clan | None: ...
    async def find_by_player(self, player_id: int) -> Clan | None: ...
    async def list_all(self) -> list[Clan]: ...
    async def add(self, clan: Clan) -> Clan: ...
    async def save(self, clan: Clan) -> Clan: ...
    async def delete(self, clan_id: int) -> None: ...


class BattleRepositoryLike(Protocol):
    """Battle repository surface used by Telegram services."""

    items: MutableMapping[int, Battle]

    async def get_by_id(self, battle_id: int) -> Battle | None: ...
    async def get_active_by_player(self, player_id: int) -> Battle | None: ...
    async def add(self, battle: Battle) -> Battle: ...
    async def save(self, battle: Battle) -> Battle: ...
    async def delete(self, battle_id: int) -> None: ...


class BannerRepositoryLike(Protocol):
    """Banner repository surface used by Telegram services."""

    items: MutableMapping[int, Banner]

    async def get_by_id(self, banner_id: int) -> Banner | None: ...
    async def list_available(self) -> list[Banner]: ...
    async def add(self, banner: Banner) -> Banner: ...
    async def save(self, banner: Banner) -> Banner: ...
    async def delete(self, banner_id: int) -> None: ...


class ShopRepositoryLike(Protocol):
    """Shop repository surface used by Telegram services."""

    items: MutableMapping[int, ShopItem]

    async def get_by_id(self, item_id: int) -> ShopItem | None: ...
    async def list_active(self) -> list[ShopItem]: ...
    async def add(self, item: ShopItem) -> ShopItem: ...
    async def save(self, item: ShopItem) -> ShopItem: ...
    async def delete(self, item_id: int) -> None: ...


class IdeaRepositoryLike(Protocol):
    """Idea repository surface used by Telegram services."""

    items: MutableMapping[int, Idea]

    async def get_by_id(self, idea_id: int) -> Idea | None: ...
    async def list_all(self) -> list[Idea]: ...
    async def add(self, idea: Idea) -> Idea: ...
    async def save(self, idea: Idea) -> Idea: ...
    async def delete(self, idea_id: int) -> None: ...


class BattlePassSeasonRepositoryLike(Protocol):
    """Battle-pass season repository surface used by Telegram services."""

    items: MutableMapping[int, BattlePassSeason]

    async def get_by_id(self, season_id: int) -> BattlePassSeason | None: ...
    async def list_active(self) -> list[BattlePassSeason]: ...
    async def list_all(self) -> list[BattlePassSeason]: ...
    async def save(self, season: BattlePassSeason) -> BattlePassSeason: ...
    async def delete(self, season_id: int) -> None: ...


class BattlePassProgressRepositoryLike(Protocol):
    """Battle-pass progress repository surface used by Telegram services."""

    items: MutableMapping[tuple[int, int], BattlePassProgress]

    async def get_for_player(
        self,
        player_id: int,
        season_id: int,
    ) -> BattlePassProgress | None: ...
    async def save(self, progress: BattlePassProgress) -> BattlePassProgress: ...
    async def delete(self, progress_key: tuple[int, int]) -> None: ...


class TelegramServiceContext(Protocol):
    """Complete service surface available to every service mixin."""

    store: SaveableStore | None
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
    card_progression: CardProgressionService
    clan_service: ClanService
    idea_service: IdeaService
    shop_service: ShopService
    banner_service: BannerRollService
    battle_engine: BattleEngine
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
    rng: Random
    free_card_weights: dict[Rarity, int]
    free_resource_weights: dict[ResourceType, int]
    free_resource_values: dict[ResourceType, int]
    _universes: list[str]
    _standard_cards: list[int]

    async def get_or_create_player(self, telegram_id: int) -> Player: ...
    async def get_player(self, telegram_id: int) -> Player | None: ...
    async def player_clan(self, player: Player) -> Clan | None: ...
    async def list_player_cards(self, telegram_id: int) -> list[PlayerCard]: ...
    async def deck_draft(self, telegram_id: int) -> list[int]: ...
    async def save_deck_draft(self, telegram_id: int) -> DeckSlots: ...
    async def get_profile_background(
        self,
        background_id: int,
    ) -> ProfileBackgroundTemplate | None: ...
    async def list_standard_cards(self) -> list[int]: ...
    async def get_card(self, card_id: int, player_id: int) -> PlayerCard: ...
    async def get_template(self, template_id: int) -> CardTemplate | None: ...
    async def _grant_template_to_player(
        self,
        player: Player,
        template: CardTemplate,
    ) -> PlayerCard: ...
    async def _grant_profile_background_to_player(
        self,
        player: Player,
        background: ProfileBackgroundTemplate,
    ) -> bool: ...
    def _clear_battle_round_drafts(self, battle_id: int) -> None: ...
    def _remove_card_ids_from_deck_drafts(self, removed_card_ids: set[int]) -> None: ...
    def _persist_runtime_state(self) -> None: ...
    @staticmethod
    def _ensure_valid_battle_deck_ids(
        card_ids: list[int] | tuple[int, ...],
    ) -> None: ...
    @staticmethod
    def _unique_card_ids(card_ids: list[int]) -> list[int]: ...


__all__ = [
    "BannerRepositoryLike",
    "BattlePassProgressRepositoryLike",
    "BattlePassSeasonRepositoryLike",
    "BattleRepositoryLike",
    "BattleTimeoutNotifier",
    "CardTemplateRepositoryLike",
    "CatalogStoreLike",
    "ClanRepositoryLike",
    "FreeRewardSettings",
    "FreeRewardsStatus",
    "IdeaRepositoryLike",
    "PlayerCardRepositoryLike",
    "PlayerRepositoryLike",
    "ProfileBackgroundRepositoryLike",
    "SaveableStore",
    "ShopRepositoryLike",
    "TelegramServiceContext",
]
