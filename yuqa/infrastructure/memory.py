"""Small in-memory repositories used by the application and tests."""


class _Store:
    """Dictionary-backed repository base."""

    def __init__(self):
        self.items = {}

    async def get_by_id(self, item_id):
        return self.items.get(item_id)

    async def add(self, item):
        self.items[item.id] = item
        return item

    async def save(self, item):
        return await self.add(item)

    async def delete(self, item_id):
        self.items.pop(item_id, None)


class InMemoryPlayerRepository(_Store):
    """Player storage with telegram-id lookup."""

    async def add(self, item):
        self.items[item.telegram_id] = item
        return item

    async def save(self, item):
        return await self.add(item)

    async def get_by_id(self, telegram_id):
        return self.items.get(telegram_id)

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


class InMemoryCardTemplateRepository(_Store):
    """Card template storage."""

    async def list_active(self):
        return [item for item in self.items.values() if item.is_available]


class InMemoryPlayerCardRepository(_Store):
    """Owned cards indexed by their id."""

    async def list_by_owner(self, owner_player_id):
        return [
            card
            for card in self.items.values()
            if card.owner_player_id == owner_player_id
        ]


class InMemoryClanRepository(_Store):
    """Clan storage with helper lookups."""

    async def find_by_player(self, player_id):
        for clan in self.items.values():
            if player_id in clan.members:
                return clan

    async def list_all(self):
        return list(self.items.values())


class InMemoryBannerRepository(_Store):
    """Banner storage with availability filters."""

    async def list_available(self):
        return [banner for banner in self.items.values() if banner.is_available()]


class InMemoryProfileBackgroundRepository(_Store):
    """Profile-background template storage."""

    async def list_all(self):
        return list(self.items.values())


class InMemoryIdeaRepository(_Store):
    """Idea storage with full-list access."""

    async def list_all(self):
        return list(self.items.values())


class InMemoryShopRepository(_Store):
    """Shop storage with active-item filters."""

    async def list_active(self):
        return [item for item in self.items.values() if item.is_active]


class InMemoryQuestRepository(_Store):
    """Quest storage."""

    async def list_active(self):
        return [item for item in self.items.values() if item.is_active]


class InMemoryQuestProgressRepository(_Store):
    """Quest progress storage keyed by a synthetic id."""

    async def list_for_player(self, player_id):
        return [row for row in self.items.values() if row.player_id == player_id]


class InMemoryBattlePassSeasonRepository(_Store):
    """Battle pass season storage."""

    async def list_active(self):
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self):
        return list(self.items.values())


class InMemoryPremiumBattlePassSeasonRepository(_Store):
    """Premium battle pass season storage."""

    async def list_active(self):
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self):
        return list(self.items.values())


class InMemoryBattlePassProgressRepository(_Store):
    """Battle pass progress storage."""

    async def get_for_player(self, player_id, season_id):
        return self.items.get((player_id, season_id))

    async def save(self, item):
        self.items[(item.player_id, item.season_id)] = item
        return item


class InMemoryPremiumBattlePassProgressRepository(_Store):
    """Premium battle pass progress storage."""

    async def get_for_player(self, player_id, season_id):
        return self.items.get((player_id, season_id))

    async def save(self, item):
        self.items[(item.player_id, item.season_id)] = item
        return item


class InMemoryBattleRepository(_Store):
    """Battle storage with active lookup."""

    async def get_active_by_player(self, player_id):
        for battle in self.items.values():
            if battle.status.value == "active" and player_id in {
                battle.player_one_id,
                battle.player_two_id,
            }:
                return battle
