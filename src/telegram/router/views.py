"""Screen rendering helpers extracted from the Telegram router."""

from html import escape

from src.players.domain.entities import ProfileBackgroundTemplate
from src.cards.domain.entities import PlayerCard
from src.shared.enums import IdeaStatus
from src.shared.errors import DomainError, ValidationError
from src.telegram.compat import CallbackQuery, Message
from src.telegram.reply import send_card_preview, send_media_preview, send_or_edit
from src.telegram.router.helpers import (
    _card_image_key,
    _paginate_items,
    _profile_backgrounds,
    _templates,
)
from src.telegram.services.services import TelegramServices
from src.telegram.texts import (
    admin_cards_text,
    admin_profile_backgrounds_text,
    admin_text,
    banner_pool_text,
    banner_text,
    battle_pass_admin_text,
    battle_pass_seasons_text,
    battle_pass_text,
    battle_result_text,
    battle_status_text,
    battle_text,
    cards_text,
    clan_text,
    collection_text,
    deck_builder_text,
    free_rewards_admin_text,
    free_rewards_text,
    gallery_text,
    idea_text,
    ideas_text,
    menu_text,
    premium_battle_pass_admin_text,
    premium_battle_pass_seasons_text,
    premium_battle_pass_text,
    profile_backgrounds_text,
    profile_text,
    shop_text,
    standard_cards_text,
    tops_text,
    universes_text,
    card_template_text,
    card_text,
)
from src.telegram.ui import (
    admin_banner_markup,
    admin_idea_detail_markup,
    admin_ideas_markup,
    admin_markup,
    banner_markup,
    battle_actions_markup,
    battle_markup,
    battle_pass_markup,
    battle_switch_markup,
    card_markup,
    cards_markup,
    clan_markup,
    collection_markup,
    deck_builder_markup,
    free_rewards_markup,
    gallery_markup,
    idea_detail_markup,
    ideas_markup,
    main_menu_markup,
    premium_battle_pass_markup,
    profile_backgrounds_markup,
    profile_markup,
    shop_markup,
    tops_markup,
)


async def show_home(event, services, player_id: int, *, is_admin: bool = False):
    """Show the main menu."""

    player = await services.get_or_create_player(player_id)
    if isinstance(event, CallbackQuery):
        if event.message is not None:
            await event.message.answer(
                menu_text(player),
                reply_markup=main_menu_markup(
                    is_admin=is_admin, is_premium=player.is_premium
                ),
            )
        return await event.answer()
    await event.answer(
        menu_text(player),
        reply_markup=main_menu_markup(is_admin=is_admin, is_premium=player.is_premium),
    )


async def show_profile(
    event,
    services,
    player_id: int,
    *,
    viewer_player_id: int | None = None,
):
    """Show the profile screen."""

    viewer_player_id = player_id if viewer_player_id is None else viewer_player_id
    player = await services.get_or_create_player(player_id)
    if player_id != viewer_player_id:
        player = await services.get_player(player_id)
        if player is None:
            text = "👤 <b>Профиль</b>\n<i>Игрок с таким ID не найден.</i>"
            if isinstance(event, CallbackQuery):
                if event.message is not None:
                    await event.message.answer(text, reply_markup=main_menu_markup())
                return await event.answer()
            return await event.answer(text, reply_markup=main_menu_markup())
    clan = await services.player_clan(player)
    selected_background = await services.selected_profile_background_for_player(player)
    markup = profile_markup(
        is_owner=player.telegram_id == viewer_player_id,
        has_nickname=player.nickname is not None,
    )
    text = profile_text(player, clan, selected_background)
    if selected_background is None:
        return await send_or_edit(event, text, markup)
    await send_media_preview(
        event,
        selected_background.media.storage_key,
        text,
        content_type=selected_background.media.content_type,
        reply_markup=markup,
    )


async def show_collection(event, services, player_id: int):
    """Show the collection hub."""

    player = await services.get_or_create_player(player_id)
    await send_or_edit(event, collection_text(player), collection_markup())


