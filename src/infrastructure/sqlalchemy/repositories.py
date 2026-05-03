"""Persistent repositories backed by relational SQLAlchemy tables."""

import json
from pathlib import Path
from typing import Any, Generic, TypeVar

from sqlalchemy import create_engine, delete, event, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.banners.domain.entities import Banner
from src.battle_pass.domain.entities import BattlePassProgress, BattlePassSeason
from src.battles.domain.entities import Battle
from src.cards.domain.entities import CardTemplate, PlayerCard
from src.clans.domain.entities import Clan
from src.infrastructure.local import CatalogStore
from src.infrastructure.sqlalchemy.base import Base
from src.infrastructure.sqlalchemy.models import (
    ActionEventORM,
    BannerORM,
    BattleORM,
    BattlePassProgressORM,
    BattlePassSeasonORM,
    CardTemplateORM,
    ClanORM,
    DeckDraftCardORM,
    FreeRewardConfigORM,
    IdeaORM,
    PlayerCardORM,
    PlayerORM,
    PremiumBattlePassProgressORM,
    PremiumBattlePassSeasonORM,
    ProfileBackgroundORM,
    QuestDefinitionORM,
    QuestProgressORM,
    SearchQueueORM,
    ShopItemORM,
    StandardCardORM,
    UniverseORM,
)
from src.infrastructure.sqlalchemy.serialization import (
    CATALOG_SECTIONS,
    SECTION_CODECS,
)
from src.infrastructure.sqlalchemy.urls import ensure_sqlite_parent, sync_database_url
from src.ideas.domain.entities import Idea
from src.players.domain.entities import Player, ProfileBackgroundTemplate
from src.quests.domain.entities import QuestDefinition, QuestProgress
from src.shared.enums import Universe
from src.shop.domain.entities import ShopItem


RepositoryKey = int | tuple[int, int]
T = TypeVar("T")


