"""Card, gallery, and deck-builder keyboards."""

from yuqa.cards.domain.entities import PlayerCard
from yuqa.telegram.callbacks import CardCallback, DeckCallback
from yuqa.telegram.compat import InlineKeyboardMarkup
from yuqa.telegram.ui.ui_helpers import _markup


_CARD_PAGE_SIZE = 10


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
    return _markup(buttons, (2, 1) if len(buttons) > 2 else (1,))


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
        ],
        (1,),
    )


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


__all__ = [
    "_CARD_PAGE_SIZE",
    "card_level_up_confirm_markup",
    "card_markup",
    "cards_markup",
    "deck_builder_markup",
    "gallery_markup",
]
