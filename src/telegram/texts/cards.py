"""Card, gallery, deck, and card-admin text renderers."""

from src.cards.domain.entities import CardTemplate, PlayerCard
from src.players.domain.entities import Player
from src.telegram.texts.shared import _stats


def cards_text(
    cards: list[PlayerCard],
    templates: dict[int, CardTemplate],
    page: int = 1,
    *,
    total_pages: int | None = None,
) -> str:
    """Build the owned card collection screen."""

    if not cards:
        return "🎴 <b>Коллекция</b>\n<i>Пока пусто. Но это легко исправить баннерами и боями!</i>"
    lines = ["🎴 <b>Коллекция</b>"]
    if total_pages is not None:
        lines.extend([f"📄 <b>Страница:</b> <code>{page}/{total_pages}</code>", ""])
    for card in cards:
        template = templates.get(card.template_id)
        name = template.name if template else f"Шаблон #{card.template_id}"
        lines.append(
            f"• <b>{name}</b> — <code>{card.id}</code>, lvl <code>{card.level}</code>, копии <code>{card.copies_owned}</code>"
        )
    return "\n".join(lines)


def card_level_up_confirm_text(
    player: Player,
    card: PlayerCard,
    template: CardTemplate,
    coins_cost: int,
    orbs_cost: int = 0,
) -> str:
    """Build a level-up confirmation screen for one card."""

    return "\n".join(
        [
            "⬆️ <b>Подтверждение улучшения</b>",
            f"🎴 <b>Карта:</b> {template.name} <code>#{card.id}</code>",
            f"⭐ <b>Уровень:</b> <code>{card.level} → {card.level + 1}</code>",
            "",
            f"🪙 <b>Монеты:</b> <code>{player.wallet.coins}</code> / <code>{coins_cost}</code>",
            f"🔮 <b>Орбы:</b> <code>{player.wallet.orbs}</code> / <code>{orbs_cost}</code>",
            f"📦 <b>Копии:</b> <code>{card.copies_owned}</code>",
            "",
            "<i>После подтверждения карта будет улучшена, если хватит ресурсов.</i>",
        ]
    )


def deck_builder_text(
    cards: list[PlayerCard], templates: dict[int, CardTemplate], selected_ids: list[int]
) -> str:
    """Build the deck-constructor screen."""

    if not cards:
        return (
            "🧱 <b>Конструктор колоды</b>\n"
            "<i>У тебя пока нет карт. Открой баннеры или магазин, чтобы собрать коллекцию.</i>"
        )
    lines = [
        "🧱 <b>Конструктор колоды</b>",
        f"🎯 <b>Выбрано:</b> <code>{len(selected_ids)}/5</code>",
    ]
    if selected_ids:
        lines.append("📌 <b>Текущий набор:</b>")
        for index, card_id in enumerate(selected_ids, start=1):
            owned_card = next((card for card in cards if card.id == card_id), None)
            template = templates.get(owned_card.template_id) if owned_card else None
            name = (
                template.name
                if template
                else f"Шаблон #{owned_card.template_id}"
                if owned_card
                else f"Карта #{card_id}"
            )
            lines.append(
                f"• <code>{index}</code>. <b>{name}</b> — <code>#{card_id}</code>"
            )
    else:
        lines.append("<i>Пока пусто. Нажми на 5 карт ниже.</i>")
    lines.append("")
    lines.append("<i>Нажми на карту, чтобы добавить или убрать её из колоды.</i>")
    lines.append("<i>Когда выбрано 5 карт, нажми «Сохранить».</i>")
    return "\n".join(lines)


def gallery_text(
    templates: list[CardTemplate],
    page: int = 1,
    *,
    total_pages: int | None = None,
) -> str:
    """Build the public gallery of card templates."""

    if not templates:
        return "📖 <b>Галерея карт</b>\n<i>Пока пусто.</i>"
    lines = ["📖 <b>Галерея карт</b>"]
    if total_pages is not None:
        lines.extend([f"📄 <b>Страница:</b> <code>{page}/{total_pages}</code>", ""])
    lines.extend(
        [
            f"• <b>{template.name}</b> — <code>{template.id}</code> · {template.rarity.value} · {_stats(template.base_stats)}"
            for template in templates
        ]
    )
    return "\n".join(lines)


def card_template_text(template: CardTemplate) -> str:
    """Render a card template with stats and ability summary."""

    ability = template.ability
    universe = getattr(template.universe, "value", template.universe)
    return (
        f"🎴 <b>{template.name}</b>\n"
        f"🆔 <b>ID:</b> <code>{template.id}</code>\n"
        f"🌌 <b>Вселенная:</b> <code>{universe}</code>\n"
        f"⭐ <b>Редкость:</b> <code>{template.rarity.value}</code>\n"
        f"🧩 <b>Класс:</b> <code>{template.card_class.value}</code>\n\n"
        f"💥 <b>База:</b> <code>{_stats(template.base_stats)}</code>\n"
        f"🔥 <b>Возвышение:</b> <code>{_stats(template.ascended_stats)}</code>\n\n"
        f"<i>Способность:</i> <code>{ability.cost}/{ability.cooldown}</code>\n\n"
    )