async def show_cards(event, services, player_id: int, page: int = 1):
    """Show the card collection."""

    cards: list[PlayerCard] = sorted(
        await services.list_player_cards(player_id), key=lambda card: card.id
    )
    page_cards, page, has_prev, has_next, total_pages = _paginate_items(cards, page)
    await send_or_edit(
        event,
        cards_text(page_cards, _templates(services), page, total_pages=total_pages),
        cards_markup(page_cards, page, has_prev=has_prev, has_next=has_next),
    )


async def show_gallery(event, services, page: int = 1):
    """Show the public gallery of all card templates."""

    templates = sorted(await services.list_card_templates(), key=lambda item: item.id)
    page_templates, page, has_prev, has_next, total_pages = _paginate_items(
        templates, page
    )
    await send_or_edit(
        event,
        gallery_text(page_templates, page, total_pages=total_pages),
        gallery_markup(page_templates, page, has_prev=has_prev, has_next=has_next),
    )


async def show_card_detail(
    event,
    services,
    card_id: int,
    player_id: int,
    *,
    page: int = 1,
    scope: str = "collection",
):
    """Show one owned card or gallery template."""

    if scope == "gallery":
        template = await services.get_template(card_id)
        if template is None:
            raise DomainError("card template not found")
        return await send_card_preview(
            event,
            _card_image_key(template),
            card_template_text(template),
            card_markup(
                card_id,
                False,
                False,
                False,
                page=page,
                scope="gallery",
            ),
            content_type=template.image.content_type,
        )
    card = await services.get_card(card_id, player_id)
    template = await services.get_template(card.template_id)
    if template is None:
        raise DomainError("card template not found")
    return await send_card_preview(
        event,
        _card_image_key(template),
        card_text(card, template),
        card_markup(
            card.id,
            card.can_level_up(),
            card.can_ascend(),
            card.is_ascended,
            page=page,
            scope="collection",
        ),
        content_type=template.image.content_type,
    )


async def show_ideas(event, services, player_id: int, page: int = 1):
    """Show the public ideas page with pagination."""

    ideas, has_prev, has_next = await services.list_ideas(
        status=IdeaStatus.PUBLISHED, page=page
    )
    await send_or_edit(
        event,
        ideas_text(
            ideas,
            page,
            title="💡 <b>Идеи</b>",
            empty_text="Пока на странице идей пусто.",
        ),
        ideas_markup(
            ideas,
            page,
            has_prev=has_prev,
            has_next=has_next,
        ),
    )


async def show_idea_collection(event, services, player_id: int, page: int = 1):
    """Show the current player's collected ideas."""

    ideas, has_prev, has_next = await services.list_ideas(
        status=IdeaStatus.COLLECTED, page=page, player_id=player_id
    )
    await send_or_edit(
        event,
        ideas_text(
            ideas,
            page,
            title="📚 <b>Моя коллекция идей</b>",
            empty_text="В твоей коллекции идей пока пусто.",
        ),
        ideas_markup(
            ideas,
            page,
            has_prev=has_prev,
            has_next=has_next,
            collection=True,
        ),
    )


async def show_idea_detail(
    event,
    services,
    idea_id: int,
    player_id: int,
    *,
    page: int = 1,
    scope: str = "published",
):
    """Show one public or collected idea."""

    idea = await services.get_idea(idea_id)
    if scope == "published" and idea.status != IdeaStatus.PUBLISHED:
        raise ValidationError("idea is not on the public ideas page")
    if scope == "collection" and (
        idea.status != IdeaStatus.COLLECTED or idea.player_id != player_id
    ):
        raise ValidationError("idea is not in your collection")
    author = await services.idea_author(idea)
    await send_or_edit(
        event,
        idea_text(idea, author, viewer_vote=idea.vote_of(player_id)),
        idea_detail_markup(
            idea.id,
            page,
            scope=scope,
            can_vote=scope == "published" and idea.vote_of(player_id) is None,
        ),
    )