def create_sync_engine(database_url: str) -> Engine:
    """Create the synchronous engine used by the repositories."""

    database_url = sync_database_url(database_url)
    ensure_sqlite_parent(database_url)

    engine = create_engine(database_url, future=True, pool_pre_ping=True)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _configure_sqlite(
            dbapi_connection: Any,
            _connection_record: Any,
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


def _legacy_json(value: Any) -> Any:
    """Decode legacy JSON values returned as strings by some DB drivers."""

    if isinstance(value, str):
        return json.loads(value)
    return value


class PersistentStateStore:
    """State store backed by per-aggregate relational tables."""

    def __init__(
        self,
        database_url: str,
        import_catalog_path: str | Path | None = None,
    ) -> None:
        self.database_url = database_url
        self.engine = create_sync_engine(database_url)
        Base.metadata.create_all(self.engine)

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
        self.premium_battle_pass_progress: dict[
            tuple[int, int], BattlePassProgress
        ] = {}
        self.quest_definitions: dict[int, QuestDefinition] = {}
        self.quest_progress: dict[tuple[int, int], QuestProgress] = {}
        self.battles: dict[int, Battle] = {}
        self.ideas: dict[int, Idea] = {}
        self.standard_cards: list[int] = []
        self.universes: list[str] = []
        self.free_rewards: dict[str, dict[str, int]] = {}
        self.search_queue: dict[int, int] = {}
        self.deck_drafts: dict[int, list[int]] = {}
        self.action_events: list[tuple[int, str]] = []

        self.load()
        if self._is_empty() and self._import_legacy_documents_if_needed():
            self.load()
        if import_catalog_path is not None:
            self._import_catalog_if_needed(Path(import_catalog_path))
        if not self.universes:
            self.universes = [
                item.value
                for item in Universe
                if item.value not in {"unknown", "other"}
            ]
            self.save_runtime_state()

    def load(self) -> None:
        """Load every relational table into the service-facing dictionaries."""

        with Session(self.engine) as session:
            self.players = self._load_mapping(
                session, "players", PlayerORM, lambda row: str(row.telegram_id)
            )
            self.player_cards = self._load_mapping(
                session, "player_cards", PlayerCardORM, lambda row: str(row.id)
            )
            self.cards = self._load_mapping(
                session, "cards", CardTemplateORM, lambda row: str(row.id)
            )
            self.profile_backgrounds = self._load_mapping(
                session,
                "profile_backgrounds",
                ProfileBackgroundORM,
                lambda row: str(row.id),
            )
            self.clans = self._load_mapping(
                session, "clans", ClanORM, lambda row: str(row.id)
            )
            self.banners = self._load_mapping(
                session, "banners", BannerORM, lambda row: str(row.id)
            )
            self.shop_items = self._load_mapping(
                session, "shop_items", ShopItemORM, lambda row: str(row.id)
            )
            self.ideas = self._load_mapping(
                session, "ideas", IdeaORM, lambda row: str(row.id)
            )
            self.battle_pass_seasons = self._load_mapping(
                session,
                "battle_pass_seasons",
                BattlePassSeasonORM,
                lambda row: str(row.id),
            )
            self.premium_battle_pass_seasons = self._load_mapping(
                session,
                "premium_battle_pass_seasons",
                PremiumBattlePassSeasonORM,
                lambda row: str(row.id),
            )
            self.battle_pass_progress = self._load_mapping(
                session,
                "battle_pass_progress",
                BattlePassProgressORM,
                lambda row: f"{row.player_id}:{row.season_id}",
            )
            self.premium_battle_pass_progress = self._load_mapping(
                session,
                "premium_battle_pass_progress",
                PremiumBattlePassProgressORM,
                lambda row: f"{row.player_id}:{row.season_id}",
            )
            self.quest_definitions = self._load_mapping(
                session,
                "quest_definitions",
                QuestDefinitionORM,
                lambda row: str(row.id),
            )
            self.quest_progress = self._load_mapping(
                session,
                "quest_progress",
                QuestProgressORM,
                lambda row: f"{row.player_id}:{row.quest_id}",
            )
            self.battles = self._load_mapping(
                session, "battles", BattleORM, lambda row: str(row.id)
            )
            self.standard_cards = [
                row.card_template_id
                for row in session.scalars(
                    select(StandardCardORM).order_by(StandardCardORM.position)
                )
            ]
            self.universes = [
                row.value
                for row in session.scalars(
                    select(UniverseORM).order_by(UniverseORM.position)
                )
            ]
            free_rewards = session.get(FreeRewardConfigORM, "free_rewards")
            self.free_rewards = dict(free_rewards.payload) if free_rewards else {}
            self.search_queue = {
                row.player_id: row.rating
                for row in session.scalars(select(SearchQueueORM))
            }
            self.deck_drafts = {}
            for row in session.scalars(
                select(DeckDraftCardORM).order_by(
                    DeckDraftCardORM.player_id,
                    DeckDraftCardORM.position,
                )
            ):
                self.deck_drafts.setdefault(row.player_id, []).append(row.card_id)
            self.action_events = [
                (row.player_id, row.action)
                for row in session.scalars(
                    select(ActionEventORM).order_by(ActionEventORM.position)
                )
            ]

    def save(self) -> None:
        """Persist every loaded section into relational tables."""

        with Session(self.engine) as session:
            self._replace_mapping(session, "players", PlayerORM, self.players)
            self._replace_mapping(
                session, "player_cards", PlayerCardORM, self.player_cards
            )
            self._replace_mapping(session, "cards", CardTemplateORM, self.cards)
            self._replace_mapping(
                session,
                "profile_backgrounds",
                ProfileBackgroundORM,
                self.profile_backgrounds,
            )
            self._replace_mapping(session, "clans", ClanORM, self.clans)
            self._replace_mapping(session, "banners", BannerORM, self.banners)
            self._replace_mapping(session, "shop_items", ShopItemORM, self.shop_items)
            self._replace_mapping(session, "ideas", IdeaORM, self.ideas)
            self._replace_mapping(
                session,
                "battle_pass_seasons",
                BattlePassSeasonORM,
                self.battle_pass_seasons,
            )
            self._replace_mapping(
                session,
                "premium_battle_pass_seasons",
                PremiumBattlePassSeasonORM,
                self.premium_battle_pass_seasons,
            )
            self._replace_mapping(
                session,
                "battle_pass_progress",
                BattlePassProgressORM,
                self.battle_pass_progress,
            )
            self._replace_mapping(
                session,
                "premium_battle_pass_progress",
                PremiumBattlePassProgressORM,
                self.premium_battle_pass_progress,
            )
            self._replace_mapping(
                session,
                "quest_definitions",
                QuestDefinitionORM,
                self.quest_definitions,
            )
            self._replace_mapping(
                session,
                "quest_progress",
                QuestProgressORM,
                self.quest_progress,
            )
            self._replace_mapping(session, "battles", BattleORM, self.battles)
            self._replace_runtime_tables(session)
            session.commit()

    def save_runtime_state(self) -> None:
        """Persist runtime-only dict/list tables without rewriting aggregates."""

        with Session(self.engine) as session:
            self._replace_runtime_tables(session)
            session.commit()

    def save_item(self, section: str, key: RepositoryKey, item: object) -> None:
        """Upsert one aggregate row."""

        with Session(self.engine) as session:
            session.merge(self._row_for_item(section, key, item))
            session.commit()

    def delete_item(self, section: str, key: RepositoryKey) -> None:
        """Delete one aggregate row."""

        model = self._model_for_section(section)
        with Session(self.engine) as session:
            row = session.get(model, key)
            if row is not None:
                session.delete(row)
                session.commit()

    def close(self) -> None:
        """Dispose the underlying database engine."""

        self.engine.dispose()

    def next_id(self, section: str) -> int:
        """Return the next numeric identifier for one mapping section."""

        items = getattr(self, section)
        return max(items, default=0) + 1

    def _is_empty(self) -> bool:
        """Return True when no relational data has been loaded."""

        return not any(
            bool(getattr(self, section))
            for section in (
                "players",
                "player_cards",
                "cards",
                "profile_backgrounds",
                "clans",
                "banners",
                "shop_items",
                "battle_pass_seasons",
                "premium_battle_pass_seasons",
                "battle_pass_progress",
                "premium_battle_pass_progress",
                "quest_definitions",
                "quest_progress",
                "battles",
                "ideas",
                "standard_cards",
                "universes",
                "free_rewards",
                "search_queue",
                "deck_drafts",
                "action_events",
            )
        )

    def _import_legacy_documents_if_needed(self) -> bool:
        """Import the old state_documents payload into relational tables once."""

        with self.engine.connect() as connection:
            if not inspect(connection).has_table("state_documents"):
                return False
            documents = {
                row.name: _legacy_json(row.payload)
                for row in connection.execute(
                    text("SELECT name, payload FROM state_documents")
                ).mappings()
            }
        if not documents:
            return False

        for section, codec in SECTION_CODECS.items():
            setattr(self, section, codec.load(documents.get(section)))
        self.save()
        return True

    def _import_catalog_if_needed(self, path: Path) -> None:
        """Seed catalog tables from the legacy JSON file on first boot."""

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

    def _load_mapping(
        self,
        session: Session,
        section: str,
        model: type[Any],
        key: Any,
    ) -> Any:
        """Load one mapping section through its existing domain codec."""

        payload = {key(row): row.payload for row in session.scalars(select(model))}
        return SECTION_CODECS[section].load(payload)

    def _replace_mapping(
        self,
        session: Session,
        section: str,
        model: type[Any],
        items: dict[Any, Any],
    ) -> None:
        """Replace one aggregate table from the current service-facing mapping."""

        session.execute(delete(model))
        for key, item in items.items():
            session.add(self._row_for_item(section, key, item))

    def _replace_runtime_tables(self, session: Session) -> None:
        """Replace small runtime/config tables from their in-memory containers."""

        session.execute(delete(StandardCardORM))
        session.execute(delete(UniverseORM))
        session.execute(delete(FreeRewardConfigORM))
        session.execute(delete(SearchQueueORM))
        session.execute(delete(DeckDraftCardORM))
        session.execute(delete(ActionEventORM))

        for position, card_id in enumerate(self.standard_cards):
            session.add(StandardCardORM(position=position, card_template_id=card_id))
        for position, value in enumerate(dict.fromkeys(self.universes)):
            session.add(UniverseORM(position=position, value=value))
        if self.free_rewards:
            session.add(
                FreeRewardConfigORM(name="free_rewards", payload=self.free_rewards)
            )
        for player_id, rating in self.search_queue.items():
            session.add(SearchQueueORM(player_id=player_id, rating=rating))
        for player_id, card_ids in self.deck_drafts.items():
            for position, card_id in enumerate(card_ids):
                session.add(
                    DeckDraftCardORM(
                        player_id=player_id,
                        position=position,
                        card_id=card_id,
                    )
                )
        for position, (player_id, action) in enumerate(self.action_events[-1000:]):
            session.add(
                ActionEventORM(position=position, player_id=player_id, action=action)
            )

    def _payload_for_item(self, section: str, key: RepositoryKey, item: object) -> Any:
        """Serialize one item with the existing domain codec for that section."""

        dumped = SECTION_CODECS[section].dump({key: item})
        return next(iter(dumped.values()))

    def _row_for_item(self, section: str, key: RepositoryKey, item: object) -> object:
        """Build one ORM row for a domain entity."""

        payload = self._payload_for_item(section, key, item)
        if section == "players":
            player = item
            return PlayerORM(
                telegram_id=player.telegram_id,
                nickname=player.nickname,
                rating=player.rating,
                clan_id=player.clan_id,
                is_banned=player.is_banned,
                is_premium=player.is_premium,
                payload=payload,
            )
        if section == "player_cards":
            card = item
            return PlayerCardORM(
                id=card.id,
                owner_player_id=card.owner_player_id,
                template_id=card.template_id,
                level=card.level,
                copies_owned=card.copies_owned,
                payload=payload,
            )
        if section == "cards":
            template = item
            return CardTemplateORM(
                id=template.id,
                name=template.name,
                universe=template.universe_value(),
                rarity=template.rarity.value,
                is_available=template.is_available,
                payload=payload,
            )
        if section == "profile_backgrounds":
            background = item
            return ProfileBackgroundORM(
                id=background.id,
                rarity=background.rarity.value,
                storage_key=background.media.storage_key,
                payload=payload,
            )
        if section == "clans":
            clan = item
            return ClanORM(
                id=clan.id,
                owner_player_id=clan.owner_player_id,
                name=clan.name,
                rating=clan.rating,
                payload=payload,
            )
        if section == "banners":
            banner = item
            return BannerORM(
                id=banner.id,
                name=banner.name,
                banner_type=banner.banner_type.value,
                cost_resource=banner.cost_resource.value,
                is_active=banner.is_active,
                start_at=banner.date_range.start_at,
                end_at=banner.date_range.end_at,
                payload=payload,
            )
        if section == "shop_items":
            item_ = item
            return ShopItemORM(
                id=item_.id,
                sell_resource_type=item_.sell_resource_type.value,
                buy_resource_type=item_.buy_resource_type.value,
                price=item_.price,
                quantity=item_.quantity,
                is_active=item_.is_active,
                payload=payload,
            )
        if section == "ideas":
            idea = item
            return IdeaORM(
                id=idea.id,
                player_id=idea.player_id,
                status=idea.status.value,
                upvotes=idea.upvotes,
                downvotes=idea.downvotes,
                payload=payload,
            )
        if section in {"battle_pass_seasons", "premium_battle_pass_seasons"}:
            season = item
            model = (
                BattlePassSeasonORM
                if section == "battle_pass_seasons"
                else PremiumBattlePassSeasonORM
            )
            return model(
                id=season.id,
                name=season.name,
                start_at=season.start_at,
                end_at=season.end_at,
                is_active=season.is_active,
                payload=payload,
            )
        if section in {"battle_pass_progress", "premium_battle_pass_progress"}:
            progress = item
            model = (
                BattlePassProgressORM
                if section == "battle_pass_progress"
                else PremiumBattlePassProgressORM
            )
            return model(
                player_id=progress.player_id,
                season_id=progress.season_id,
                points=progress.points,
                payload=payload,
            )
        if section == "quest_definitions":
            definition = item
            return QuestDefinitionORM(
                id=definition.id,
                period=definition.period.value,
                action_type=definition.action_type.value,
                cooldown_seconds=int(definition.cooldown.total_seconds()),
                is_active=definition.is_active,
                payload=payload,
            )
        if section == "quest_progress":
            progress = item
            return QuestProgressORM(
                player_id=progress.player_id,
                quest_id=progress.quest_id,
                completed=progress.completed,
                completed_count=progress.completed_count,
                cooldown_until=progress.cooldown_until,
                payload=payload,
            )
        if section == "battles":
            battle = item
            return BattleORM(
                id=battle.id,
                player_one_id=battle.player_one_id,
                player_two_id=battle.player_two_id,
                status=battle.status.value,
                winner_id=battle.winner_id,
                payload=payload,
            )
        raise ValueError(f"unknown persistent section: {section}")

    @staticmethod
    def _model_for_section(section: str) -> type[Any]:
        """Return the ORM model for one aggregate section."""

        models: dict[str, type[Any]] = {
            "players": PlayerORM,
            "player_cards": PlayerCardORM,
            "cards": CardTemplateORM,
            "profile_backgrounds": ProfileBackgroundORM,
            "clans": ClanORM,
            "banners": BannerORM,
            "shop_items": ShopItemORM,
            "ideas": IdeaORM,
            "battle_pass_seasons": BattlePassSeasonORM,
            "premium_battle_pass_seasons": PremiumBattlePassSeasonORM,
            "battle_pass_progress": BattlePassProgressORM,
            "premium_battle_pass_progress": PremiumBattlePassProgressORM,
            "quest_definitions": QuestDefinitionORM,
            "quest_progress": QuestProgressORM,
            "battles": BattleORM,
        }
        return models[section]


class _Repository(Generic[T]):
    """Base repository backed by one relational table."""

    section: str

    def __init__(self, store: PersistentStateStore) -> None:
        self.store = store
        self.items: dict[RepositoryKey, T] = getattr(store, self.section)

    async def get_by_id(self, item_id: RepositoryKey) -> T | None:
        return self.items.get(item_id)

    async def add(self, item: T) -> T:
        key = self._item_key(item)
        self.items[key] = item
        self.store.save_item(self.section, key, item)
        return item

    async def save(self, item: T) -> T:
        return await self.add(item)

    async def delete(self, item_id: RepositoryKey) -> None:
        self.items.pop(item_id, None)
        self.store.delete_item(self.section, item_id)

    def _item_key(self, item: T) -> int:
        return getattr(item, "id")


class PersistentPlayerRepository(_Repository[Player]):
    """Player storage with telegram-id lookup."""

    section = "players"

    async def add(self, item: Player) -> Player:
        self.items[item.telegram_id] = item
        self.store.save_item(self.section, item.telegram_id, item)
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
        key = (item.player_id, item.season_id)
        self.items[key] = item
        self.store.save_item(self.section, key, item)
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
        key = (item.player_id, item.season_id)
        self.items[key] = item
        self.store.save_item(self.section, key, item)
        return item


class PersistentQuestRepository:
    """Quest definitions and per-player cooldown progress."""

    def __init__(self, store: PersistentStateStore) -> None:
        self.store = store
        self.items: dict[int, QuestDefinition] = store.quest_definitions
        self.progress_items: dict[tuple[int, int], QuestProgress] = store.quest_progress

    async def get_definition_by_id(self, quest_id: int) -> QuestDefinition | None:
        return self.items.get(quest_id)

    async def list_active_definitions(self) -> list[QuestDefinition]:
        return [
            definition for definition in self.items.values() if definition.is_active
        ]

    async def get_progress(
        self,
        player_id: int,
        quest_id: int,
    ) -> QuestProgress | None:
        return self.progress_items.get((player_id, quest_id))

    async def save_definition(self, definition: QuestDefinition) -> None:
        self.items[definition.id] = definition
        self.store.save_item("quest_definitions", definition.id, definition)

    async def save_progress(self, progress: QuestProgress) -> None:
        key = (progress.player_id, progress.quest_id)
        self.progress_items[key] = progress
        self.store.save_item("quest_progress", key, progress)

    async def delete_progress(self, progress_key: tuple[int, int]) -> None:
        self.progress_items.pop(progress_key, None)
        self.store.delete_item("quest_progress", progress_key)


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
