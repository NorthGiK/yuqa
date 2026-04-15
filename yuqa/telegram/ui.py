"""Keyboard builders for the Telegram UI."""

from yuqa.cards.domain.entities import PlayerCard
from yuqa.ideas.domain.entities import Idea
from yuqa.shared.enums import IdeaStatus
from yuqa.telegram.callbacks import (
    AdminCallback,
    BannerCallback,
    BattleCallback,
    BattleQueueCallback,
    BattlePassCallback,
    PremiumBattlePassCallback,
    CardCallback,
    ClanCallback,
    DeckCallback,
    FreeRewardCallback,
    IdeaCallback,
    MenuCallback,
    ProfileCallback,
    ShopCallback,
    TopCallback,
)
from yuqa.telegram.compat import (
    InlineKeyboardBuilder,
    InlineKeyboardMarkup,
    ReplyKeyboardBuilder,
    ReplyKeyboardMarkup,
)

_CARD_PAGE_SIZE = 10
_PREMIUM_MENU_BUTTON = "💎 Premium Battle Pass"
COLLECTION_MENU_BUTTON = "🐦‍🔥 Коллекция"
MAIN_MENU_BUTTON_ROWS: tuple[tuple[str, ...], ...] = (
    ("👤 Профиль", COLLECTION_MENU_BUTTON),
    ("📖 Галерея", "💡 Идеи"),
    ("🏆 Топы", "⚔️ Бой"),
    ("🛒 Магазин", "🎁 Баннеры"),
    ("🏁 Battle Pass", "🏰 Клан"),
)
MAIN_MENU_BUTTON_TEXTS = {text for row in MAIN_MENU_BUTTON_ROWS for text in row} | {
    _PREMIUM_MENU_BUTTON,
    "🛠 Админка",
}


def _markup(buttons, sizes):
    """Build a markup from a list of button specs."""

    builder = InlineKeyboardBuilder()
    if not buttons:
        return builder.as_markup()
    for text, payload in buttons:
        builder.button(text=text, callback_data=payload)
    builder.adjust(*sizes)
    return builder.as_markup()


def _reply_markup(rows: tuple[tuple[str, ...], ...]) -> ReplyKeyboardMarkup:
    """Build a reply keyboard from button rows."""

    builder = ReplyKeyboardBuilder()
    for row in rows:
        for text in row:
            builder.button(text=text)
    builder.adjust(*(len(row) for row in rows))
    return builder.as_markup(resize_keyboard=True)


def _choice_markup(
    action: str, items: list[tuple[str, str]], back_value: str = "dashboard"
):
    """Build a small choice keyboard."""

    buttons = [
        (text, AdminCallback(action=action, value=value)) for text, value in items
    ]
    buttons.append(("⬅️ Назад", AdminCallback(action="section", value=back_value)))
    return _markup(buttons, (2, 2, 2))


def main_menu_markup(
    *, is_admin: bool = False, is_premium: bool = False
) -> ReplyKeyboardMarkup:
    """Return the main navigation keyboard."""

    rows = list(MAIN_MENU_BUTTON_ROWS)
    if is_premium:
        rows.insert(5, (_PREMIUM_MENU_BUTTON,))
    if is_admin:
        rows.append(("🛠 Админка",))
    return _reply_markup(tuple(rows))


def battle_markup(searching: bool = False) -> InlineKeyboardMarkup:
    """Return the battle screen keyboard."""

    button = "⏳ Отменить поиск" if searching else "🔍 Поиск соперника"
    action = "cancel_search" if searching else "search"
    return _markup(
        [
            (button, BattleQueueCallback(action=action)),
            ("🧱 Конструктор колоды", MenuCallback(section="deck")),
        ],
        (1, 1),
    )


def battle_actions_markup(
    *, can_switch: bool, ability_cost: int, can_use_ability: bool = True
) -> InlineKeyboardMarkup:
    """Return the battle round action keyboard."""

    buttons = [
        ("⚔️Атака", BattleCallback(action="attack")),
        ("🛡️Блок", BattleCallback(action="block")),
        ("🌟Бонус", BattleCallback(action="bonus")),
    ]
    if can_switch:
        buttons.append(("🦹‍♂️Сменить карту", BattleCallback(action="switch")))
    if can_use_ability:
        buttons.append(
            (f"🔥Способность {ability_cost}", BattleCallback(action="ability"))
        )
    if len(buttons) == 1:
        sizes = (1,)
    elif len(buttons) == 2:
        sizes = (2,)
    elif len(buttons) == 3:
        sizes = (2, 1)
    elif len(buttons) == 4:
        sizes = (2, 2)
    else:
        sizes = (2, 2, 1)
    return _markup(buttons, sizes)