async def show_admin_idea_detail(
    event,
    services,
    idea_id: int,
    *,
    page: int = 1,
    scope: str = "admin_pending",
):
    """Show one idea in the admin moderation browser."""

    idea = await services.get_idea(idea_id)
    author = await services.idea_author(idea)
    await send_or_edit(
        event,
        idea_text(idea, author),
        admin_idea_detail_markup(idea.id, page, scope=scope, status=idea.status),
    )


async def show_clan(event, services, player_id: int):
    """Show clan information."""

    player = await services.get_or_create_player(player_id)
    clan = await services.player_clan(player)
    members = await services.clan_members(clan)
    await send_or_edit(
        event,
        text=clan_text(clan, player, members),
        reply_markup=clan_markup(player.clan_id is not None),
    )


async def show_shop(event, services):
    """Show the shop catalog."""

    items = await services.list_active_shop_items()
    await send_or_edit(
        event, shop_text(items), shop_markup([item.id for item in items])
    )


async def show_banners(event, services):
    """Show active banners."""

    banners = await services.list_available_banners()
    if not banners:
        return await send_or_edit(
            event,
            "🎁 <b>Баннеры</b>\n<i>Пока активных баннеров нет.</i>",
        )
    await send_or_edit(
        event,
        "🎁 <b>Баннеры</b>\n"
        + "\n".join(
            f"• <b>{banner.name}</b> — <code>{banner.id}</code>" for banner in banners
        ),
        banner_markup(banners[0].id),
    )


def _battle_switch_cards(battle, player_id: int) -> list[tuple[int, str]]:
    """Build the alive card list for the battle switch picker."""

    side = battle.side_for(player_id)
    cards: list[tuple[int, str]] = []
    for card in side.cards.values():
        if not card.alive:
            continue
        active = "✅ " if card.player_card_id == side.active_card_id else ""
        cards.append(
            (
                card.player_card_id,
                f"{active}{escape(card.template.name)} |♥️{card.current_health}| "
                f"|⚔️{card.damage}| |🛡️{card.defense}|",
            )
        )
    return cards


async def show_battle_round(
    event,
    services,
    player_id: int,
    *,
    battle=None,
    prefix: str | None = None,
):
    """Show the battle round status screen."""

    battle = battle or await services.get_active_battle(player_id)
    if battle is None:
        return await show_battle(event, services, player_id)
    if battle.status.value != "active":
        player = await services.get_player(player_id)
        if player is None:
            player = await services.get_or_create_player(player_id)
        text = battle_result_text(battle, player)
        if prefix is not None:
            text = prefix + "\n\n" + text
        return await send_or_edit(event, text, None)
    summary = services.battle_round_summary(battle, player_id)
    text = battle_status_text(
        battle,
        player_id,
        current_turn_player_id=summary.current_turn_player_id,
        opponent_spent_action_points=summary.opponent_spent_action_points,
        available_action_points=summary.available_action_points,
        total_action_points=summary.total_action_points,
        attack_count=summary.attack_count,
        block_count=summary.block_count,
        bonus_count=summary.bonus_count,
        ability_used=summary.ability_used,
    )
    if prefix is not None:
        text = prefix + "\n\n" + text
    markup = None
    if (
        battle.status.value == "active"
        and summary.is_player_turn
        and summary.available_action_points > 0
    ):
        markup = battle_actions_markup(
            can_switch=summary.can_switch,
            ability_cost=summary.ability_cost,
            can_use_ability=(
                not summary.ability_used
                and summary.ability_cooldown_remaining <= 0
                and summary.available_action_points >= summary.ability_cost
            ),
        )
    await send_or_edit(event, text, markup)


async def show_battle_switch(event, services, player_id: int):
    """Show the battle switch picker for alive cards."""

    battle = await services.get_active_battle(player_id)
    if battle is None:
        return await show_battle(event, services, player_id)
    cards = _battle_switch_cards(battle, player_id)
    if len(cards) <= 1:
        return await show_battle_round(event, services, player_id, battle=battle)
    summary = services.battle_round_summary(battle, player_id)
    if battle.status.value != "active":
        return await show_battle_round(event, services, player_id, battle=battle)
    await send_or_edit(
        event,
        battle_status_text(
            battle,
            player_id,
            current_turn_player_id=summary.current_turn_player_id,
            opponent_spent_action_points=summary.opponent_spent_action_points,
            available_action_points=summary.available_action_points,
            total_action_points=summary.total_action_points,
            attack_count=summary.attack_count,
            block_count=summary.block_count,
            bonus_count=summary.bonus_count,
            ability_used=summary.ability_used,
        ),
        battle_switch_markup(cards),
    )


