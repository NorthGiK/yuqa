"""Router compatibility surface and builder for the Telegram bot."""

from yuqa.telegram.compat import Router
from yuqa.telegram.router_admin import register_admin_handlers
from yuqa.telegram.router_battle import cancel_battle_search, search_battle, start_battle
from yuqa.telegram.router_helpers import _parse_effects
from yuqa.telegram.router_public import register_public_handlers
from yuqa.telegram.router_views import (
    show_admin,
    show_battle,
    show_card_detail,
    show_cards,
    show_deck_builder,
    show_free_rewards,
    show_gallery,
    show_idea_collection,
    show_idea_detail,
    show_ideas,
    show_premium_battle_pass,
    show_profile,
    show_tops,
)
from yuqa.telegram.router_wizards_banners import (
    banner_end_at,
    banner_name,
    banner_start_at,
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
    capture_universe_add,
    capture_universe_remove,
    profile_background_media,
    start_card_create,
    start_universe_create,
    start_universe_delete,
)
from yuqa.telegram.router_wizards_shop import shop_price, shop_quantity
from yuqa.telegram.router_wizards_players import (
    capture_admin_player_delete,
    capture_admin_player_id,
    capture_admin_player_value,
    capture_clan_icon,
    capture_clan_name,
    capture_idea_description,
    capture_idea_title,
    capture_profile_nickname,
    start_admin_player_delete,
    start_admin_player_edit,
    start_clan_creation,
    start_idea_proposal,
    start_profile_nickname_edit,
)
from yuqa.telegram.router_wizards_progression import (
    capture_battle_pass_level_number,
    capture_battle_pass_required_points,
    capture_battle_pass_reward,
    capture_battle_pass_season_delete,
    capture_free_rewards_edit,
    start_battle_pass_level_create,
    start_free_rewards_edit,
)


def build_router(services, settings) -> Router:
    """Build a router that closes over the runtime dependencies."""

    router = Router(name="yuqa")
    register_public_handlers(router, services, settings)
    register_admin_handlers(router, services, settings)
    return router


__all__ = [
    "_parse_effects",
    "banner_end_at",
    "banner_name",
    "banner_start_at",
    "build_router",
    "cancel_battle_search",
    "card_ability_cooldown",
    "card_ability_cost",
    "card_ability_effects",
    "card_ascended_effects",
    "card_ascended_stats",
    "card_base_stats",
    "card_image",
    "card_name",
    "capture_admin_player_delete",
    "capture_admin_player_id",
    "capture_admin_player_value",
    "capture_battle_pass_level_number",
    "capture_battle_pass_required_points",
    "capture_battle_pass_reward",
    "capture_battle_pass_season_delete",
    "capture_clan_icon",
    "capture_clan_name",
    "capture_free_rewards_edit",
    "capture_idea_description",
    "capture_idea_title",
    "capture_profile_nickname",
    "capture_universe_add",
    "capture_universe_remove",
    "profile_background_media",
    "search_battle",
    "shop_price",
    "shop_quantity",
    "show_admin",
    "show_battle",
    "show_card_detail",
    "show_cards",
    "show_deck_builder",
    "show_free_rewards",
    "show_gallery",
    "show_idea_collection",
    "show_idea_detail",
    "show_ideas",
    "show_premium_battle_pass",
    "show_profile",
    "show_tops",
    "start_admin_player_delete",
    "start_admin_player_edit",
    "start_battle",
    "start_battle_pass_level_create",
    "start_card_create",
    "start_clan_creation",
    "start_free_rewards_edit",
    "start_idea_proposal",
    "start_profile_nickname_edit",
    "start_universe_create",
    "start_universe_delete",
]
