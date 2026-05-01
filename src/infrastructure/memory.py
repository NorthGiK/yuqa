"""Small in-memory repositories used by the application and tests."""

from typing import Generic, TypeVar

from src.banners.domain.entities import Banner
from src.battle_pass.domain.entities import BattlePassProgress, BattlePassSeason
from src.battles.domain.entities import Battle
from src.cards.domain.entities import CardTemplate, PlayerCard
from src.clans.domain.entities import Clan
from src.ideas.domain.entities import Idea
from src.players.domain.entities import Player, ProfileBackgroundTemplate
from src.quests.domain.entities import QuestDefinition, QuestProgress
from src.shop.domain.entities import ShopItem


RepositoryKey = int | tuple[int, int]
T = TypeVar("T")


class _Store(Generic[T]):
    """Dictionary-backed repository base."""

    def __init__(self) -> None:
        self.items: dict[RepositoryKey, T] = {}

    async def get_by_id(self, item_id: RepositoryKey) -> T | None:
        return self.items.get(item_id)

    async def add(self, item: T) -> T:
        self.items[self._item_key(item)] = item
        return item

    async def save(self, item: T) -> T:
        return await self.add(item)

    async def delete(self, item_id: RepositoryKey) -> None:
        self.items.pop(item_id, None)

    def _item_key(self, item: T) -> int:
        return getattr(item, "id")


class InMemoryPlayerRepository(_Store[Player]):
    """Player storage with telegram-id lookup."""

    async def add(self, item: Player) -> Player:
        self.items[item.telegram_id] = item
        return item

    async def save(self, item: Player) -> Player:
        return await self.add(item)

    async def get_by_id(self, telegram_id: int) -> Player | None:
        return self.items.get(telegram_id)

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


class InMemoryCardTemplateRepository(_Store[CardTemplate]):
    """Card template storage."""

    async def list_active(self) -> list[CardTemplate]:
        return [item for item in self.items.values() if item.is_available]


class InMemoryPlayerCardRepository(_Store[PlayerCard]):
    """Owned cards indexed by their id."""

    async def list_by_owner(self, owner_player_id: int) -> list[PlayerCard]:
        return [
            card
            for card in self.items.values()
            if card.owner_player_id == owner_player_id
        ]


class InMemoryClanRepository(_Store[Clan]):
    """Clan storage with helper lookups."""

    async def find_by_player(self, player_id: int) -> Clan | None:
        for clan in self.items.values():
            if player_id in clan.members:
                return clan
        return None

    async def list_all(self) -> list[Clan]:
        return list(self.items.values())


class InMemoryBannerRepository(_Store[Banner]):
    """Banner storage with availability filters."""

    async def list_available(self) -> list[Banner]:
        return [banner for banner in self.items.values() if banner.is_available()]


class InMemoryProfileBackgroundRepository(_Store[ProfileBackgroundTemplate]):
    """Profile-background template storage."""

    async def list_all(self) -> list[ProfileBackgroundTemplate]:
        return list(self.items.values())


class InMemoryIdeaRepository(_Store[Idea]):
    """Idea storage with full-list access."""

    async def list_all(self) -> list[Idea]:
        return list(self.items.values())


class InMemoryShopRepository(_Store[ShopItem]):
    """Shop storage with active-item filters."""

    async def list_active(self) -> list[ShopItem]:
        return [item for item in self.items.values() if item.is_active]


class InMemoryQuestRepository(_Store[QuestDefinition]):
    """Quest storage."""

    async def list_active(self) -> list[QuestDefinition]:
        return [item for item in self.items.values() if item.is_active]


class InMemoryQuestProgressRepository(_Store[QuestProgress]):
    """Quest progress storage keyed by a synthetic id."""

    async def list_for_player(self, player_id: int) -> list[QuestProgress]:
        return [row for row in self.items.values() if row.player_id == player_id]


class InMemoryBattlePassSeasonRepository(_Store[BattlePassSeason]):
    """Battle pass season storage."""

    async def list_active(self) -> list[BattlePassSeason]:
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self) -> list[BattlePassSeason]:
        return list(self.items.values())


class InMemoryPremiumBattlePassSeasonRepository(_Store[BattlePassSeason]):
    """Premium battle pass season storage."""

    async def list_active(self) -> list[BattlePassSeason]:
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self) -> list[BattlePassSeason]:
        return list(self.items.values())


class InMemoryBattlePassProgressRepository(_Store[BattlePassProgress]):
    """Battle pass progress storage."""

    async def get_for_player(
        self,
        player_id: int,
        season_id: int,
    ) -> BattlePassProgress | None:
        return self.items.get((player_id, season_id))

    async def save(self, item: BattlePassProgress) -> BattlePassProgress:
        self.items[(item.player_id, item.season_id)] = item
        return item


class InMemoryPremiumBattlePassProgressRepository(_Store[BattlePassProgress]):
    """Premium battle pass progress storage."""

    async def get_for_player(
        self,
        player_id: int,
        season_id: int,
    ) -> BattlePassProgress | None:
        return self.items.get((player_id, season_id))

    async def save(self, item: BattlePassProgress) -> BattlePassProgress:
        self.items[(item.player_id, item.season_id)] = item
        return item


class InMemoryBattleRepository(_Store[Battle]):
    """Battle storage with active lookup."""

    async def get_active_by_player(self, player_id: int) -> Battle | None:
        for battle in self.items.values():
            if battle.status.value == "active" and player_id in {
                battle.player_one_id,
                battle.player_two_id,
            }:
                return battle
        return None