async def show_battle(event, services, player_id: int):
    """Show the battle lobby with matchmaking state."""

    battle = await services.get_active_battle(player_id)
    if battle is not None:
        return await show_battle_round(event, services, player_id, battle=battle)
    player = await services.get_or_create_player(player_id)
    await send_or_edit(
        event,
        battle_text(player, await services.is_searching(player_id)),
        battle_markup(await services.is_searching(player_id)),
    )


async def show_deck_builder(event, services, player_id: int):
    """Show the deck constructor."""

    cards = await services.list_player_cards(player_id)
    templates = _templates(services)
    selected_ids = await services.deck_draft(player_id)
    await send_or_edit(
        event,
        deck_builder_text(cards, templates, selected_ids),
        deck_builder_markup(cards, selected_ids),
    )


async def show_free_rewards(event, services, player_id: int, notice: str | None = None):
    """Show the free rewards screen."""

    player = await services.get_or_create_player(player_id)
    status = await services.free_rewards_status(player_id)
    await send_or_edit(
        event, free_rewards_text(player, status, notice), free_rewards_markup()
    )


async def show_battle_pass(event, services, player_id: int):
    """Show the current battle pass progress."""

    player = await services.get_or_create_player(player_id)
    season = await services.active_battle_pass()
    await send_or_edit(
        event,
        battle_pass_text(season, player),
        battle_pass_markup(can_buy_level=season is not None),
    )


async def show_premium_battle_pass(event, services, player_id: int):
    """Show the premium battle pass progress for premium players."""

    player = await services.get_or_create_player(player_id)
    season = await services.active_premium_battle_pass()
    await send_or_edit(
        event,
        premium_battle_pass_text(season, player),
        premium_battle_pass_markup(
            can_buy_level=season is not None and player.is_premium
        ),
    )


async def show_tops(event, services, mode: str = "rating"):
    """Show one users-top screen."""

    try:
        entries = await services.list_top_players(mode)
    except ValidationError as error:
        return await send_or_edit(
            event,
            f"🏆 <b>Топы</b>\n<i>{escape(str(error))}</i>",
            tops_markup("rating"),
        )
    await send_or_edit(event, tops_text(entries, mode), tops_markup(mode))


async def show_profile_backgrounds(event, services, player_id: int):
    """Show the player's profile-background collection."""

    player = await services.get_or_create_player(player_id)
    backgrounds = await services.list_player_profile_backgrounds(player_id)
    await send_or_edit(
        event,
        profile_backgrounds_text(backgrounds, player.selected_profile_background_id),
        profile_backgrounds_markup([background.id for background in backgrounds]),
    )


