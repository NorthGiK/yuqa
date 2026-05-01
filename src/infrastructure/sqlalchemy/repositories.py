"""Persistent repositories backed by a single SQLAlchemy document store."""

from pathlib import Path
from typing import Any, Generic, TypeVar

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.banners.domain.entities import Banner
from src.battle_pass.domain.entities import BattlePassProgress, BattlePassSeason
from src.battles.domain.entities import Battle
from src.cards.domain.entities import CardTemplate, PlayerCard
from src.clans.domain.entities import Clan
from src.infrastructure.local import CatalogStore
from src.infrastructure.sqlalchemy.models import StateDocumentORM
from src.infrastructure.sqlalchemy.serialization import (
    CATALOG_SECTIONS,
    SECTION_CODECS,
)
from src.infrastructure.sqlalchemy.urls import ensure_sqlite_parent, sync_database_url
from src.ideas.domain.entities import Idea
from src.players.domain.entities import Player, ProfileBackgroundTemplate
from src.shared.enums import Universe
from src.shop.domain.entities import ShopItem


RepositoryKey = int | tuple[int, int]
T = TypeVar("T")


def create_sync_engine(database_url: str) -> Engine:
    """Create the synchronous engine used by the document store."""

    database_url = sync_database_url(database_url)
    ensure_sqlite_parent(database_url)

    engine = create_engine(database_url, future=True, pool_pre_ping=True)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _configure_sqlite(
            dbapi_connection: Any,
            _connection_record: Any,
        ) -> None:
            # These PRAGMAs keep the single-document store safe enough for
            # bot-style write patterns while preserving SQLite compatibility.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


class PersistentStateStore:
    """State store that persists named JSON documents into the database."""

    def __init__(
        self,
        database_url: str,
        import_catalog_path: str | Path | None = None,
    ) -> None:
        self.database_url = database_url
        self.engine = create_sync_engine(database_url)
        StateDocumentORM.metadata.create_all(self.engine)

        self.players: dict[int, Player] = {}
        self.player_cards: dict[int, PlayerCard] = {}
        self.cards: dict[int, CardTemplate] = {}
        self.profile_backgrounds: dict[int, ProfileBackgroundTemplate] = {}
        self.clans: dict[int, Clan] = {}
        self.banners: dict[int, Banner] = {}
        self.shop_items: dict[int, ShopItem] = {}
        self.battle_pass_seasons: dict[int, BattlePassSeason] = {}
        self.premium_battle_pass_seasons: dict[int, BattlePassSeason] = {}
        self.battle_pass_progress: dict[tuple[int, int], BattlePassProgress] = {}
        self.premium_battle_pass_progress: dict[tuple[int, int], BattlePassProgress] = {}
        self.battles: dict[int, Battle] = {}
        self.ideas: dict[int, Idea] = {}
        self.standard_cards: list[int] = []
        self.universes: list[str] = []
        self.free_rewards: dict[str, dict[str, int]] = {}
        self.search_queue: dict[int, int] = {}
        self.deck_drafts: dict[int, list[int]] = {}
        self.action_events: list[tuple[int, str]] = []

        self.load()
        if import_catalog_path is not None:
            self._import_catalog_if_needed(Path(import_catalog_path))
        if not self.universes:
            self.universes = [
                item.value
                for item in Universe
                if item.value not in {"unknown", "other"}
            ]

    def load(self) -> None:
        """Load every document from the database into store dictionaries."""

        with Session(self.engine) as session:
            documents = {
                row.name: row.payload
                for row in session.scalars(select(StateDocumentORM))
            }

        for section, codec in SECTION_CODECS.items():
            setattr(self, section, codec.load(documents.get(section)))

    def save(self) -> None:
        """Persist every loaded section into the database."""

        with Session(self.engine) as session:
            for section, codec in SECTION_CODECS.items():
                payload = codec.dump(getattr(self, section))
                row = session.get(StateDocumentORM, section)
                if row is None:
                    row = StateDocumentORM(name=section, payload=payload)
                else:
                    row.payload = payload
                session.add(row)
            session.commit()

    def close(self) -> None:
        """Dispose the underlying database engine."""

        self.engine.dispose()

    def next_id(self, section: str) -> int:
        """Return the next numeric identifier for one mapping section."""

        items = getattr(self, section)
        return max(items, default=0) + 1

    def _import_catalog_if_needed(self, path: Path) -> None:
        """Seed catalog documents from the legacy JSON file on first boot."""

        if not path.exists():
            return
        if any(bool(getattr(self, section)) for section in CATALOG_SECTIONS):
            return

        legacy = CatalogStore(path)
        self.cards = dict(legacy.cards)
        self.profile_backgrounds = dict(legacy.profile_backgrounds)
        self.banners = dict(legacy.banners)
        self.shop_items = dict(legacy.shop_items)
        self.battle_pass_seasons = dict(legacy.battle_pass_seasons)
        self.premium_battle_pass_seasons = dict(legacy.premium_battle_pass_seasons)
        self.ideas = dict(legacy.ideas)
        self.standard_cards = list(legacy.standard_cards)
        self.universes = list(legacy.universes)
        self.free_rewards = dict(legacy.free_rewards)
        self.save()


