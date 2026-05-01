"""Admin control keyboards."""

from src.telegram.callbacks import AdminCallback
from src.telegram.compat import InlineKeyboardMarkup
from src.telegram.ui.helpers import _choice_markup, _markup


def admin_markup(section: str = "dashboard") -> InlineKeyboardMarkup:
    """Return the admin dashboard keyboard."""

    if section == "cards":
        return _markup(
            [
                ("➕ Создать карту", AdminCallback(action="create_card")),
                ("🗑 Удалить карту", AdminCallback(action="delete_card")),
                ("🎁 Выдать игроку", AdminCallback(action="player_add_card")),
                ("↩️ Забрать у игрока", AdminCallback(action="player_remove_card")),
                (
                    "🖼 Фоны профиля",
                    AdminCallback(action="section", value="profile_backgrounds"),
                ),
                ("👥 Игроки", AdminCallback(action="section", value="players")),
                ("🌌 Вселенные", AdminCallback(action="section", value="universes")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2, 2, 2, 2),
        )
    if section == "profile_backgrounds":
        return _markup(
            [
                ("➕ Создать фон", AdminCallback(action="create_profile_background")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2,),
        )
    if section == "players":
        return _markup(
            [
                ("🪄 Creator Points", AdminCallback(action="players_creator_points")),
                ("✨ Титул", AdminCallback(action="players_title")),
                ("💎 Премиум", AdminCallback(action="players_premium_toggle")),
                ("🗑 Удалить игрока", AdminCallback(action="delete_player")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2, 2, 1),
        )
    if section == "banners":
        return _markup(
            [
                ("➕ Создать баннер", AdminCallback(action="create_banner")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2,),
        )
    if section == "shop":
        return _markup(
            [
                ("➕ Создать товар", AdminCallback(action="create_shop_item")),
                ("🗑 Удалить товар", AdminCallback(action="delete_shop_item")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2, 1),
        )
    if section == "standard_cards":
        return _markup(
            [
                ("➕ Добавить ID", AdminCallback(action="standard_add")),
                ("➖ Удалить ID", AdminCallback(action="standard_remove")),
                ("🗑 Очистить", AdminCallback(action="standard_clear")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2, 2),
        )
    if section == "universes":
        return _markup(
            [
                ("➕ Новая вселенная", AdminCallback(action="universe_add")),
                ("🗑 Удалить вселенную", AdminCallback(action="universe_remove")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2, 1),
        )
    if section == "battle_pass":
        return _markup(
            [
                (
                    "➕ Уровень Battle Pass",
                    AdminCallback(action="battle_pass_add_level"),
                ),
                (
                    "🆕 Новый сезон",
                    AdminCallback(action="battle_pass_create_season"),
                ),
                (
                    "🗑 Удалить сезон",
                    AdminCallback(action="battle_pass_delete_season"),
                ),
                (
                    "🎁 Фри-награды",
                    AdminCallback(action="section", value="free_rewards"),
                ),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (1, 1, 1, 1, 1),
        )
    if section == "premium_battle_pass":
        return _markup(
            [
                (
                    "➕ Уровень Premium Pass",
                    AdminCallback(action="premium_battle_pass_add_level"),
                ),
                (
                    "🆕 Новый премиум-сезон",
                    AdminCallback(action="premium_battle_pass_create_season"),
                ),
                (
                    "🗑 Удалить премиум-сезон",
                    AdminCallback(action="premium_battle_pass_delete_season"),
                ),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (1, 1, 1, 1),
        )
    if section == "free_rewards":
        return _markup(
            [
                ("🎴 Шансы карт", AdminCallback(action="free_rewards_card_weights")),
                (
                    "💰 Шансы ресурсов",
                    AdminCallback(action="free_rewards_resource_weights"),
                ),
                (
                    "📦 Значения ресурсов",
                    AdminCallback(action="free_rewards_resource_values"),
                ),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
            ],
            (2, 1, 1),
        )
    return _markup(
        [
            ("🎴 Карты", AdminCallback(action="section", value="cards")),
            ("🖼 Фоны", AdminCallback(action="section", value="profile_backgrounds")),
            ("👥 Игроки", AdminCallback(action="section", value="players")),
            ("💡 Идеи", AdminCallback(action="section", value="ideas_pending")),
            ("🎁 Баннеры", AdminCallback(action="section", value="banners")),
            ("🛒 Магазин", AdminCallback(action="section", value="shop")),
            (
                "🆓 Стартовые карты",
                AdminCallback(action="section", value="standard_cards"),
            ),
            ("🏁 Battle Pass", AdminCallback(action="section", value="battle_pass")),
            (
                "💎 Premium Pass",
                AdminCallback(action="section", value="premium_battle_pass"),
            ),
            ("🎁 Фри-награды", AdminCallback(action="section", value="free_rewards")),
            ("🌌 Вселенные", AdminCallback(action="section", value="universes")),
        ],
        (2, 2, 2, 2, 2, 1),
    )


def admin_wizard_markup(back_section: str = "dashboard") -> InlineKeyboardMarkup:
    """Return the wizard control keyboard."""

    return _markup(
        [
            ("🗑 Сбросить", AdminCallback(action="cancel")),
            ("⬅️ Назад", AdminCallback(action="section", value=back_section)),
        ],
        (2,),
    )


def admin_banner_markup(
    banner_id: int, editable: bool, allow_delete: bool = False
) -> InlineKeyboardMarkup:
    """Return a banner management keyboard."""

    buttons = []
    if editable:
        buttons.extend(
            [
                (
                    "➕ Добавить карту",
                    AdminCallback(action="banner_add_card", banner_id=banner_id),
                ),
                (
                    "➖ Удалить карту",
                    AdminCallback(action="banner_remove_card", banner_id=banner_id),
                ),
                (
                    "➕ Добавить фон",
                    AdminCallback(action="banner_add_background", banner_id=banner_id),
                ),
                (
                    "➖ Удалить фон",
                    AdminCallback(
                        action="banner_remove_background", banner_id=banner_id
                    ),
                ),
            ]
        )
    if editable or allow_delete:
        buttons.append(
            (
                "🗑 Удалить баннер",
                AdminCallback(action="delete_banner", banner_id=banner_id),
            )
        )
    if editable:
        sizes = (2, 2, 1)
    elif allow_delete:
        sizes = (1,)
    else:
        sizes = (1,)
    return _markup(buttons, sizes)


def admin_choice_markup(
    action: str, items: list[tuple[str, str]], back_section: str = "dashboard"
) -> InlineKeyboardMarkup:
    """Return a keyboard with choice buttons."""

    return _choice_markup(action, items, back_section)


__all__ = [
    "admin_banner_markup",
    "admin_choice_markup",
    "admin_markup",
    "admin_wizard_markup",
]
