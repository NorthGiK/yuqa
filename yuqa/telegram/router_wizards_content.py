"""Compatibility facade for content-admin wizard families."""

from yuqa.telegram.router_wizards_banners import (
    _banner_reward_finish,
    banner_end_at,
    banner_name,
    banner_start_at,
    start_banner_create,
)
from yuqa.telegram.router_wizards_cards import (
    card_ability_cooldown,
    card_ability_cost,
    card_ability_effects,
    card_ascended_effects,
    card_ascended_stats,
    card_base_stats,
    card_image,
    card_name,
    card_universe_value,
    capture_universe_add,
    capture_universe_remove,
    profile_background_media,
    standard_cards_add,
    standard_cards_remove,
    start_card_create,
    start_profile_background_create,
    start_universe_create,
    start_universe_delete,
)
from yuqa.telegram.router_wizards_shop import (
    shop_price,
    shop_quantity,
    start_shop_create,
)


__all__ = [
    "_banner_reward_finish",
    "banner_end_at",
    "banner_name",
    "banner_start_at",
    "card_ability_cooldown",
    "card_ability_cost",
    "card_ability_effects",
    "card_ascended_effects",
    "card_ascended_stats",
    "card_base_stats",
    "card_image",
    "card_name",
    "card_universe_value",
    "capture_universe_add",
    "capture_universe_remove",
    "profile_background_media",
    "shop_price",
    "shop_quantity",
    "standard_cards_add",
    "standard_cards_remove",
    "start_banner_create",
    "start_card_create",
    "start_profile_background_create",
    "start_shop_create",
    "start_universe_create",
    "start_universe_delete",
]
