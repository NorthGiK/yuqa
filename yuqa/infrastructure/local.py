"""Local JSON-backed catalog used by admin-created content."""

import json
from datetime import datetime, timezone
from pathlib import Path

from yuqa.ideas.domain.entities import Idea
from yuqa.banners.domain.entities import Banner, BannerReward
from yuqa.battle_pass.domain.entities import BattlePassLevel, BattlePassSeason
from yuqa.cards.domain.entities import Ability, AbilityEffect, CardTemplate
from yuqa.players.domain.entities import ProfileBackgroundTemplate
from yuqa.quests.domain.entities import QuestReward
from yuqa.shop.domain.entities import ShopItem
from yuqa.shared.enums import (
    AbilityStat,
    AbilityTarget,
    BannerType,
    CardClass,
    IdeaStatus,
    ProfileBackgroundRarity,
    Rarity,
    ResourceType,
    RewardType,
    Universe,
)
from yuqa.shared.value_objects.date_range import DateRange
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.stat_block import StatBlock


def _dt(value: datetime | None) -> str | None:
    """Serialize a datetime into an ISO-8601 string."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    """Deserialize an ISO-8601 datetime string."""

    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _enum(value, enum_type):
    """Convert an enum value to its serialized form."""

    return value.value if value is not None else None


def _enum_from(value, enum_type):
    """Convert a serialized enum string back to the enum instance."""

    return None if value is None else enum_type(value)


def _stat_block_to_dict(block: StatBlock) -> dict:
    """Serialize a stat block."""

    return {"damage": block.damage, "health": block.health, "defense": block.defense}


def _stat_block_from_dict(data: dict) -> StatBlock:
    """Deserialize a stat block."""

    return StatBlock(data["damage"], data["health"], data["defense"])


def _image_ref_to_dict(image: ImageRef) -> dict:
    """Serialize an image reference."""

    return {
        "storage_key": image.storage_key,
        "content_type": image.content_type,
        "original_name": image.original_name,
    }


def _image_ref_from_dict(data: dict) -> ImageRef:
    """Deserialize an image reference."""

    return ImageRef(
        data["storage_key"],
        content_type=data.get("content_type", "image/png"),
        original_name=data.get("original_name"),
    )


def _effects_to_dict(effects: tuple[AbilityEffect, ...]) -> list[dict]:
    """Serialize ability effects."""

    return [
        {
            "target": _enum(effect.target, AbilityTarget),
            "stat": _enum(effect.stat, AbilityStat),
            "duration": effect.duration,
            "value": effect.value,
        }
        for effect in effects
    ]


def _effects_from_dict(items: list[dict]) -> tuple[AbilityEffect, ...]:
    """Deserialize ability effects."""

    return tuple(
        AbilityEffect(
            AbilityTarget(item["target"]),
            AbilityStat(item["stat"]),
            item["duration"],
            item["value"],
        )
        for item in items
    )


def _ability_to_dict(ability: Ability | None) -> dict | None:
    """Serialize an ability."""

    if ability is None:
        return None
    return {
        "cost": ability.cost,
        "cooldown": ability.cooldown,
        "effects": _effects_to_dict(ability.effects),
    }


def _ability_from_dict(data: dict | None) -> Ability | None:
    """Deserialize an ability."""

    if data is None:
        return None
    return Ability(data["cost"], data["cooldown"], _effects_from_dict(data["effects"]))


def _card_to_dict(card: CardTemplate) -> dict:
    """Serialize a card template."""

    return {
        "id": card.id,
        "name": card.name,
        "universe": getattr(card.universe, "value", card.universe),
        "rarity": _enum(card.rarity, Rarity),
        "image": _image_ref_to_dict(card.image),
        "card_class": _enum(card.card_class, CardClass),
        "base_stats": _stat_block_to_dict(card.base_stats),
        "ascended_stats": _stat_block_to_dict(card.ascended_stats),
        "ability": _ability_to_dict(card.ability),
        "ascended_ability": _ability_to_dict(card.ascended_ability),
        "is_available": card.is_available,
    }


def _card_from_dict(data: dict) -> CardTemplate:
    """Deserialize a card template."""

    return CardTemplate(
        id=data["id"],
        name=data["name"],
        universe=data["universe"],
        rarity=Rarity(data["rarity"]),
        image=_image_ref_from_dict(data["image"]),
        card_class=CardClass(data["card_class"]),
        base_stats=_stat_block_from_dict(data["base_stats"]),
        ascended_stats=_stat_block_from_dict(data["ascended_stats"]),
        ability=_ability_from_dict(data["ability"]),
        ascended_ability=_ability_from_dict(data.get("ascended_ability")),
        is_available=data.get("is_available", True),
    )


def _banner_reward_to_dict(reward: BannerReward) -> dict:
    """Serialize a banner reward."""

    return {
        "reward_type": _enum(reward.reward_type, RewardType),
        "resource_type": _enum(reward.resource_type, ResourceType),
        "card_template_id": reward.card_template_id,
        "profile_background_id": reward.profile_background_id,
        "quantity": reward.quantity,
        "rarity": _enum(reward.rarity, Rarity),
        "profile_background_rarity": _enum(
            reward.profile_background_rarity, ProfileBackgroundRarity
        ),
        "weight": reward.weight,
        "guaranteed_for_10_pull": reward.guaranteed_for_10_pull,
    }


def _banner_reward_from_dict(data: dict) -> BannerReward:
    """Deserialize a banner reward."""

    return BannerReward(
        RewardType(data["reward_type"]),
        resource_type=_enum_from(data.get("resource_type"), ResourceType),
        card_template_id=data.get("card_template_id"),
        profile_background_id=data.get("profile_background_id"),
        quantity=data.get("quantity", 0),
        rarity=_enum_from(data.get("rarity"), Rarity),
        profile_background_rarity=_enum_from(
            data.get("profile_background_rarity"), ProfileBackgroundRarity
        ),
        weight=data.get("weight", 1),
        guaranteed_for_10_pull=data.get("guaranteed_for_10_pull", False),
    )


def _banner_to_dict(banner: Banner) -> dict:
    """Serialize a banner."""

    return {
        "id": banner.id,
        "name": banner.name,
        "banner_type": _enum(banner.banner_type, BannerType),
        "cost_resource": _enum(banner.cost_resource, ResourceType),
        "pools": [_banner_reward_to_dict(item) for item in banner.pools],
        "date_range": {
            "start_at": _dt(banner.date_range.start_at),
            "end_at": _dt(banner.date_range.end_at),
        },
        "is_active": banner.is_active,
    }


def _banner_from_dict(data: dict) -> Banner:
    """Deserialize a banner."""

    dates = data.get("date_range", {})
    return Banner(
        id=data["id"],
        name=data["name"],
        banner_type=BannerType(data["banner_type"]),
        cost_resource=ResourceType(data["cost_resource"]),
        pools=[_banner_reward_from_dict(item) for item in data.get("pools", [])],
        date_range=DateRange(
            _parse_dt(dates.get("start_at")), _parse_dt(dates.get("end_at"))
        ),
        is_active=data.get("is_active", True),
    )


def _profile_background_to_dict(background: ProfileBackgroundTemplate) -> dict:
    """Serialize a profile background."""

    return {
        "id": background.id,
        "rarity": _enum(background.rarity, ProfileBackgroundRarity),
        "media": _image_ref_to_dict(background.media),
    }


def _profile_background_from_dict(data: dict) -> ProfileBackgroundTemplate:
    """Deserialize a profile background."""

    return ProfileBackgroundTemplate(
        id=data["id"],
        rarity=ProfileBackgroundRarity(data["rarity"]),
        media=_image_ref_from_dict(data["media"]),
    )


def _quest_reward_to_dict(reward: QuestReward) -> dict:
    """Serialize a quest or battle pass reward."""

    return {
        "coins": reward.coins,
        "crystals": reward.crystals,
        "orbs": reward.orbs,
        "battle_pass_points": reward.battle_pass_points,
    }


def _quest_reward_from_dict(data: dict) -> QuestReward:
    """Deserialize a quest or battle pass reward."""

    return QuestReward(
        coins=data.get("coins", 0),
        crystals=data.get("crystals", 0),
        orbs=data.get("orbs", 0),
        battle_pass_points=data.get("battle_pass_points", 0),
    )


def _battle_pass_level_to_dict(level: BattlePassLevel) -> dict:
    """Serialize a battle pass level."""

    return {
        "level_number": level.level_number,
        "required_points": level.required_points,
        "reward": _quest_reward_to_dict(level.reward),
    }


def _battle_pass_level_from_dict(data: dict) -> BattlePassLevel:
    """Deserialize a battle pass level."""

    return BattlePassLevel(
        data["level_number"],
        data["required_points"],
        _quest_reward_from_dict(data["reward"]),
    )


def _battle_pass_season_to_dict(season: BattlePassSeason) -> dict:
    """Serialize a battle pass season."""

    return {
        "id": season.id,
        "name": season.name,
        "start_at": _dt(season.start_at),
        "end_at": _dt(season.end_at),
        "levels": [_battle_pass_level_to_dict(item) for item in season.levels],
        "is_active": season.is_active,
    }


def _battle_pass_season_from_dict(data: dict) -> BattlePassSeason:
    """Deserialize a battle pass season."""

    return BattlePassSeason(
        id=data["id"],
        name=data["name"],
        start_at=_parse_dt(data["start_at"]),
        end_at=_parse_dt(data["end_at"]),
        levels=[_battle_pass_level_from_dict(item) for item in data.get("levels", [])],
        is_active=data.get("is_active", True),
    )


def _shop_to_dict(item: ShopItem) -> dict:
    """Serialize a shop item."""

    return {
        "id": item.id,
        "sell_resource_type": _enum(item.sell_resource_type, ResourceType),
        "buy_resource_type": _enum(item.buy_resource_type, ResourceType),
        "price": item.price,
        "quantity": item.quantity,
        "is_active": item.is_active,
    }


def _shop_from_dict(data: dict) -> ShopItem:
    """Deserialize a shop item."""

    return ShopItem(
        id=data["id"],
        sell_resource_type=ResourceType(data["sell_resource_type"]),
        buy_resource_type=ResourceType(data["buy_resource_type"]),
        price=data["price"],
        quantity=data["quantity"],
        is_active=data.get("is_active", True),
    )


def _idea_to_dict(idea: Idea) -> dict:
    """Serialize a player idea."""

    return {
        "id": idea.id,
        "player_id": idea.player_id,
        "title": idea.title,
        "description": idea.description,
        "status": _enum(idea.status, IdeaStatus),
        "created_at": _dt(idea.created_at),
        "votes": {str(player_id): value for player_id, value in idea.votes.items()},
    }


def _idea_from_dict(data: dict) -> Idea:
    """Deserialize a player idea."""

    return Idea(
        id=data["id"],
        player_id=data["player_id"],
        title=data["title"],
        description=data["description"],
        status=IdeaStatus(data.get("status", IdeaStatus.PENDING.value)),
        created_at=_parse_dt(data.get("created_at")) or datetime.now(timezone.utc),
        votes={
            int(player_id): int(value)
            for player_id, value in data.get("votes", {}).items()
        },
    )


class CatalogStore:
    """Local catalog with a single JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.cards: dict[int, CardTemplate] = {}
        self.profile_backgrounds: dict[int, ProfileBackgroundTemplate] = {}
        self.banners: dict[int, Banner] = {}
        self.shop_items: dict[int, ShopItem] = {}
        self.battle_pass_seasons: dict[int, BattlePassSeason] = {}
        self.ideas: dict[int, Idea] = {}
        self.standard_cards: list[int] = []
        self.universes: list[str] = [
            item.value for item in Universe if item.value not in {"unknown", "other"}
        ]
        self.free_rewards: dict[str, dict[str, int]] = {}
        self.load()

    def load(self) -> None:
        """Load catalog content from disk if the file exists."""

        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.cards = {
            item["id"]: _card_from_dict(item) for item in data.get("cards", [])
        }
        self.profile_backgrounds = {
            item["id"]: _profile_background_from_dict(item)
            for item in data.get("profile_backgrounds", [])
        }
        self.banners = {
            item["id"]: _banner_from_dict(item) for item in data.get("banners", [])
        }
        self.shop_items = {
            item["id"]: _shop_from_dict(item) for item in data.get("shop_items", [])
        }
        self.battle_pass_seasons = {
            item["id"]: _battle_pass_season_from_dict(item)
            for item in data.get("battle_pass_seasons", [])
        }
        self.ideas = {
            item["id"]: _idea_from_dict(item) for item in data.get("ideas", [])
        }
        self.standard_cards = list(data.get("standard_cards", []))
        self.universes = list(data.get("universes", self.universes))
        self.free_rewards = dict(data.get("free_rewards", {}))

    def save(self) -> None:
        """Persist catalog content to disk."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cards": [_card_to_dict(item) for item in self.cards.values()],
            "profile_backgrounds": [
                _profile_background_to_dict(item)
                for item in self.profile_backgrounds.values()
            ],
            "banners": [_banner_to_dict(item) for item in self.banners.values()],
            "shop_items": [_shop_to_dict(item) for item in self.shop_items.values()],
            "battle_pass_seasons": [
                _battle_pass_season_to_dict(item)
                for item in self.battle_pass_seasons.values()
            ],
            "ideas": [_idea_to_dict(item) for item in self.ideas.values()],
            "standard_cards": list(self.standard_cards),
            "universes": list(self.universes),
            "free_rewards": dict(self.free_rewards),
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def next_id(self, section: str) -> int:
        """Return the next numeric identifier for a catalog section."""

        items = {
            "cards": self.cards,
            "profile_backgrounds": self.profile_backgrounds,
            "banners": self.banners,
            "shop_items": self.shop_items,
            "battle_pass_seasons": self.battle_pass_seasons,
            "ideas": self.ideas,
        }[section]
        return max(items, default=0) + 1


class _CatalogRepository:
    """Shared repository mechanics for catalog sections."""

    section: str

    def __init__(self, store: CatalogStore | None = None) -> None:
        self.store = store
        self.items = {}

    def _load_from_store(self) -> None:
        if self.store is None:
            return
        self.items = dict(getattr(self.store, self.section))

    def _flush(self) -> None:
        if self.store is None:
            return
        getattr(self.store, self.section).clear()
        getattr(self.store, self.section).update(self.items)
        self.store.save()

    async def get_by_id(self, item_id):
        return self.items.get(item_id)

    async def add(self, item):
        self.items[item.id] = item
        self._flush()
        return item

    async def save(self, item):
        return await self.add(item)

    async def delete(self, item_id):
        self.items.pop(item_id, None)
        self._flush()


class LocalCardTemplateRepository(_CatalogRepository):
    """Card template storage backed by the local catalog."""

    section = "cards"

    def __init__(self, store: CatalogStore | None = None) -> None:
        super().__init__(store)
        self._load_from_store()

    async def list_active(self):
        return [item for item in self.items.values() if item.is_available]


class LocalProfileBackgroundRepository(_CatalogRepository):
    """Profile-background storage backed by the local catalog."""

    section = "profile_backgrounds"

    def __init__(self, store: CatalogStore | None = None) -> None:
        super().__init__(store)
        self._load_from_store()

    async def list_all(self):
        return list(self.items.values())


class LocalBannerRepository(_CatalogRepository):
    """Banner storage backed by the local catalog."""

    section = "banners"

    def __init__(self, store: CatalogStore | None = None) -> None:
        super().__init__(store)
        self._load_from_store()

    async def list_available(self):
        return [banner for banner in self.items.values() if banner.is_available()]


class LocalShopRepository(_CatalogRepository):
    """Shop storage backed by the local catalog."""

    section = "shop_items"

    def __init__(self, store: CatalogStore | None = None) -> None:
        super().__init__(store)
        self._load_from_store()

    async def list_active(self):
        return [item for item in self.items.values() if item.is_active]


class LocalBattlePassSeasonRepository(_CatalogRepository):
    """Battle pass season storage backed by the local catalog."""

    section = "battle_pass_seasons"

    def __init__(self, store: CatalogStore | None = None) -> None:
        super().__init__(store)
        self._load_from_store()

    async def list_active(self):
        return [season for season in self.items.values() if season.is_active]

    async def list_all(self):
        return list(self.items.values())


class LocalIdeaRepository(_CatalogRepository):
    """Idea storage backed by the local catalog."""

    section = "ideas"

    def __init__(self, store: CatalogStore | None = None) -> None:
        super().__init__(store)
        self._load_from_store()

    async def list_all(self):
        return list(self.items.values())
