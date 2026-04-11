"""Persistent repositories backed by a single SQLAlchemy document store."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from yuqa.infrastructure.local import CatalogStore
from yuqa.infrastructure.sqlalchemy.models import StateDocumentORM
from yuqa.infrastructure.sqlalchemy.serialization import (
    CATALOG_SECTIONS,
    SECTION_CODECS,
)
from yuqa.shared.enums import Universe


def create_sync_engine(database_url: str):
    """Create the synchronous engine used by the document store."""

    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        if db_path.name:
            db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, future=True, pool_pre_ping=True)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _connection_record) -> None:
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

        self.players = {}
        self.player_cards = {}
        self.cards = {}
        self.profile_backgrounds = {}
        self.clans = {}
        self.banners = {}
        self.shop_items = {}
        self.battle_pass_seasons = {}
        self.battle_pass_progress = {}
        self.battles = {}
        self.ideas = {}
        self.standard_cards = []
        self.universes = []
        self.free_rewards = {}
        self.search_queue = {}
        self.deck_drafts = {}
        self.action_events = []

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
        """Load every document from the database into memory."""

        with Session(self.engine) as session:
            documents = {
                row.name: row.payload
                for row in session.scalars(select(StateDocumentORM))
            }

        for section, codec in SECTION_CODECS.items():
            setattr(self, section, codec.load(documents.get(section)))

    def save(self) -> None:
        """Persist every in-memory section into the database."""

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
        self.ideas = dict(legacy.ideas)
        self.standard_cards = list(legacy.standard_cards)
        self.universes = list(legacy.universes)
        self.free_rewards = dict(legacy.free_rewards)
        self.save()


class _Repository:
    """Base repository backed by one store section."""

    section: str

    def __init__(self, store: PersistentStateStore) -> None:
        self.store = store
        self.items = getattr(store, self.section)

    async def get_by_id(self, item_id):
        return self.items.get(item_id)

    async def add(self, item):
        self.items[self._item_key(item)] = item
        self.store.save()
        return item

    async def save(self, item):
        return await self.add(item)

    async def delete(self, item_id):
        self.items.pop(item_id, None)
        self.store.save()

    def _item_key(self, item):
        return item.id


class PersistentPlayerRepository(_Repository):
    """Player storage with telegram-id lookup."""

    section = "players"

    async def add(self, item):
        self.items[item.telegram_id] = item
        self.store.save()
        return item

    async def save(self, item):
        return await self.add(item)

    async def get_by_telegram_id(self, telegram_id):
        return self.items.get(telegram_id)

    async def get_by_nickname(self, nickname):
        normalized = nickname.casefold()
        for player in self.items.values():
            if player.nickname and player.nickname.casefold() == normalized:
                return player
        return None

    async def list_all(self):
        return list(self.items.values())


class PersistentCardTemplateRepository(_Repository):
    """Card template storage."""

    section = "cards"

    async def list_active(self):
        return [item for item in self.items.values() if item.is_available]


class PersistentPlayerCardRepository(_Repository):
    """Owned cards indexed by id."""

    section = "player_cards"

    async def list_by_owner(self, owner_player_id):
        return [
            card
            for card in self.items.values()
            if card.owner_player_id == owner_player_id
        ]


class PersistentProfileBackgroundRepository(_Repository):
    """Profile-background template storage."""

    section = "profile_backgrounds"

    async def list_all(self):
        return list(self.items.values())


class PersistentClanRepository(_Repository):
    """Clan storage with helper lookups."""

    section = "clans"

    async def find_by_player(self, player_id):
        for clan in self.items.values():
            if player_id in clan.members:
                return clan
        return None

    async def list_all(self):
        return list(self.items.values())


class PersistentBannerRepository(_Repository):
    """Banner storage with visibility filters."""

    section = "banners"

    async def list_available(self):
        return [banner for banner in self.items.values() if banner.is_available()]


class PersistentShopRepository(_Repository):
    """Shop storage with active-item filters."""

    section = "shop_items"

    async def list_active(self):
        return [item for item in self.items.values() if item.is_active]


class PersistentIdeaRepository(_Repository):
    """Idea storage with list access."""

    section = "ideas"

    async def list_all(self):
        return list(self.items.values())


class PersistentBattlePassSeasonRepository(_Repository):
    """Battle pass season storage."""

    section = "battle_pass_seasons"

    async def list_active(self):
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self):
        return list(self.items.values())


class PersistentBattlePassProgressRepository(_Repository):
    """Battle pass progress keyed by player and season."""

    section = "battle_pass_progress"

    async def get_for_player(self, player_id, season_id):
        return self.items.get((player_id, season_id))

    async def save(self, item):
        self.items[(item.player_id, item.season_id)] = item
        self.store.save()
        return item


class PersistentBattleRepository(_Repository):
    """Battle storage with active lookup."""

    section = "battles"

    async def get_active_by_player(self, player_id):
        for battle in self.items.values():
            if battle.status.value == "active" and player_id in {
                battle.player_one_id,
                battle.player_two_id,
            }:
                return battle
        return None
