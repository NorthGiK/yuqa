"""Finite-state-machine states for Telegram flows."""

from yuqa.telegram.compat import State, StatesGroup


class ClanCreation(StatesGroup):
    """Collect clan data before creation."""

    name = State()
    icon = State()


class CardCreate(StatesGroup):
    """Collect card template data step by step."""

    name = State()
    universe = State()
    universe_value = State()
    rarity = State()
    image = State()
    card_class = State()
    base_stats = State()
    ascended_stats = State()
    ability_cost = State()
    ability_cooldown = State()
    ability_effects = State()
    ascended_effects = State()


class CardDelete(StatesGroup):
    """Collect a card template id for deletion."""

    item_id = State()


class BannerCreate(StatesGroup):
    """Collect banner data step by step."""

    name = State()
    banner_type = State()
    cost_resource = State()
    start_at = State()
    end_at = State()


class BannerRewardCreate(StatesGroup):
    """Collect banner reward data step by step."""

    template_id = State()
    weight = State()
    guaranteed = State()


class ShopCreate(StatesGroup):
    """Collect shop item data step by step."""

    sell_resource = State()
    buy_resource = State()
    price = State()
    quantity = State()
    active = State()


class StandardCardsEdit(StatesGroup):
    """Edit the starter-card list step by step."""

    value = State()


class UniverseCreate(StatesGroup):
    """Create a new universe name."""

    value = State()


class UniverseDelete(StatesGroup):
    """Delete an existing universe name."""

    value = State()


class ShopDelete(StatesGroup):
    """Collect the shop item id to delete."""

    item_id = State()


class BattlePassLevelCreate(StatesGroup):
    """Collect battle pass level data step by step."""

    level_number = State()
    required_points = State()
    reward = State()


class BattlePassSeasonCreate(StatesGroup):
    """Collect battle pass season data step by step."""

    name = State()
    start_at = State()
    end_at = State()


class BattlePassSeasonDelete(StatesGroup):
    """Collect a battle pass season id for deletion."""

    season_id = State()


class FreeRewardsEdit(StatesGroup):
    """Edit free reward configuration values."""

    value = State()


class ProfileEdit(StatesGroup):
    """Edit the player's profile cosmetics."""

    nickname = State()


class IdeaProposal(StatesGroup):
    """Collect a new mechanic idea from a player."""

    title = State()
    description = State()


class AdminPlayerEdit(StatesGroup):
    """Edit another player's cosmetics from the admin panel."""

    player_id = State()
    value = State()


class ProfileBackgroundCreate(StatesGroup):
    """Create a profile background step by step."""

    rarity = State()
    media = State()
