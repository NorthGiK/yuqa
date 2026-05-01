"""Admin dashboard and wizard text renderers."""


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
        "premium_battle_pass": "💎 <b>Premium Battle Pass</b>",
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
        f"💎 <b>Уровней Premium BP:</b> <code>{counts.get('premium_battle_pass_levels', 0)}</code>\n"
        f"💡 <b>На модерации:</b> <code>{counts.get('ideas_pending', 0)}</code>\n"
        f"📣 <b>В голосовании:</b> <code>{counts.get('ideas_public', 0)}</code>\n"
        f"📚 <b>В коллекции:</b> <code>{counts.get('ideas_collection', 0)}</code>\n"
        f"🗑 <b>Отклонено:</b> <code>{counts.get('ideas_rejected', 0)}</code>\n\n"
        "<i>Выбери раздел и собери контент без суеты ✨</i>"
    )


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
        "<i>Поддерживаются фото, видео, документы, ссылки и готовые file_id. "
        "Медиа сохранится локально.</i>"
    )


def shop_wizard_text(step: str, draft: dict) -> str:
    """Render the shop item creation wizard."""

    return f"🛒 <b>Создание товара</b>\n<i>Шаг:</i> <code>{step}</code>\n\n<b>Отдаём:</b> {draft.get('sell_resource_type', '—')}\n<b>Берём:</b> {draft.get('buy_resource_type', '—')}\n<b>Цена:</b> {draft.get('price', '—')}\n<b>Количество:</b> {draft.get('quantity', '—')}\n<b>Активен:</b> {draft.get('is_active', '—')}\n\n<i>Один и тот же товар можно добавить сколько угодно раз.</i>"


__all__ = [
    "admin_text",
    "banner_wizard_text",
    "profile_background_wizard_text",
    "shop_wizard_text",
]