async def show_admin(
    event: CallbackQuery | Message,
    services: TelegramServices,
    section: str = "dashboard",
    page: int = 1,
) -> None:
    """Show the admin dashboard or a section page."""

    counts = await services.admin_counts()
    templates = _templates(services)
    backgrounds: dict[int, ProfileBackgroundTemplate] = _profile_backgrounds(services)
    cards = list(services.card_templates.items.values())
    profile_backgrounds = list(services.profile_backgrounds.items.values())
    banners = list(services.banners.items.values())
    shop_items = list(services.shop.items.values())
    standard_cards = await services.list_standard_cards()
    universes = await services.list_universes()

    match section:
        case "cards":
            text, markup = (
                admin_text(counts, "cards") + "\n\n" + admin_cards_text(cards),
                admin_markup("cards"),
            )

        case "profile_backgrounds":
            text, markup = (
                admin_text(counts, "profile_backgrounds")
                + "\n\n"
                + admin_profile_backgrounds_text(profile_backgrounds),
                admin_markup("profile_backgrounds"),
            )

        case "players":
            text, markup = (
                admin_text(counts, "players")
                + "\n\n<i>Через этот раздел можно начислять Creator Points, задавать титул и переключать premium-статус игроку по ID.</i>",
                admin_markup("players"),
            )

        case "banners":
            if banners:
                banner = next(
                    (item for item in banners if item.is_available()), banners[0]
                )
                text = (
                    admin_text(counts, "banners")
                    + "\n\n"
                    + banner_text(banner, banner.can_edit())
                    + "\n\n"
                    + banner_pool_text(banner, templates, backgrounds)
                )
                markup = admin_banner_markup(
                    banner.id, banner.can_edit(), banner.is_available()
                )
            else:
                text, markup = (
                    admin_text(counts, "banners")
                    + "\n\n<i>Пока баннеров нет. Самое время создать первый ✨</i>",
                    admin_markup("banners"),
                )

        case "shop":
            text, markup = (
                admin_text(counts, "shop") + "\n\n" + shop_text(shop_items),
                admin_markup("shop"),
            )

        case "standard_cards":
            text, markup = (
                admin_text(counts, "standard_cards")
                + "\n\n"
                + standard_cards_text(standard_cards, templates),
                admin_markup("standard_cards"),
            )

        case "universes":
            text, markup = (
                admin_text(counts, "universes") + "\n\n" + universes_text(universes),
                admin_markup("universes"),
            )

        case "battle_pass":
            season = await services.active_battle_pass()
            seasons = await services.list_battle_pass_seasons()
            text, markup = (
                admin_text(counts, "battle_pass")
                + "\n\n"
                + battle_pass_admin_text(season)
                + "\n\n"
                + battle_pass_seasons_text(seasons),
                admin_markup("battle_pass"),
            )

        case "premium_battle_pass":
            season = await services.active_premium_battle_pass()
            seasons = await services.list_premium_battle_pass_seasons()
            text, markup = (
                admin_text(counts, "premium_battle_pass")
                + "\n\n"
                + premium_battle_pass_admin_text(season)
                + "\n\n"
                + premium_battle_pass_seasons_text(seasons),
                admin_markup("premium_battle_pass"),
            )

        case "free_rewards":
            text, markup = (
                admin_text(counts, "free_rewards")
                + "\n\n"
                + free_rewards_admin_text(services.free_reward_settings()),
                admin_markup("free_rewards"),
            )

        case "dashboard":
            text, markup = admin_text(counts, "dashboard"), admin_markup("dashboard")

        case _:
            if section in {
                ipen := "ideas_pending",
                ipub := "ideas_public",
                icol := "ideas_collection",
                irej := "ideas_rejected",
            }:
                status = {
                    ipen: IdeaStatus.PENDING,
                    ipub: IdeaStatus.PUBLISHED,
                    icol: IdeaStatus.COLLECTED,
                    irej: IdeaStatus.REJECTED,
                }[section]
                ideas, has_prev, has_next = await services.list_ideas(
                    status=status, page=page
                )
                text, markup = (
                    admin_text(counts, section)
                    + "\n\n"
                    + ideas_text(
                        ideas,
                        page,
                        title="💡 <b>Список идей</b>",
                        empty_text="В этом разделе пока пусто.",
                    ),
                    admin_ideas_markup(
                        ideas,
                        page,
                        scope=section.replace("ideas_", "admin_"),
                        has_prev=has_prev,
                        has_next=has_next,
                    ),
                )

    try:
        await send_or_edit(event, text, markup)
    except NameError:
        return


__all__ = [
    "show_admin",
    "show_admin_idea_detail",
    "show_banners",
    "show_battle",
    "show_battle_pass",
    "show_battle_round",
    "show_battle_switch",
    "show_cards",
    "show_card_detail",
    "show_clan",
    "show_collection",
    "show_deck_builder",
    "show_free_rewards",
    "show_gallery",
    "show_home",
    "show_idea_collection",
    "show_idea_detail",
    "show_ideas",
    "show_premium_battle_pass",
    "show_profile",
    "show_profile_backgrounds",
    "show_shop",
    "show_tops",
]
