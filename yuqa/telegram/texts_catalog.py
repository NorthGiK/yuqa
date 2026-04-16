"""Clan, shop, and banner text renderers."""

from html import escape

from yuqa.banners.domain.entities import Banner
from yuqa.cards.domain.entities import CardTemplate
from yuqa.clans.domain.entities import Clan
from yuqa.players.domain.entities import Player, ProfileBackgroundTemplate
from yuqa.shop.domain.entities import ShopItem
from yuqa.telegram.texts_shared import _player_name


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


__all__ = ["banner_pool_text", "banner_text", "clan_text", "shop_text"]