def battle_switch_markup(
    cards: list[tuple[int, str]], *, back_action: str = "back"
) -> InlineKeyboardMarkup:
    """Return the card picker for a battle switch action."""

    buttons = [
        (label, BattleCallback(action="switch_choose", card_id=card_id))
        for card_id, label in cards
    ]
    buttons.append(("⬅️ Назад", BattleCallback(action=back_action)))
    return _markup(buttons, (1,) * len(buttons))


def cards_markup(
    cards: list[PlayerCard],
    page: int = 1,
    *,
    has_prev: bool = False,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    """Return the card list keyboard."""

    buttons = [
        (
            f"🎴 Карта #{card.id}",
            CardCallback(action="open", card_id=card.id, page=page, scope="collection"),
        )
        for card in cards
    ]
    if has_prev:
        buttons.append(
            ("⬅️", CardCallback(action="page", page=page - 1, scope="collection"))
        )
    if has_next:
        buttons.append(
            ("➡️", CardCallback(action="page", page=page + 1, scope="collection"))
        )
    sizes = [1] * len(cards)
    if has_prev or has_next:
        sizes.append(2 if has_prev and has_next else 1)
    return _markup(buttons, tuple(sizes))


def gallery_markup(
    templates,
    page: int = 1,
    *,
    has_prev: bool = False,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    """Return the public card gallery keyboard."""

    buttons = [
        (
            f"✨ {template.name}",
            CardCallback(
                action="template_open",
                card_id=template.id,
                page=page,
                scope="gallery",
            ),
        )
        for template in templates
    ]
    if has_prev:
        buttons.append(
            ("⬅️", CardCallback(action="page", page=page - 1, scope="gallery"))
        )
    if has_next:
        buttons.append(
            ("➡️", CardCallback(action="page", page=page + 1, scope="gallery"))
        )
    sizes = [1] * len(templates)
    if has_prev or has_next:
        sizes.append(2 if has_prev and has_next else 1)
    return _markup(buttons, tuple(sizes))


def card_markup(
    card_id: int,
    can_level_up: bool,
    can_ascend: bool,
    is_ascended: bool,
    *,
    page: int = 1,
    scope: str = "collection",
) -> InlineKeyboardMarkup:
    """Return a keyboard for a card detail screen."""

    buttons = []
    if can_level_up:
        buttons.append(("⬆️ Улучшить", CardCallback(action="level_up", card_id=card_id)))
    if can_ascend:
        buttons.append(("🔥 Возвысить", CardCallback(action="ascend", card_id=card_id)))
    if is_ascended:
        buttons.append(
            ("🔁 Сменить форму", CardCallback(action="toggle_form", card_id=card_id))
        )
    buttons.append(
        (
            "⬅️ В коллекцию" if scope == "collection" else "⬅️ В галерею",
            CardCallback(action="page", card_id=card_id, page=page, scope=scope),
        )
    )
    return _markup(buttons, (2, 1))


def card_level_up_confirm_markup(
    card_id: int, *, page: int = 1, scope: str = "collection"
) -> InlineKeyboardMarkup:
    """Return confirmation controls for a card level-up."""

    return _markup(
        [
            (
                "✅ Подтвердить",
                CardCallback(action="confirm_level_up", card_id=card_id),
            ),
            (
                "⬅️ Назад",
                CardCallback(action="open", card_id=card_id, page=page, scope=scope),
            ),
        ],
        (1, 1),
    )


def clan_markup(has_clan: bool) -> InlineKeyboardMarkup:
    """Return the clan screen keyboard."""

    return _markup(
        [
            (
                "🚪 Покинуть клан" if has_clan else "➕ Создать клан",
                ClanCallback(action="leave" if has_clan else "create"),
            ),
        ],
        (1,),
    )


def profile_markup(
    *,
    is_owner: bool,
    has_nickname: bool,
) -> InlineKeyboardMarkup:
    """Return the profile screen keyboard."""

    buttons = []
    if is_owner:
        buttons.append(("✏️ Никнейм", ProfileCallback(action="edit_nickname")))
        buttons.append(("🖼️ Фоны профиля", MenuCallback(section="profile_backgrounds")))
        if has_nickname:
            buttons.append(
                ("🧹 Сбросить ник", ProfileCallback(action="clear_nickname"))
            )
    if not buttons:
        return _markup(buttons, ())
    return _markup(buttons, (2, 1) if is_owner and has_nickname else (2,))


def collection_markup() -> InlineKeyboardMarkup:
    """Return the collection hub keyboard."""

    return _markup(
        [
            ("🎴 Мои Карты", MenuCallback(section="cards")),
            ("💡 Мои идеи", MenuCallback(section="idea_collection")),
        ],
        (1, 1),
    )


def shop_markup(item_ids: list[int]) -> InlineKeyboardMarkup:
    """Return the shop catalog keyboard."""

    buttons = [
        (f"🛒 Купить #{item_id}", ShopCallback(action="buy", item_id=item_id))
        for item_id in item_ids
    ]
    buttons.append(("🎁 Бесплатно", MenuCallback(section="free_rewards")))
    sizes = [2] * (len(item_ids) // 2)
    if len(item_ids) % 2:
        sizes.append(1)
    sizes.append(1)
    return _markup(buttons, tuple(sizes))


def banner_markup(banner_id: int) -> InlineKeyboardMarkup:
    """Return the banner detail keyboard."""

    return _markup(
        [
            (
                "🎲 Крутка x1",
                BannerCallback(action="pull", banner_id=banner_id, count=1),
            ),
            (
                "✨ Крутка x10",
                BannerCallback(action="pull", banner_id=banner_id, count=10),
            ),
        ],
        (2,),
    )


def battle_pass_markup(*, can_buy_level: bool = False) -> InlineKeyboardMarkup:
    """Return a minimal battle pass keyboard."""

    buttons = []
    if can_buy_level:
        buttons.append(
            ("💰 Купить уровень за 250", BattlePassCallback(action="buy_level"))
        )
    return _markup(buttons, (1, 1) if can_buy_level else (1,))


def premium_battle_pass_markup(*, can_buy_level: bool = False) -> InlineKeyboardMarkup:
    """Return a minimal premium battle pass keyboard."""

    buttons = []
    if can_buy_level:
        buttons.append(
            ("💰 Купить уровень за 250", PremiumBattlePassCallback(action="buy_level"))
        )
    return _markup(buttons, (1, 1) if can_buy_level else (1,))


def tops_markup(current_mode: str) -> InlineKeyboardMarkup:
    """Return the users-top keyboard."""

    icons = {
        "rating": "🏆",
        "badenko_cards": "🃏",
        "creator_points": "🪄",
    }
    labels = {
        "rating": "Рейтинг",
        "badenko_cards": "Badenko",
        "creator_points": "Creator Points",
    }
    buttons = [
        (
            f"{icons[mode]} {'• ' if mode == current_mode else ''}{labels[mode]}",
            TopCallback(mode=mode),
        )
        for mode in ("rating", "badenko_cards", "creator_points")
    ]
    return _markup(buttons, (1, 1, 1))


def profile_backgrounds_markup(background_ids: list[int]) -> InlineKeyboardMarkup:
    """Return the owned profile-background collection keyboard."""

    buttons = [
        (
            f"🖼 Фон #{background_id}",
            ProfileCallback(action="open_background", background_id=background_id),
        )
        for background_id in background_ids
    ]
    buttons.append(("🧹 Снять фон", ProfileCallback(action="clear_background")))
    return _markup(buttons, (2, 2, 1))


def profile_background_markup(
    background_id: int, *, selected: bool
) -> InlineKeyboardMarkup:
    """Return one profile-background detail keyboard."""

    buttons = []
    if not selected:
        buttons.append(
            (
                "✅ Установить",
                ProfileCallback(action="set_background", background_id=background_id),
            )
        )
    return _markup(buttons, (1, 1))


def free_rewards_markup() -> InlineKeyboardMarkup:
    """Return the free rewards screen keyboard."""

    return _markup(
        [
            ("🎴 Забрать карту", FreeRewardCallback(action="claim_card")),
            ("💰 Забрать ресурсы", FreeRewardCallback(action="claim_resources")),
        ],
        (1, 1),
    )


def ideas_markup(
    ideas: list[Idea],
    page: int,
    *,
    has_prev: bool,
    has_next: bool,
    collection: bool = False,
) -> InlineKeyboardMarkup:
    """Return the public ideas or collection keyboard."""

    scope = "collection" if collection else "published"
    buttons = [
        (
            f"💡 {idea.title[:24]}{'…' if len(idea.title) > 24 else ''} · 👍 {idea.upvotes}",
            IdeaCallback(action="open", idea_id=idea.id, page=page, scope=scope),
        )
        for idea in ideas
    ]
    nav = []
    if has_prev:
        nav.append(("⬅️", IdeaCallback(action="page", page=page - 1, scope=scope)))
    if has_next:
        nav.append(("➡️", IdeaCallback(action="page", page=page + 1, scope=scope)))
    buttons.extend(nav)
    if not collection:
        buttons.append(
            ("➕ Предложить идею", IdeaCallback(action="propose", page=page))
        )
    sizes = [1] * len(ideas)
    if nav:
        sizes.append(len(nav))
    if not collection:
        sizes.append(1)
    return _markup(buttons, tuple(sizes))


def idea_detail_markup(
    idea_id: int,
    page: int,
    *,
    scope: str,
    can_vote: bool,
) -> InlineKeyboardMarkup:
    """Return the public idea detail keyboard."""

    buttons = []
    if can_vote:
        buttons.extend(
            [
                (
                    "👍 За",
                    IdeaCallback(
                        action="vote_up",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
                (
                    "👎 Против",
                    IdeaCallback(
                        action="vote_down",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
            ]
        )
    return _markup(buttons, (2,) if can_vote else ())


def admin_ideas_markup(
    ideas: list[Idea],
    page: int,
    *,
    scope: str,
    has_prev: bool,
    has_next: bool,
) -> InlineKeyboardMarkup:
    """Return the admin ideas browser keyboard."""

    buttons = [
        (
            f"💡 {idea.title[:22]}{'…' if len(idea.title) > 22 else ''} · 👍 {idea.upvotes}",
            IdeaCallback(action="open", idea_id=idea.id, page=page, scope=scope),
        )
        for idea in ideas
    ]
    buttons.extend(
        [
            ("🆕 Модерация", IdeaCallback(action="admin_list", scope="admin_pending")),
            ("📣 Паблик", IdeaCallback(action="admin_list", scope="admin_public")),
            (
                "📚 Коллекция",
                IdeaCallback(action="admin_list", scope="admin_collection"),
            ),
            (
                "🗑 Архив",
                IdeaCallback(action="admin_list", scope="admin_rejected"),
            ),
        ]
    )
    nav = []
    if has_prev:
        nav.append(("⬅️", IdeaCallback(action="admin_list", page=page - 1, scope=scope)))
    if has_next:
        nav.append(("➡️", IdeaCallback(action="admin_list", page=page + 1, scope=scope)))
    buttons.extend(nav)
    buttons.append(("🏠 Панель", AdminCallback(action="section", value="dashboard")))
    buttons.append(("⬅️ В меню", MenuCallback(section="home")))
    sizes = [1] * len(ideas)
    sizes.extend((2, 2))
    if nav:
        sizes.append(len(nav))
    sizes.extend((1, 1))
    return _markup(buttons, tuple(sizes))


def admin_idea_detail_markup(
    idea_id: int,
    page: int,
    *,
    scope: str,
    status: IdeaStatus,
) -> InlineKeyboardMarkup:
    """Return the admin idea detail keyboard."""

    buttons = []
    if status == IdeaStatus.PENDING:
        buttons.extend(
            [
                (
                    "✅ На страницу идей",
                    IdeaCallback(
                        action="admin_publish",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
                (
                    "🗑 Отклонить",
                    IdeaCallback(
                        action="admin_reject",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
            ]
        )
    elif status == IdeaStatus.PUBLISHED:
        buttons.extend(
            [
                (
                    "📚 В коллекцию",
                    IdeaCallback(
                        action="admin_collect",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
                (
                    "🗑 Отклонить",
                    IdeaCallback(
                        action="admin_reject",
                        idea_id=idea_id,
                        page=page,
                        scope=scope,
                    ),
                ),
            ]
        )
    buttons.append(
        ("⬅️ К списку", IdeaCallback(action="admin_list", page=page, scope=scope))
    )
    return _markup(buttons, (2, 1) if len(buttons) > 1 else (1,))


def deck_builder_markup(
    cards: list[PlayerCard], selected_ids: list[int]
) -> InlineKeyboardMarkup:
    """Return deck-constructor keyboard."""

    selected = set(selected_ids)
    card_buttons = [
        (
            f"{'✅' if card.id in selected else '▫️'} #{card.id}",
            DeckCallback(action="toggle", card_id=card.id),
        )
        for card in cards
    ]
    controls = [
        ("💾 Сохранить", DeckCallback(action="save", card_id=0)),
        ("🧹 Очистить", DeckCallback(action="clear", card_id=0)),
    ]
    buttons = card_buttons + controls
    card_rows = [2] * ((len(card_buttons) + 1) // 2)
    return _markup(buttons, tuple(card_rows + [2]))


def admin_markup(section: str = "dashboard") -> InlineKeyboardMarkup:
    """Return the admin dashboard keyboard."""

    if section == "cards":
        return _markup(
            [
                ("➕ Создать карту", AdminCallback(action="create_card")),
                ("🗑 Удалить карту", AdminCallback(action="delete_card")),
                (
                    "🖼 Фоны профиля",
                    AdminCallback(action="section", value="profile_backgrounds"),
                ),
                ("👥 Игроки", AdminCallback(action="section", value="players")),
                ("🌌 Вселенные", AdminCallback(action="section", value="universes")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 2, 2),
        )
    if section == "profile_backgrounds":
        return _markup(
            [
                ("➕ Создать фон", AdminCallback(action="create_profile_background")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 1),
        )
    if section == "players":
        return _markup(
            [
                ("🪄 Creator Points", AdminCallback(action="players_creator_points")),
                ("✨ Титул", AdminCallback(action="players_title")),
                ("💎 Премиум", AdminCallback(action="players_premium_toggle")),
                ("🗑 Удалить игрока", AdminCallback(action="delete_player")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 2, 2),
        )
    if section == "banners":
        return _markup(
            [
                ("➕ Создать баннер", AdminCallback(action="create_banner")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 1),
        )
    if section == "shop":
        return _markup(
            [
                ("➕ Создать товар", AdminCallback(action="create_shop_item")),
                ("🗑 Удалить товар", AdminCallback(action="delete_shop_item")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 2),
        )
    if section == "standard_cards":
        return _markup(
            [
                ("➕ Добавить ID", AdminCallback(action="standard_add")),
                ("➖ Удалить ID", AdminCallback(action="standard_remove")),
                ("🗑 Очистить", AdminCallback(action="standard_clear")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 2, 1),
        )
    if section == "universes":
        return _markup(
            [
                ("➕ Новая вселенная", AdminCallback(action="universe_add")),
                ("🗑 Удалить вселенную", AdminCallback(action="universe_remove")),
                ("🏠 Панель", AdminCallback(action="section", value="dashboard")),
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 2),
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
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (1, 1, 1, 2),
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
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (1, 1, 1, 2),
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
                ("⬅️ Назад", MenuCallback(section="home")),
            ],
            (2, 1, 2),
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
            ("⬅️ Назад", MenuCallback(section="home")),
        ],
        (2, 2, 2, 2, 2, 2),
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


def admin_banner_markup(banner_id: int, editable: bool) -> InlineKeyboardMarkup:
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
                (
                    "🗑 Удалить баннер",
                    AdminCallback(action="delete_banner", banner_id=banner_id),
                ),
            ]
        )
    buttons.append(("⬅️ К баннерам", AdminCallback(action="section", value="banners")))
    return _markup(buttons, (2, 2, 1, 1))


def admin_choice_markup(
    action: str, items: list[tuple[str, str]], back_section: str = "dashboard"
) -> InlineKeyboardMarkup:
    """Return a keyboard with choice buttons."""

    return _choice_markup(action, items, back_section)
