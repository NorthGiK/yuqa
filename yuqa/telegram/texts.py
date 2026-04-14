"""Text renderers for Telegram screens."""

from datetime import datetime, timezone
from html import escape

from yuqa.banners.domain.entities import Banner
from yuqa.battle_pass.domain.entities import BattlePassSeason
from yuqa.battles.domain.entities import Battle
from yuqa.cards.domain.entities import CardTemplate, PlayerCard
from yuqa.clans.domain.entities import Clan
from yuqa.ideas.domain.entities import Idea
from yuqa.players.domain.entities import (
    Player,
    PlayerTopEntry,
    ProfileBackgroundTemplate,
)
from yuqa.shared.enums import IdeaStatus
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.shop.domain.entities import ShopItem


def _wallet(player: Player) -> str:
    """Render player resources in a compact block."""

    wallet = player.wallet
    return (
        f"🪙 <b>Монеты:</b> <code>{wallet.coins}</code>\n"
        f"💎 <b>Кристаллы:</b> <code>{wallet.crystals}</code>\n"
        f"🔮 <b>Орбы:</b> <code>{wallet.orbs}</code>\n"
        f"🎫 <b>Серебряные билеты:</b> <code>{wallet.silver_tickets}</code>\n"
        f"🎟️ <b>Золотые билеты:</b> <code>{wallet.gold_tickets}</code>"
    )


def _stats(stats: StatBlock | None) -> str:
    return "—" if stats is None else f"{stats.damage}/{stats.health}/{stats.defense}"


def _player_name(player: Player) -> str:
    """Render the player's public name without HTML breakage."""

    if player.nickname:
        base = escape(player.nickname)
    else:
        base = f"Игрок <code>{player.telegram_id}</code>"
    if player.title:
        return f"{base} <b>{escape(player.title)}</b>"
    return base


def _background_label(background: ProfileBackgroundTemplate | None) -> str:
    """Render a compact profile-background label."""

    if background is None:
        return "<i>не выбран</i>"
    kind = "video" if background.media.content_type.startswith("video/") else "image"
    return (
        f"<code>#{background.id}</code> · "
        f"<code>{background.rarity.value}</code> · <code>{kind}</code>"
    )


def _idea_status_label(status: IdeaStatus) -> str:
    """Render a human-readable idea status."""

    labels = {
        IdeaStatus.PENDING: "на модерации",
        IdeaStatus.PUBLISHED: "на странице идей",
        IdeaStatus.COLLECTED: "в коллекции",
        IdeaStatus.REJECTED: "отклонена",
    }
    return labels[status]


