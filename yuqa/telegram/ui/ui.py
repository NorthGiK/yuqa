"""Stable compatibility layer for Telegram keyboard builders."""

from yuqa.telegram.ui.ui_admin import (
    admin_banner_markup,
    admin_choice_markup,
    admin_markup,
    admin_wizard_markup,
)
from yuqa.telegram.ui.ui_battle import (
    battle_actions_markup,
    battle_markup,
    battle_switch_markup,
)
from yuqa.telegram.ui.ui_cards import (
    _CARD_PAGE_SIZE,
    card_level_up_confirm_markup,
    card_markup,
    cards_markup,
    deck_builder_markup,
    gallery_markup,
)
from yuqa.telegram.ui.ui_catalog import banner_markup, shop_markup
from yuqa.telegram.ui.ui_helpers import _choice_markup, _markup, _reply_markup
from yuqa.telegram.ui.ui_ideas import (
    admin_idea_detail_markup,
    admin_ideas_markup,
    idea_detail_markup,
    ideas_markup,
)
from yuqa.telegram.ui.ui_navigation import (
    COLLECTION_MENU_BUTTON,
    MAIN_MENU_BUTTON_ROWS,
    MAIN_MENU_BUTTON_TEXTS,
    _PREMIUM_MENU_BUTTON,
    collection_markup,
    main_menu_markup,
)
from yuqa.telegram.ui.ui_profile import (
    clan_markup,
    profile_background_markup,
    profile_backgrounds_markup,
    profile_markup,
    tops_markup,
)
from yuqa.telegram.ui.ui_rewards import (
    battle_pass_markup,
    free_rewards_markup,
    premium_battle_pass_markup,
)


__all__ = [
    "_CARD_PAGE_SIZE",
    "_PREMIUM_MENU_BUTTON",
    "_choice_markup",
    "_markup",
    "_reply_markup",
    "COLLECTION_MENU_BUTTON",
    "MAIN_MENU_BUTTON_ROWS",
    "MAIN_MENU_BUTTON_TEXTS",
    "admin_banner_markup",
    "admin_choice_markup",
    "admin_idea_detail_markup",
    "admin_ideas_markup",
    "admin_markup",
    "admin_wizard_markup",
    "banner_markup",
    "battle_actions_markup",
    "battle_markup",
    "battle_pass_markup",
    "battle_switch_markup",
    "card_level_up_confirm_markup",
    "card_markup",
    "cards_markup",
    "clan_markup",
    "collection_markup",
    "deck_builder_markup",
    "free_rewards_markup",
    "gallery_markup",
    "idea_detail_markup",
    "ideas_markup",
    "main_menu_markup",
    "premium_battle_pass_markup",
    "profile_background_markup",
    "profile_backgrounds_markup",
    "profile_markup",
    "shop_markup",
    "tops_markup",
]
