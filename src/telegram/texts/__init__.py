"""Stable compatibility layer for Telegram screen text renderers."""

from src.telegram.texts.admin import (
    admin_text,
    banner_wizard_text,
    profile_background_wizard_text,
    shop_wizard_text,
)
from src.telegram.texts.battle import (
    _battle_card_line,
    battle_started_text,
    battle_result_text,
    battle_status_text,
    battle_text,
)
from src.telegram.texts.battle_pass import (
    battle_pass_admin_text,
    battle_pass_level_wizard_text,
    battle_pass_season_wizard_text,
    battle_pass_seasons_text,
    battle_pass_text,
    premium_battle_pass_admin_text,
    premium_battle_pass_seasons_text,
    premium_battle_pass_text,
)
from src.telegram.texts.cards import (
    ability_effects_guide,
    admin_cards_text,
    card_level_up_confirm_text,
    card_template_text,
    card_text,
    cards_text,
    card_wizard_text,
    deck_builder_text,
    gallery_text,
    image_input_guide,
    standard_cards_text,
    universes_text,
)
from src.telegram.texts.catalog import (
    banner_pool_text,
    banner_text,
    clan_text,
    shop_text,
)
from src.telegram.texts.ideas import idea_text, ideas_text, idea_wizard_text
from src.telegram.texts.navigation import collection_text, menu_text
from src.telegram.texts.profile import (
    admin_profile_backgrounds_text,
    profile_background_text,
    profile_backgrounds_text,
    profile_text,
    tops_text,
)
from src.telegram.texts.rewards import (
    free_rewards_admin_text,
    free_rewards_edit_guide,
    free_rewards_text,
)
from src.telegram.texts.shared import (
    _background_label,
    _cooldown_line,
    _idea_status_label,
    _player_name,
    _stats,
    _wallet,
)


__all__ = [
    "_background_label",
    "_battle_card_line",
    "_cooldown_line",
    "_idea_status_label",
    "_player_name",
    "_stats",
    "_wallet",
    "ability_effects_guide",
    "admin_cards_text",
    "admin_profile_backgrounds_text",
    "admin_text",
    "banner_pool_text",
    "banner_text",
    "banner_wizard_text",
    "battle_pass_admin_text",
    "battle_pass_level_wizard_text",
    "battle_pass_season_wizard_text",
    "battle_pass_seasons_text",
    "battle_pass_text",
    "battle_started_text",
    "battle_result_text",
    "battle_status_text",
    "battle_text",
    "card_level_up_confirm_text",
    "card_template_text",
    "card_text",
    "cards_text",
    "card_wizard_text",
    "clan_text",
    "collection_text",
    "deck_builder_text",
    "free_rewards_admin_text",
    "free_rewards_edit_guide",
    "free_rewards_text",
    "gallery_text",
    "idea_text",
    "ideas_text",
    "idea_wizard_text",
    "image_input_guide",
    "menu_text",
    "premium_battle_pass_admin_text",
    "premium_battle_pass_seasons_text",
    "premium_battle_pass_text",
    "profile_background_text",
    "profile_background_wizard_text",
    "profile_backgrounds_text",
    "profile_text",
    "shop_text",
    "shop_wizard_text",
    "standard_cards_text",
    "tops_text",
    "universes_text",
]