def admin_cards_text(templates: list[CardTemplate]) -> str:
    """Build the admin card catalog screen."""

    if not templates:
        return (
            "🎴 <b>Карты</b>\n<i>Пока шаблонов нет. Самое время создать первый ✨</i>"
        )
    return "\n".join(
        [
            "🎴 <b>Карты</b>",
            *[
                f"• <b>{template.name}</b> — <code>{template.id}</code> · {template.rarity.value}"
                for template in templates
            ],
        ]
    )


def universes_text(values: list[str]) -> str:
    """Render the editable universe list."""

    if not values:
        return "🌌 <b>Вселенные</b>\n<i>Список пустой. Добавь первую вселенную ✨</i>"
    return "\n".join(
        [
            "🌌 <b>Вселенные</b>",
            *[f"• <code>{value}</code>" for value in values],
            "\n<i>Можешь добавить новую или удалить лишнюю.</i>",
        ]
    )


def ability_effects_guide() -> str:
    """Describe the effect syntax and available enum values."""

    return """
🎯 <b>Эффекты способности</b>
<i>Можно вводить по одному эффекту в строке или через <code>;</code>.</i>

<b>Как писать:</b> <code>target:stat:duration:value</code>
<b>Примеры:</b> <code>self:defense:1:2</code>, <code>opponents_deck:health:2:-3</code>

<b>TargetType:</b>
• <code>self</code>
• <code>teammates_deck</code>
• <code>opponents_deck</code>

<b>StatType:</b>
• <code>damage</code>
• <code>health</code>
• <code>defense</code>

<i>Если у возвышенной формы другая способность — введи её эффекты. Иначе отправь <code>-</code>.</i>
""".strip()


def image_input_guide() -> str:
    """Explain which image formats the admin wizard accepts."""

    return """
🖼️ <b>Изображение карты</b>
<i>Можешь прислать:</i>
• фото прямо в Telegram
• документ с картинкой
• ссылку на изображение
• готовый file_id

<i>Картинка сохранится локально в хранилище бота.</i>
""".strip()


def card_text(card: PlayerCard, template: CardTemplate | None) -> str:
    """Build one card detail screen."""

    name = template.name if template else f"Шаблон #{card.template_id}"
    stats = template.stats_for(card.current_form) if template else None
    body = [
        f"🎴 <b>{name}</b>",
        f"🆔 <b>Карта:</b> <code>{card.id}</code>",
        f"⭐ <b>Уровень:</b> <code>{card.level}</code>",
        f"📦 <b>Копии:</b> <code>{card.copies_owned}</code>",
        f"🔥 <b>Возвышена:</b> <code>{'да' if card.is_ascended else 'нет'}</code>",
        f"🌀 <b>Форма:</b> <code>{card.current_form.value}</code>",
    ]
    if stats:
        body.extend(
            [
                f"💥 <b>Урон:</b> <code>{stats.damage}</code>",
                f"❤️ <b>Здоровье:</b> <code>{stats.health}</code>",
                f"🛡️ <b>Защита:</b> <code>{stats.defense}</code>",
            ]
        )
    return "\n".join(body)


def card_wizard_text(step: str, draft: dict) -> str:
    """Render the card creation wizard."""

    return f"🎴 <b>Создание карты</b>\n<i>Шаг:</i> <code>{step}</code>\n\n<b>Название:</b> {draft.get('name', '—')}\n<b>Вселенная:</b> {draft.get('universe', '—')}\n<b>Редкость:</b> {draft.get('rarity', '—')}\n<b>Класс:</b> {draft.get('card_class', '—')}\n<b>База:</b> {draft.get('base_stats', '—')}\n<b>Возвышение:</b> {draft.get('ascended_stats', '—')}\n<b>Способность:</b> {draft.get('ability', '—')}\n<b>Возвышенная способность:</b> {draft.get('ascended_ability', '—')}\n\n<i>Можешь в любой момент нажать «Сбросить» и начать заново.</i>"


def standard_cards_text(ids: list[int], templates: dict[int, CardTemplate]) -> str:
    """Render the starter-card list editor."""

    if not ids:
        return "🆓 <b>Стартовые карты</b>\n<i>Список пустой. Новые игроки получат только базовый старт.</i>"
    lines = ["🆓 <b>Стартовые карты</b>"]
    for template_id in ids:
        template = templates.get(template_id)
        name = template.name if template else f"Шаблон #{template_id}"
        lines.append(f"• <b>{name}</b> — <code>{template_id}</code>")
    lines.append(
        "\n<i>Эти карты получат только новые игроки. Старых это не затрагивает.</i>"
    )
    return "\n".join(lines)


__all__ = [
    "ability_effects_guide",
    "admin_cards_text",
    "card_level_up_confirm_text",
    "card_template_text",
    "card_text",
    "cards_text",
    "card_wizard_text",
    "deck_builder_text",
    "gallery_text",
    "image_input_guide",
    "standard_cards_text",
    "universes_text",
]