def _cooldown_line(ready_at: datetime, now: datetime | None = None) -> str:
    """Render time remaining until a reward is ready."""

    current = now or datetime.now(timezone.utc)
    if ready_at <= current:
        return "✅ <b>Готово</b>"
    remaining = ready_at - current
    total_seconds = int(remaining.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"⏳ <b>Через:</b> <code>{hours:02d}:{minutes:02d}:{seconds:02d}</code>"


def menu_text(player: Player) -> str:
    """Build the friendly home screen text."""

    return (
        "🎮 <b>Добро пожаловать в Yuqa!</b>\n"
        "<i>Здесь карты не лежат в пыли — они дерутся, качаются и сияют.</i> ✨\n\n"
        f"👋 <b>Игрок:</b> {_player_name(player)}\n"
        f"🆔 <b>Твой Telegram ID:</b> <code>{player.telegram_id}</code>\n"
        f"🏆 <b>Рейтинг:</b> <code>{player.rating}</code>\n"
        f"🔥 <b>Победы:</b> <code>{player.wins}</code>  "
        f"⚔️ <b>Поражения:</b> <code>{player.losses}</code>  "
        f"🤝 <b>Ничьи:</b> <code>{player.draws}</code>\n\n"
        f"{_wallet(player)}"
    )


def battle_text(player: Player | None = None, searching: bool = False) -> str:
    """Explain how to start or cancel a battle search."""

    header = "⚔️ <b>Арена PvP</b>\n<i>Пора показать, кто тут главный!</i>\n\n"
    body = (
        "• для боя нужна колода из <b>5 разных карт</b>\n"
        "• поиск соперника подбирает игрока с разницей рейтинга <b>±100</b>\n"
        "• можно остановить поиск в любой момент\n"
    )
    if player is None:
        return header + body
    line = f"👤 <b>Твой ID:</b> <code>{player.telegram_id}</code>\n"
    line += f"🔎 <b>Статус:</b> <i>{'ищем соперника' if searching else 'готов к бою'}</i>\n\n"
    return header + line + body


def battle_started_text(battle: Battle) -> str:
    """Render a short message after battle creation."""

    return (
        "💥 <b>Бой начался!</b>\n"
        f"🆔 <b>Бой:</b> <code>{battle.id}</code>\n"
        f"🎲 <b>Первый ход:</b> <code>{battle.first_turn_player_id}</code>\n"
        f"📍 <i>Раунд {battle.current_round}</i>\n"
    )


def battle_pass_text(season: BattlePassSeason | None, player: Player) -> str:
    """Render the current battle pass and player progress."""

    points = sum(player.battle_pass_progress)
    if season is None:
        return "🏁 <b>Battle Pass</b>\n<i>Сезон пока не активен.</i>"
    unlocked = (
        ", ".join(
            str(level.level_number)
            for level in season.levels
            if points >= level.required_points
        )
        or "—"
    )
    return (
        f"🏁 <b>{season.name}</b>\n"
        f"📅 <b>Период:</b> <code>{season.start_at.date()} → {season.end_at.date()}</code>\n"
        f"⭐ <b>Твои очки:</b> <code>{points}</code>\n"
        f"🎁 <b>Открыты уровни:</b> <code>{unlocked}</code>\n\n"
        "<i>Очки Battle Pass приходят за квесты и события. Можно купить следующий уровень за 250 монет.</i>"
    )


def battle_pass_admin_text(season: BattlePassSeason | None) -> str:
    """Render the current admin view for battle pass levels."""

    if season is None:
        return "🏁 <b>Battle Pass</b>\n<i>Активный сезон не найден.</i>"
    if not season.levels:
        levels = "<i>Пока уровней нет.</i>"
    else:
        levels = "\n".join(
            f"• <b>Уровень {level.level_number}</b> — <code>{level.required_points}</code> очков, награда: "
            f"<code>{level.reward.coins}</code>🪙 <code>{level.reward.crystals}</code>💎 <code>{level.reward.orbs}</code>🔮"
            for level in season.levels
        )
    return (
        f"🏁 <b>{season.name}</b>\n"
        f"📅 <b>Период:</b> <code>{season.start_at.date()} → {season.end_at.date()}</code>\n"
        f"🎚️ <b>Уровней:</b> <code>{len(season.levels)}</code>\n\n"
        f"{levels}"
    )


def battle_pass_seasons_text(seasons: list[BattlePassSeason]) -> str:
    """Render the admin battle pass season list."""

    if not seasons:
        return "🏁 <b>Battle Pass</b>\n<i>Сезонов пока нет.</i>"
    lines = ["🏁 <b>Battle Pass</b>"]
    for season in seasons:
        status = "активен" if season.is_active else "архив"
        lines.append(
            f"• <b>{season.name}</b> — <code>{season.start_at.date()} → {season.end_at.date()}</code> · {status}"
        )
    return "\n".join(lines)


def battle_pass_level_wizard_text(step: str, draft: dict) -> str:
    """Render the battle pass level creation wizard."""

    return (
        "🏁 <b>Добавление уровня Battle Pass</b>\n"
        f"<i>Текущий шаг:</i> <code>{step}</code>\n\n"
        f"<b>Уровень:</b> {draft.get('level_number', '—')}\n"
        f"<b>Нужно очков:</b> {draft.get('required_points', '—')}\n"
        f"<b>Награда:</b> {draft.get('reward', '—')}\n\n"
        "<i>Пиши по одному полю за раз. На любом шаге можно нажать <b>Сбросить</b>.</i>\n"
        "<i>Награду вводи как:</i> <code>coins crystals orbs</code>\n"
        "<i>Пример:</i> <code>100 5 1</code>"
    )


def battle_pass_season_wizard_text(step: str, draft: dict) -> str:
    """Render the battle pass season creation wizard."""

    return (
        "🏁 <b>Создание Battle Pass</b>\n"
        f"<i>Текущий шаг:</i> <code>{step}</code>\n\n"
        f"<b>Название:</b> {draft.get('name', '—')}\n"
        f"<b>Старт:</b> {draft.get('start_at', '—')}\n"
        f"<b>Финиш:</b> {draft.get('end_at', '—')}\n\n"
        "<i>Даты вводи в ISO-формате, например <code>2026-04-10T12:00:00+00:00</code>.</i>"
    )


def profile_text(
    player: Player,
    clan: Clan | None,
    selected_background: ProfileBackgroundTemplate | None = None,
) -> str:
    """Build the player profile screen."""

    clan_line = f"<b>{clan.name}</b>" if clan else "<i>нет клана</i>"
    return (
        "👤 <b>Профиль бойца</b>\n\n"
        f"🏷 <b>Имя:</b> {_player_name(player)}\n"
        f"🆔 <b>ID:</b> <code>{player.telegram_id}</code>\n"
        f"📅 <b>Создан:</b> <code>{player.created_at.date()!s}</code>\n"
        f"🏆 <b>Рейтинг:</b> <code>{player.rating}</code>\n"
        f"🔥 <b>Победы/Проигрыши/Ничьи:</b> <code>{player.wins}/{player.losses}/{player.draws}</code>\n"
        f"🪄 <b>Creator Points:</b> <code>{player.creator_points}</code>\n"
        f"🏰 <b>Клан:</b> {clan_line}\n"
        f"📚 <b>Коллекция:</b> <code>{player.collection_count}</code>\n\n"
        f"🎨 <b>Активный фон:</b> {_background_label(selected_background)}\n"
        f"🖼 <b>Фонов в коллекции:</b> <code>{len(player.owned_profile_background_ids)}</code>\n\n"
        f"{_wallet(player)}"
    )


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


def free_rewards_text(
    player: Player, status: dict[str, object], notice: str | None = None
) -> str:
    """Build the free rewards screen."""

    card_ready_at = status["card_ready_at"]
    resource_ready_at = status["resource_ready_at"]
    lines = [
        "🎁 <b>Бесплатные награды</b>",
        "<i>Каждую категорию можно забирать раз в 2 часа.</i>",
        "",
        f"🎴 <b>Карта:</b> {_cooldown_line(card_ready_at)}",
        f"💰 <b>Ресурсы:</b> {_cooldown_line(resource_ready_at)}",
        "",
        f"📚 <b>Коллекция:</b> <code>{player.collection_count}</code>",
        f"🪙 <b>Монеты:</b> <code>{player.wallet.coins}</code>",
        f"💎 <b>Кристаллы:</b> <code>{player.wallet.crystals}</code>",
        f"🔮 <b>Орбы:</b> <code>{player.wallet.orbs}</code>",
    ]
    if notice:
        lines.extend(["", notice])
    return "\n".join(lines)


def free_rewards_admin_text(settings: dict[str, dict[str, int]]) -> str:
    """Render free reward configuration for admins."""

    card_weights = settings["card_weights"]
    resource_weights = settings["resource_weights"]
    resource_values = settings["resource_values"]
    return "\n".join(
        [
            "🎁 <b>Бесплатные награды</b>",
            "<i>Отдельные кулдауны: карта и ресурсы, по 2 часа.</i>",
            "",
            "🎴 <b>Шансы редкости карты:</b>",
            *[
                f"• <code>{name}</code> = <code>{value}</code>"
                for name, value in card_weights.items()
            ],
            "",
            "💰 <b>Шансы типа ресурса:</b>",
            *[
                f"• <code>{name}</code> = <code>{value}</code>"
                for name, value in resource_weights.items()
            ],
            "",
            "📦 <b>Значения ресурсов:</b>",
            *[
                f"• <code>{name}</code> = <code>{value}</code>"
                for name, value in resource_values.items()
            ],
        ]
    )


def free_rewards_edit_guide(mode: str) -> str:
    """Explain how an admin should edit one free reward config block."""

    examples = {
        "card_weights": "common=50 rare=25 epic=15 mythic=5 legendary=4 godly=1",
        "resource_weights": "coins=50 crystals=30 orbs=20",
        "resource_values": "coins=1000 crystals=25 orbs=1",
    }
    titles = {
        "card_weights": "🎴 <b>Шансы редкости карты</b>",
        "resource_weights": "💰 <b>Шансы типа ресурса</b>",
        "resource_values": "📦 <b>Значения ресурсов</b>",
    }
    return (
        f"{titles[mode]}\n"
        "<i>Введи все пары в одной строке через пробел.</i>\n\n"
        f"<b>Пример:</b> <code>{examples[mode]}</code>"
    )


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


def ideas_text(
    ideas: list[Idea],
    page: int,
    *,
    title: str = "💡 <b>Идеи</b>",
    empty_text: str = "Пока идей нет.",
) -> str:
    """Render one page of idea titles with upvote counts."""

    if not ideas:
        return f"{title}\n<i>{empty_text}</i>"
    lines = [title, f"📄 <b>Страница:</b> <code>{page}</code>", ""]
    for idea in ideas:
        lines.append(f"• <b>{escape(idea.title)}</b> — 👍 <code>{idea.upvotes}</code>")
    return "\n".join(lines)


def idea_text(
    idea: Idea, author: Player | None, *, viewer_vote: int | None = None
) -> str:
    """Render one idea with author, body, and vote counters."""

    lines = [
        f"👤 <b>Автор:</b> {_player_name(author) if author else f'Игрок <code>{idea.player_id}</code>'}",
        "",
        f"💡 <b>{escape(idea.title)}</b>",
        escape(idea.description),
        "",
        f"👍 <b>За:</b> <code>{idea.upvotes}</code>",
        f"👎 <b>Против:</b> <code>{idea.downvotes}</code>",
        f"📌 <b>Статус:</b> <code>{_idea_status_label(idea.status)}</code>",
    ]
    if viewer_vote is not None:
        lines.append(
            f"🗳 <b>Твой голос:</b> <code>{'за' if viewer_vote > 0 else 'против'}</code>"
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
        f"<i>Способность:</i> <code>{ability.cost}/{ability.cooldown}</code>"
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

<i>Картинка сохранится локально как ссылка или Telegram file_id.</i>
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


def clan_text(
    clan: Clan | None, player: Player, members: list[Player] | None = None
) -> str:
    """Build clan information text."""

    if clan is None:
        return "🏰 <b>Клан</b>\n<i>Ты пока не в клане — самое время собрать сильную команду.</i>\n\n📈 <b>Для создания:</b> рейтинг <code>1001+</code>\n🪙 <b>Стоимость:</b> <code>10000</code> монет"
    role = "глава" if player.telegram_id == clan.owner_player_id else "участник"
    owner = next(
        (
            member
            for member in members or []
            if member.telegram_id == clan.owner_player_id
        ),
        None,
    )
    roster = members or []
    member_lines = (
        "\n".join(f"• {_player_name(member)}" for member in roster[:10])
        or "<i>пока пусто</i>"
    )
    return (
        f"🏰 <b>{escape(clan.name)}</b> {clan.icon}\n"
        f"🆔 <b>ID:</b> <code>{clan.id}</code>\n"
        f"👑 <b>Владелец:</b> {_player_name(owner or player)}\n"
        f"👥 <b>Участники:</b> <code>{len(clan.members)}/25</code>\n"
        f"📈 <b>Порог:</b> <code>{clan.min_entry_rating}</code>\n"
        f"🎭 <b>Твоя роль:</b> <i>{role}</i>\n\n"
        f"📋 <b>Состав:</b>\n{member_lines}"
    )


def shop_text(items: list[ShopItem]) -> str:
    """Build the shop catalog screen."""

    if not items:
        return "🛒 <b>Магазин</b>\n<i>Пока витрины пустые. Админ скоро всё завезёт.</i>"
    return "\n".join(
        [
            "🛒 <b>Магазин</b>",
            *[
                f"• <b>{item.id}</b> — <code>{item.price}</code> {item.buy_resource_type.value} → <code>{item.quantity}</code> {item.sell_resource_type.value}"
                for item in items
            ],
        ]
    )


def banner_text(banner: Banner, editable: bool = False) -> str:
    """Build banner information text."""

    status = "🟢 открыт для правок" if editable else "🔒 уже запущен"
    return f"🎁 <b>{banner.name}</b>\n🆔 <b>ID:</b> <code>{banner.id}</code>\n🎲 <b>Тип:</b> <code>{banner.banner_type.value}</code>\n🎫 <b>Билет:</b> <code>{banner.cost_resource.value}</code>\n📦 <b>Элементов в пуле:</b> <code>{len(banner.pools)}</code>\n{status}"


def banner_pool_text(
    banner: Banner,
    templates: dict[int, CardTemplate],
    backgrounds: dict[int, ProfileBackgroundTemplate] | None = None,
) -> str:
    """Render banner reward pools."""

    if not banner.pools:
        return "<i>Пул пока пустой. Самое время добавить любимые карты ✨</i>"
    lines = []
    for reward in banner.pools:
        if reward.profile_background_id is not None:
            background = (backgrounds or {}).get(reward.profile_background_id)
            name = (
                f"Фон #{background.id} · {background.rarity.value}"
                if background is not None
                else f"Фон #{reward.profile_background_id}"
            )
            lines.append(
                f"• <b>{name}</b> — вес <code>{reward.weight}</code>, "
                f"гарант x10: <code>{'да' if reward.guaranteed_for_10_pull else 'нет'}</code>"
            )
            continue
        if reward.card_template_id is None:
            lines.append(
                f"• <b>{reward.reward_type.value}</b> × <code>{reward.quantity}</code>"
            )
            continue
        template = templates.get(reward.card_template_id)
        name = template.name if template else f"#{reward.card_template_id}"
        lines.append(
            f"• <b>{name}</b> — вес <code>{reward.weight}</code>, гарант x10: <code>{'да' if reward.guaranteed_for_10_pull else 'нет'}</code>"
        )
    return "\n".join(lines)


def admin_text(counts: dict[str, int], section: str = "dashboard") -> str:
    """Build a compact admin dashboard."""

    titles = {
        "dashboard": "🛠 <b>Админ-панель</b>",
        "cards": "🎴 <b>Управление картами</b>",
        "profile_backgrounds": "🖼 <b>Фоны профиля</b>",
        "players": "👥 <b>Управление игроками</b>",
        "banners": "🎁 <b>Управление баннерами</b>",
        "shop": "🛒 <b>Управление магазином</b>",
        "standard_cards": "🆓 <b>Стартовые карты</b>",
        "universes": "🌌 <b>Вселенные</b>",
        "battle_pass": "🏁 <b>Battle Pass</b>",
        "free_rewards": "🎁 <b>Бесплатные награды</b>",
        "ideas_pending": "💡 <b>Идеи на модерации</b>",
        "ideas_public": "📣 <b>Идеи в голосовании</b>",
        "ideas_collection": "📚 <b>Коллекция идей</b>",
        "ideas_rejected": "🗑 <b>Отклонённые идеи</b>",
    }
    title = titles.get(section, titles["dashboard"])
    return (
        f"{title}\n\n"
        f"👥 <b>Игроков:</b> <code>{counts.get('players', 0)}</code>\n"
        f"🎴 <b>Карт:</b> <code>{counts.get('cards', 0)}</code>\n"
        f"🖼 <b>Фонов профиля:</b> <code>{counts.get('profile_backgrounds', 0)}</code>\n"
        f"🎁 <b>Баннеров:</b> <code>{counts.get('banners', 0)}</code>\n"
        f"🛒 <b>Товаров:</b> <code>{counts.get('shop', 0)}</code>\n"
        f"🆓 <b>Стартовых карт:</b> <code>{counts.get('standard_cards', 0)}</code>\n"
        f"🌌 <b>Вселенных:</b> <code>{counts.get('universes', 0)}</code>\n"
        f"🏁 <b>Уровней BP:</b> <code>{counts.get('battle_pass_levels', 0)}</code>\n"
        f"💡 <b>На модерации:</b> <code>{counts.get('ideas_pending', 0)}</code>\n"
        f"📣 <b>В голосовании:</b> <code>{counts.get('ideas_public', 0)}</code>\n"
        f"📚 <b>В коллекции:</b> <code>{counts.get('ideas_collection', 0)}</code>\n"
        f"🗑 <b>Отклонено:</b> <code>{counts.get('ideas_rejected', 0)}</code>\n\n"
        "<i>Выбери раздел и собери контент без суеты ✨</i>"
    )


def admin_profile_backgrounds_text(
    backgrounds: list[ProfileBackgroundTemplate],
) -> str:
    """Build the admin profile-background catalog screen."""

    if not backgrounds:
        return "🖼 <b>Фоны профиля</b>\n<i>Пока фонов нет. Добавь первый и выдай игрокам стиль ✨</i>"
    return "\n".join(
        [
            "🖼 <b>Фоны профиля</b>",
            *[
                f"• <b>Фон #{background.id}</b> — <code>{background.rarity.value}</code>"
                for background in backgrounds
            ],
        ]
    )


def card_wizard_text(step: str, draft: dict) -> str:
    """Render the card creation wizard."""

    return f"🎴 <b>Создание карты</b>\n<i>Шаг:</i> <code>{step}</code>\n\n<b>Название:</b> {draft.get('name', '—')}\n<b>Вселенная:</b> {draft.get('universe', '—')}\n<b>Редкость:</b> {draft.get('rarity', '—')}\n<b>Класс:</b> {draft.get('card_class', '—')}\n<b>База:</b> {draft.get('base_stats', '—')}\n<b>Возвышение:</b> {draft.get('ascended_stats', '—')}\n<b>Способность:</b> {draft.get('ability', '—')}\n<b>Возвышенная способность:</b> {draft.get('ascended_ability', '—')}\n\n<i>Можешь в любой момент нажать «Сбросить» и начать заново.</i>"


def banner_wizard_text(step: str, draft: dict) -> str:
    """Render the banner creation wizard."""

    return f"🎁 <b>Создание баннера</b>\n<i>Шаг:</i> <code>{step}</code>\n\n<b>Название:</b> {draft.get('name', '—')}\n<b>Тип:</b> {draft.get('banner_type', '—')}\n<b>Валюта:</b> {draft.get('cost_resource', '—')}\n<b>Старт:</b> {draft.get('start_at', '—')}\n<b>Стоп:</b> {draft.get('end_at', '—')}\n\n<i>Пока старт не наступил, пул баннера можно редактировать.</i>"


def profile_background_wizard_text(step: str, draft: dict) -> str:
    """Render the profile-background creation wizard."""

    return (
        "🖼 <b>Создание фона профиля</b>\n"
        f"<i>Шаг:</i> <code>{step}</code>\n\n"
        f"<b>Редкость:</b> {draft.get('rarity', '—')}\n"
        f"<b>Медиа:</b> {draft.get('media', '—')}\n\n"
        "<i>Поддерживаются фото, видео, документы, ссылки и готовые file_id.</i>"
    )


def idea_wizard_text(step: str, draft: dict) -> str:
    """Render the player idea proposal flow."""

    return (
        "💡 <b>Новая идея механики</b>\n"
        f"<i>Шаг:</i> <code>{step}</code>\n\n"
        f"<b>Название:</b> {escape(str(draft.get('title', '—')))}\n"
        f"<b>Описание:</b> {escape(str(draft.get('description', '—')))}\n\n"
        "<i>После отправки идея попадёт на модерацию к администратору.</i>"
    )


def profile_backgrounds_text(
    backgrounds: list[ProfileBackgroundTemplate], selected_id: int | None
) -> str:
    """Render the owned profile-background collection."""

    if not backgrounds:
        return (
            "🖼 <b>Фоны профиля</b>\n<i>Коллекция пока пустая. Ищи фоны в баннерах.</i>"
        )
    lines = ["🖼 <b>Фоны профиля</b>"]
    for background in backgrounds:
        selected = " · ✅ выбран" if background.id == selected_id else ""
        lines.append(
            f"• <b>Фон #{background.id}</b> — <code>{background.rarity.value}</code>{selected}"
        )
    return "\n".join(lines)


def profile_background_text(
    background: ProfileBackgroundTemplate, *, selected: bool = False
) -> str:
    """Render one profile background detail screen."""

    kind = (
        "видео" if background.media.content_type.startswith("video/") else "изображение"
    )
    selected_line = "да" if selected else "нет"
    return (
        f"🖼 <b>Фон профиля #{background.id}</b>\n"
        f"⭐ <b>Редкость:</b> <code>{background.rarity.value}</code>\n"
        f"🎞 <b>Тип медиа:</b> <code>{kind}</code>\n"
        f"✅ <b>Выбран:</b> <code>{selected_line}</code>"
    )


def tops_text(entries: list[PlayerTopEntry], mode: str) -> str:
    """Render one users-top screen."""

    titles = {
        "rating": "🏆 <b>Топ по рейтингу</b>",
        "badenko_cards": "🃏 <b>Топ по Badenko-картам</b>",
        "creator_points": "🪄 <b>Топ по Creator Points</b>",
    }
    labels = {
        "rating": "рейтинг",
        "badenko_cards": "badenko",
        "creator_points": "creator points",
    }
    if not entries:
        return f"{titles[mode]}\n<i>Пока игроков в рейтинге нет.</i>"
    lines = [titles[mode], ""]
    for entry in entries:
        lines.append(
            f"{entry.rank}. {_player_name(entry.player)} — "
            f"<code>{entry.value}</code> {labels[mode]} · id <code>{entry.player.telegram_id}</code>"
        )
    return "\n".join(lines)


def shop_wizard_text(step: str, draft: dict) -> str:
    """Render the shop item creation wizard."""

    return f"🛒 <b>Создание товара</b>\n<i>Шаг:</i> <code>{step}</code>\n\n<b>Отдаём:</b> {draft.get('sell_resource_type', '—')}\n<b>Берём:</b> {draft.get('buy_resource_type', '—')}\n<b>Цена:</b> {draft.get('price', '—')}\n<b>Количество:</b> {draft.get('quantity', '—')}\n<b>Активен:</b> {draft.get('is_active', '—')}\n\n<i>Один и тот же товар можно добавить сколько угодно раз.</i>"


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