class _Repository(Generic[T]):
    """Base repository backed by one store section."""

    section: str

    def __init__(self, store: PersistentStateStore) -> None:
        self.store = store
        self.items: dict[RepositoryKey, T] = getattr(store, self.section)

    async def get_by_id(self, item_id: RepositoryKey) -> T | None:
        return self.items.get(item_id)

    async def add(self, item: T) -> T:
        self.items[self._item_key(item)] = item
        self.store.save()
        return item

    async def save(self, item: T) -> T:
        return await self.add(item)

    async def delete(self, item_id: RepositoryKey) -> None:
        self.items.pop(item_id, None)
        self.store.save()

    def _item_key(self, item: T) -> int:
        return getattr(item, "id")


class PersistentPlayerRepository(_Repository[Player]):
    """Player storage with telegram-id lookup."""

    section = "players"

    async def add(self, item: Player) -> Player:
        self.items[item.telegram_id] = item
        self.store.save()
        return item

    async def save(self, item: Player) -> Player:
        return await self.add(item)

    async def get_by_telegram_id(self, telegram_id: int) -> Player | None:
        return self.items.get(telegram_id)

    async def get_by_nickname(self, nickname: str) -> Player | None:
        normalized = nickname.casefold()
        for player in self.items.values():
            if player.nickname and player.nickname.casefold() == normalized:
                return player
        return None

    async def list_all(self) -> list[Player]:
        return list(self.items.values())


class PersistentCardTemplateRepository(_Repository[CardTemplate]):
    """Card template storage."""

    section = "cards"

    async def list_active(self) -> list[CardTemplate]:
        return [item for item in self.items.values() if item.is_available]


class PersistentPlayerCardRepository(_Repository[PlayerCard]):
    """Owned cards indexed by id."""

    section = "player_cards"

    async def list_by_owner(self, owner_player_id: int) -> list[PlayerCard]:
        return [
            card
            for card in self.items.values()
            if card.owner_player_id == owner_player_id
        ]


class PersistentProfileBackgroundRepository(_Repository[ProfileBackgroundTemplate]):
    """Profile-background template storage."""

    section = "profile_backgrounds"

    async def list_all(self) -> list[ProfileBackgroundTemplate]:
        return list(self.items.values())


class PersistentClanRepository(_Repository[Clan]):
    """Clan storage with helper lookups."""

    section = "clans"

    async def find_by_player(self, player_id: int) -> Clan | None:
        for clan in self.items.values():
            if player_id in clan.members:
                return clan
        return None

    async def list_all(self) -> list[Clan]:
        return list(self.items.values())


class PersistentBannerRepository(_Repository[Banner]):
    """Banner storage with visibility filters."""

    section = "banners"

    async def list_available(self) -> list[Banner]:
        return [banner for banner in self.items.values() if banner.is_available()]


class PersistentShopRepository(_Repository[ShopItem]):
    """Shop storage with active-item filters."""

    section = "shop_items"

    async def list_active(self) -> list[ShopItem]:
        return [item for item in self.items.values() if item.is_active]


class PersistentIdeaRepository(_Repository[Idea]):
    """Idea storage with list access."""

    section = "ideas"

    async def list_all(self) -> list[Idea]:
        return list(self.items.values())


class PersistentBattlePassSeasonRepository(_Repository[BattlePassSeason]):
    """Battle pass season storage."""

    section = "battle_pass_seasons"

    async def list_active(self) -> list[BattlePassSeason]:
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self) -> list[BattlePassSeason]:
        return list(self.items.values())


class PersistentPremiumBattlePassSeasonRepository(_Repository[BattlePassSeason]):
    """Premium battle pass season storage."""

    section = "premium_battle_pass_seasons"

    async def list_active(self) -> list[BattlePassSeason]:
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self) -> list[BattlePassSeason]:
        return list(self.items.values())


class PersistentBattlePassProgressRepository(_Repository[BattlePassProgress]):
    """Battle pass progress keyed by player and season."""

    section = "battle_pass_progress"

    async def get_for_player(
        self,
        player_id: int,
        season_id: int,
    ) -> BattlePassProgress | None:
        return self.items.get((player_id, season_id))

    async def save(self, item: BattlePassProgress) -> BattlePassProgress:
        self.items[(item.player_id, item.season_id)] = item
        self.store.save()
        return item


class PersistentPremiumBattlePassProgressRepository(_Repository[BattlePassProgress]):
    """Premium battle pass progress keyed by player and season."""

    section = "premium_battle_pass_progress"

    async def get_for_player(
        self,
        player_id: int,
        season_id: int,
    ) -> BattlePassProgress | None:
        return self.items.get((player_id, season_id))

    async def save(self, item: BattlePassProgress) -> BattlePassProgress:
        self.items[(item.player_id, item.season_id)] = item
        self.store.save()
        return item


class PersistentBattleRepository(_Repository[Battle]):
    """Battle storage with active lookup."""

    section = "battles"

    async def get_active_by_player(self, player_id: int) -> Battle | None:
        for battle in self.items.values():
            if battle.status.value == "active" and player_id in {
                battle.player_one_id,
                battle.player_two_id,
            }:
                return battle
        return None
