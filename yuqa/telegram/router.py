"""Router tree and handlers for the Telegram bot."""

from html import escape
from datetime import datetime, timezone

from yuqa.cards.domain.entities import Ability, AbilityEffect
from yuqa.quests.domain.entities import QuestReward
from yuqa.shared.errors import (
    BattleRuleViolationError,
    DomainError,
    EntityNotFoundError,
    ValidationError,
)
from yuqa.shared.enums import (
    AbilityStat,
    AbilityTarget,
    BannerType,
    CardClass,
    IdeaStatus,
    ProfileBackgroundRarity,
    Rarity,
    ResourceType,
)
from yuqa.shared.value_objects.stat_block import StatBlock
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
    CallbackQuery,
    Command,
    CommandObject,
    CommandStart,
    FSMContext,
    Message,
    Router,
)
from yuqa.telegram.reply import (
    send_card_preview,
    send_alert,
    send_media_preview,
    send_notice,
    send_or_edit,
)
from yuqa.telegram.services import TelegramServices
from yuqa.telegram.states import (
    BannerCreate,
    BannerRewardCreate,
    BattlePassLevelCreate,
    BattlePassSeasonCreate,
    BattlePassSeasonDelete,
    AdminPlayerEdit,
    CardCreate,
    CardDelete,
    ClanCreation,
    FreeRewardsEdit,
    IdeaProposal,
    ProfileBackgroundCreate,
    ProfileEdit,
    ShopCreate,
    ShopDelete,
    StandardCardsEdit,
    PlayerDelete,
    UniverseCreate,
    UniverseDelete,
)
from yuqa.telegram.texts import (
    ability_effects_guide,
    admin_cards_text,
    admin_profile_backgrounds_text,
    admin_text,
    banner_pool_text,
    banner_text,
    battle_pass_admin_text,
    battle_pass_level_wizard_text,
    battle_pass_seasons_text,
    battle_pass_season_wizard_text,
    battle_pass_text,
    premium_battle_pass_admin_text,
    premium_battle_pass_seasons_text,
    premium_battle_pass_text,
    battle_started_text,
    collection_text,
    battle_text,
    banner_wizard_text,
    card_level_up_confirm_text,
    cards_text,
    card_template_text,
    card_text,
    card_wizard_text,
    clan_text,
    deck_builder_text,
    free_rewards_admin_text,
    free_rewards_edit_guide,
    free_rewards_text,
    gallery_text,
    idea_text,
    ideas_text,
    idea_wizard_text,
    image_input_guide,
    menu_text,
    profile_background_text,
    profile_background_wizard_text,
    profile_backgrounds_text,
    profile_text,
    battle_status_text,
    shop_text,
    shop_wizard_text,
    standard_cards_text,
    tops_text,
    universes_text,
)
from yuqa.telegram.ui import (
    admin_banner_markup,
    admin_idea_detail_markup,
    admin_ideas_markup,
    admin_choice_markup,
    admin_markup,
    admin_wizard_markup,
    banner_markup,
    battle_markup,
    battle_actions_markup,
    battle_switch_markup,
    battle_pass_markup,
    collection_markup,
    COLLECTION_MENU_BUTTON,
    premium_battle_pass_markup,
    card_level_up_confirm_markup,
    card_markup,
    cards_markup,
    clan_markup,
    deck_builder_markup,
    free_rewards_markup,
    gallery_markup,
    idea_detail_markup,
    ideas_markup,
    main_menu_markup,
    MAIN_MENU_BUTTON_TEXTS,
    profile_background_markup,
    profile_backgrounds_markup,
    profile_markup,
    shop_markup,
    tops_markup,
)


def _parse_int(text: str, label: str, *, positive: bool = False) -> int:
    """Parse an integer with friendly validation errors."""

    try:
        value = int((text or "").strip())
    except ValueError as error:
        raise ValidationError(f"{label} must be an integer") from error
    if positive and value <= 0:
        raise ValidationError(f"{label} must be > 0")
    if not positive and value < 0:
        raise ValidationError(f"{label} must be >= 0")
    return value


def _parse_dt(text: str) -> datetime | None:
    """Parse ISO datetime or a blank marker."""

    text = (text or "").strip()
    if text in {"", "-", "none", "нет"}:
        return None
    value = datetime.fromisoformat(text)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _normalize_token(value: str) -> str:
    """Normalize a free-form token for enum lookup."""

    return "".join(ch for ch in value.lower() if ch.isalnum())


def _parse_effects(text: str) -> tuple[AbilityEffect, ...]:
    """Parse a readable list of ability effects."""

    text = (text or "").strip()
    if text in {"", "-", "none", "нет"}:
        return ()
    targets = {
        "self": AbilityTarget.SELF,
        "teammatesdeck": AbilityTarget.TEAMMATES_DECK,
        "teammates": AbilityTarget.TEAMMATES_DECK,
        "team": AbilityTarget.TEAMMATES_DECK,
        "allydeck": AbilityTarget.TEAMMATES_DECK,
        "opponentsdeck": AbilityTarget.OPPONENTS_DECK,
        "opponentdeck": AbilityTarget.OPPONENTS_DECK,
        "enemydeck": AbilityTarget.OPPONENTS_DECK,
        "opponent": AbilityTarget.OPPONENTS_DECK,
        "enemy": AbilityTarget.OPPONENTS_DECK,
    }
    stats = {
        "damage": AbilityStat.DAMAGE,
        "health": AbilityStat.HEALTH,
        "defense": AbilityStat.DEFENSE,
    }
    effects = []
    for chunk in text.replace("\n", ";").split(";"):
        chunk = chunk.strip().lstrip("•*- ")
        if not chunk or chunk in {"-", "none", "нет"}:
            continue
        parts = [part.strip() for part in chunk.split(":")]
        if len(parts) != 4:
            raise ValidationError(
                f"effect must have 4 parts: target:stat:duration:value, got '{chunk}'"
            )
        target_raw, stat_raw, duration_raw, value_raw = parts
        try:
            target = targets[_normalize_token(target_raw)]
        except KeyError as error:
            raise ValidationError(f"unknown target '{target_raw}'") from error
        try:
            stat = stats[_normalize_token(stat_raw)]
        except KeyError as error:
            raise ValidationError(f"unknown stat '{stat_raw}'") from error
        duration = _parse_int(duration_raw, "duration")
        try:
            value = int(value_raw)
        except ValueError as error:
            raise ValidationError("value must be an integer") from error
        if value == 0:
            raise ValidationError("value must not be 0")
        effects.append(AbilityEffect(target, stat, duration, value))
    return tuple(effects)


def _parse_reward_bundle(text: str) -> QuestReward:
    """Parse a simple battle pass reward bundle from three integers."""

    values = [part for part in (text or "").replace(",", " ").split() if part]
    if len(values) != 3:
        raise ValidationError("reward must contain three integers: coins crystals orbs")
    coins, crystals, orbs = (_parse_int(value, "reward value") for value in values)
    return QuestReward(coins=coins, crystals=crystals, orbs=orbs, battle_pass_points=0)


def _parse_mapping(
    text: str, allowed: tuple[str, ...], label: str, *, positive: bool = False
) -> dict[str, int]:
    """Parse `key=value` pairs for admin-edited settings."""

    raw_parts = [
        part.strip() for part in (text or "").replace(",", " ").split() if part.strip()
    ]
    if len(raw_parts) != len(allowed):
        raise ValidationError(f"{label} must include all values: {' '.join(allowed)}")
    result: dict[str, int] = {}
    for part in raw_parts:
        if "=" in part:
            key, value = part.split("=", 1)
        elif ":" in part:
            key, value = part.split(":", 1)
        else:
            raise ValidationError(f"{label} must use key=value pairs")
        normalized = key.strip().lower()
        if normalized not in allowed:
            raise ValidationError(f"unknown key '{key}' in {label}")
        if normalized in result:
            raise ValidationError(f"duplicate key '{key}' in {label}")
        result[normalized] = _parse_int(value.strip(), normalized, positive=positive)
    missing = [key for key in allowed if key not in result]
    if missing:
        raise ValidationError(f"{label} is missing: {' '.join(missing)}")
    return result


def _card_image_key(template) -> str:
    """Return a photo key for a card template."""

    return template.image.storage_key


def _templates(services) -> dict[int, object]:
    """Return a template lookup map."""

    return {
        template.id: template for template in services.card_templates.items.values()
    }


def _paginate_items(items: list[object], page: int, size: int = 10):
    """Return a slice of items together with pagination flags."""

    if not items:
        return [], 1, False, False, 1
    total_pages = max(1, (len(items) + size - 1) // size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * size
    end = start + size
    return items[start:end], page, page > 1, page < total_pages, total_pages


def _profile_backgrounds(services) -> dict[int, object]:
    """Return a profile-background lookup map."""

    return {
        background.id: background
        for background in services.profile_backgrounds.items.values()
    }


def _admin_idea_scope_to_section(scope: str) -> str:
    """Map an idea callback scope to one admin section key."""

    mapping = {
        "admin_pending": "ideas_pending",
        "admin_public": "ideas_public",
        "admin_collection": "ideas_collection",
        "admin_rejected": "ideas_rejected",
    }
    return mapping.get(scope, "ideas_pending")


def _media_from_message(message: Message) -> tuple[str | None, str]:
    """Return a Telegram file id or URL together with a best-effort content type."""
    photo = getattr(message, "photo", None) or []
    if photo:
        return getattr(photo[-1], "file_id", None), "image/jpeg"
    video = getattr(message, "video", None)
    if video is not None:
        return getattr(video, "file_id", None), getattr(video, "mime_type", "video/mp4")
    document = getattr(message, "document", None)
    if document is not None:
        return getattr(document, "file_id", None), getattr(
            document, "mime_type", "application/octet-stream"
        )
    text = (message.text or "").strip()
    if text.lower().endswith((".mp4", ".mov", ".webm")):
        return text or None, "video/mp4"
    return text or None, "image/png"


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

    cards = sorted(
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
    summary = services.battle_round_summary(battle, player_id)
    text = battle_status_text(
        battle,
        player_id,
        opponent_action_points=summary.opponent_action_points,
        available_action_points=summary.available_action_points,
        attack_count=summary.attack_count,
        block_count=summary.block_count,
        bonus_count=summary.bonus_count,
        ability_used=summary.ability_used,
    )
    if prefix is not None:
        text = prefix + "\n\n" + text
    markup = None
    if battle.status.value == "active" and summary.available_action_points > 0:
        markup = battle_actions_markup(
            can_switch=summary.can_switch,
            ability_cost=summary.ability_cost,
            can_use_ability=(
                not summary.ability_used
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
    if not cards:
        return await show_battle_round(event, services, player_id, battle=battle)
    summary = services.battle_round_summary(battle, player_id)
    if battle.status.value != "active":
        return await show_battle_round(event, services, player_id, battle=battle)
    await send_or_edit(
        event,
        battle_status_text(
            battle,
            player_id,
            opponent_action_points=summary.opponent_action_points,
            available_action_points=summary.available_action_points,
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
    backgrounds = _profile_backgrounds(services)
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
                banner = banners[0]
                text = (
                    admin_text(counts, "banners")
                    + "\n\n"
                    + banner_text(banner, banner.can_edit())
                    + "\n\n"
                    + banner_pool_text(banner, templates, backgrounds)
                )
                markup = admin_banner_markup(banner.id, banner.can_edit())
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


# Clan flow -----------------------------------------------------------------


async def start_clan_creation(message: Message, state: FSMContext):
    """Enter the clan creation flow."""

    await state.clear()
    await state.set_state(ClanCreation.name)
    await message.answer("🏰 <b>Создание клана</b>\nНапиши название клана ✍️")


async def capture_clan_name(message: Message, state: FSMContext):
    """Store the clan name and ask for an icon."""

    if not message.text:
        return await message.answer("Напиши название клана текстом 🙂")
    await state.update_data(name=message.text.strip())
    await state.set_state(ClanCreation.icon)
    await message.answer(
        "А теперь выбери иконку: например <code>🐺</code> или <code>🔥</code>"
    )


async def capture_clan_icon(message: Message, services, state: FSMContext):
    """Create the clan after collecting all fields."""

    data = await state.get_data()
    if not data.get("name"):
        await state.set_state(ClanCreation.name)
        return await message.answer("Сначала напиши название клана 🙂")
    try:
        clan = await services.create_clan(
            message.from_user.id if message.from_user else 0,
            data["name"],
            (message.text or "🐺").strip()[:8],
        )
    except (DomainError, ValidationError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    player = await services.get_or_create_player(clan.owner_player_id)
    await message.answer(text=clan_text(clan, player), reply_markup=clan_markup(True))


# Battle pass wizard -------------------------------------------------------


async def start_battle_pass_level_create(
    message: Message, state: FSMContext, *, premium: bool = False
):
    """Open the Battle Pass level wizard from the first step."""

    await state.clear()
    await state.set_state(BattlePassLevelCreate.level_number)
    mode = "premium" if premium else "standard"
    await state.update_data(battle_pass_mode=mode)
    await message.answer(
        battle_pass_level_wizard_text("уровень", {}),
        reply_markup=admin_wizard_markup(
            "premium_battle_pass" if premium else "battle_pass"
        ),
    )


async def capture_battle_pass_level_number(message: Message, state: FSMContext):
    """Store the level number and move to the points step."""

    data = await state.get_data()
    back_section = (
        "premium_battle_pass"
        if data.get("battle_pass_mode") == "premium"
        else "battle_pass"
    )
    level_number = _parse_int(message.text or "0", "level number", positive=True)
    await state.update_data(level_number=level_number)
    await state.set_state(BattlePassLevelCreate.required_points)
    await message.answer(
        battle_pass_level_wizard_text("очки", await state.get_data()),
        reply_markup=admin_wizard_markup(back_section),
    )


async def capture_battle_pass_required_points(message: Message, state: FSMContext):
    """Store the required points and move to the reward step."""

    data = await state.get_data()
    back_section = (
        "premium_battle_pass"
        if data.get("battle_pass_mode") == "premium"
        else "battle_pass"
    )
    required_points = _parse_int(message.text or "0", "required points", positive=True)
    await state.update_data(required_points=required_points)
    await state.set_state(BattlePassLevelCreate.reward)
    await message.answer(
        battle_pass_level_wizard_text("награда", await state.get_data()),
        reply_markup=admin_wizard_markup(back_section),
    )


async def capture_battle_pass_reward(message: Message, services, state: FSMContext):
    """Parse the reward bundle and save the level in the active season."""

    data = await state.get_data()
    try:
        reward = _parse_reward_bundle(message.text or "")
        if data.get("battle_pass_mode") == "premium":
            await services.add_premium_battle_pass_level(
                data["level_number"],
                data["required_points"],
                reward,
            )
        else:
            await services.add_battle_pass_level(
                data["level_number"],
                data["required_points"],
                reward,
            )
    except (DomainError, ValidationError, KeyError, ValueError) as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    await state.clear()
    is_premium = data.get("battle_pass_mode") == "premium"
    await message.answer(
        "✅ Уровень Premium Battle Pass сохранён!"
        if is_premium
        else "✅ Уровень Battle Pass сохранён!"
    )
    await show_admin(
        message, services, "premium_battle_pass" if is_premium else "battle_pass"
    )


async def start_battle_pass_season_create(
    message: Message, state: FSMContext, *, premium: bool = False
):
    """Open the Battle Pass season wizard from the first step."""

    await state.clear()
    await state.set_state(BattlePassSeasonCreate.name)
    await state.update_data(battle_pass_mode="premium" if premium else "standard")
    await message.answer(
        battle_pass_season_wizard_text("название", {}),
        reply_markup=admin_wizard_markup(
            "premium_battle_pass" if premium else "battle_pass"
        ),
    )


async def capture_battle_pass_season_name(message: Message, state: FSMContext):
    """Store the season name and ask for the start date."""

    data = await state.get_data()
    back_section = (
        "premium_battle_pass"
        if data.get("battle_pass_mode") == "premium"
        else "battle_pass"
    )
    if not message.text:
        return await message.answer("Напиши название текстом 🙂")
    await state.update_data(name=message.text.strip())
    await state.set_state(BattlePassSeasonCreate.start_at)
    await message.answer(
        battle_pass_season_wizard_text("старт", await state.get_data()),
        reply_markup=admin_wizard_markup(back_section),
    )


async def capture_battle_pass_season_start_at(message: Message, state: FSMContext):
    """Store the start date and ask for the end date."""

    data = await state.get_data()
    back_section = (
        "premium_battle_pass"
        if data.get("battle_pass_mode") == "premium"
        else "battle_pass"
    )
    start_at = _parse_dt(message.text or "")
    if start_at is None:
        return await message.answer("Введи дату старта в ISO-формате 🙂")
    await state.update_data(start_at=start_at)
    await state.set_state(BattlePassSeasonCreate.end_at)
    await message.answer(
        battle_pass_season_wizard_text("финиш", await state.get_data()),
        reply_markup=admin_wizard_markup(back_section),
    )


async def capture_battle_pass_season_end_at(
    message: Message, services, state: FSMContext
):
    """Create a new battle pass season with the collected dates."""

    data = await state.get_data()
    end_at = _parse_dt(message.text or "")
    if end_at is None:
        return await message.answer("Введи дату финиша в ISO-формате 🙂")
    try:
        if data.get("battle_pass_mode") == "premium":
            await services.create_premium_battle_pass_season(
                data["name"], data["start_at"], end_at
            )
        else:
            await services.create_battle_pass_season(
                data["name"], data["start_at"], end_at
            )
    except (DomainError, ValidationError, KeyError, ValueError) as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    await state.clear()
    is_premium = data.get("battle_pass_mode") == "premium"
    await message.answer(
        "✅ Premium Battle Pass создан!" if is_premium else "✅ Battle Pass создан!",
        reply_markup=admin_wizard_markup(
            "premium_battle_pass" if is_premium else "battle_pass"
        ),
    )
    await show_admin(
        message, services, "premium_battle_pass" if is_premium else "battle_pass"
    )


async def start_battle_pass_season_delete(
    message: Message, state: FSMContext, *, premium: bool = False
):
    """Ask for the ended season id to delete."""

    await state.clear()
    await state.set_state(BattlePassSeasonDelete.season_id)
    await state.update_data(battle_pass_mode="premium" if premium else "standard")
    await message.answer(
        (
            "Введи ID завершённого Premium Battle Pass для удаления 🗑️"
            if premium
            else "Введи ID завершённого Battle Pass для удаления 🗑️"
        ),
        reply_markup=admin_wizard_markup(
            "premium_battle_pass" if premium else "battle_pass"
        ),
    )


async def capture_battle_pass_season_delete(
    message: Message, services, state: FSMContext
):
    """Delete an ended battle pass season."""

    data = await state.get_data()
    try:
        season_id = _parse_int(message.text or "0", "season id", positive=True)
        if data.get("battle_pass_mode") == "premium":
            await services.delete_premium_battle_pass_season(season_id)
        else:
            await services.delete_battle_pass_season(season_id)
    except (DomainError, ValidationError) as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    await state.clear()
    await show_admin(
        message,
        services,
        "premium_battle_pass"
        if data.get("battle_pass_mode") == "premium"
        else "battle_pass",
    )


# Free rewards admin ------------------------------------------------------


async def start_free_rewards_edit(message: Message, state: FSMContext, mode: str):
    """Open one of the free reward config editors."""

    await state.clear()
    await state.set_state(FreeRewardsEdit.value)
    await state.update_data(mode=mode)
    await message.answer(
        free_rewards_edit_guide(mode),
        reply_markup=admin_wizard_markup("free_rewards"),
    )


async def capture_free_rewards_edit(message: Message, services, state: FSMContext):
    """Persist one free reward config block."""

    data = await state.get_data()
    mode = data.get("mode")
    try:
        if mode == "card_weights":
            parsed = _parse_mapping(
                message.text or "",
                ("common", "rare", "epic", "mythic", "legendary", "godly"),
                "card weights",
            )
            await services.set_free_card_weights(
                {Rarity(key): value for key, value in parsed.items()}
            )
        elif mode == "resource_weights":
            parsed = _parse_mapping(
                message.text or "",
                ("coins", "crystals", "orbs"),
                "resource weights",
            )
            await services.set_free_resource_weights(
                {ResourceType(key): value for key, value in parsed.items()}
            )
        elif mode == "resource_values":
            parsed = _parse_mapping(
                message.text or "",
                ("coins", "crystals", "orbs"),
                "resource values",
                positive=True,
            )
            await services.set_free_resource_values(
                {ResourceType(key): value for key, value in parsed.items()}
            )
        else:
            raise ValidationError("unknown free rewards edit mode")
    except (DomainError, ValidationError, ValueError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    await show_admin(message, services, "free_rewards")


# Ideas -------------------------------------------------------------------


async def start_idea_proposal(message: Message, state: FSMContext):
    """Open the player idea proposal wizard."""

    await state.clear()
    await state.set_state(IdeaProposal.title)
    await message.answer(idea_wizard_text("название", {}))


async def capture_idea_title(message: Message, state: FSMContext):
    """Store the idea title and ask for a description."""

    if not message.text:
        return await message.answer("Напиши название идеи текстом 🙂")
    await state.update_data(title=message.text.strip())
    await state.set_state(IdeaProposal.description)
    await message.answer(idea_wizard_text("описание", await state.get_data()))


async def capture_idea_description(message: Message, services, state: FSMContext):
    """Persist the proposal and return the player to the ideas page."""

    if not message.from_user:
        return
    data = await state.get_data()
    try:
        await services.propose_idea(
            message.from_user.id,
            data.get("title", ""),
            message.text or "",
        )
    except (DomainError, ValidationError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    await message.answer("✅ Идея отправлена на модерацию.")
    await show_ideas(message, services, message.from_user.id)


# Profile cosmetics --------------------------------------------------------


async def start_profile_nickname_edit(message: Message, state: FSMContext):
    """Open nickname editing for the current player."""

    await state.clear()
    await state.set_state(ProfileEdit.nickname)
    await message.answer(
        "🏷 <b>Никнейм</b>\nВведи уникальный ник или отправь <code>-</code>, чтобы очистить.",
    )


async def capture_profile_nickname(message: Message, services, state: FSMContext):
    """Persist the player's nickname."""

    if not message.from_user:
        return
    try:
        await services.set_player_nickname(message.from_user.id, message.text)
    except (DomainError, ValidationError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    await show_profile(message, services, message.from_user.id)


async def start_admin_player_edit(
    message: Message, state: FSMContext, mode: str
) -> Message:
    """Open the admin flow for player-specific cosmetics."""

    await state.clear()
    await state.set_state(AdminPlayerEdit.player_id)
    await state.update_data(mode=mode)
    if mode == "creator_points":
        return await message.answer(
            "🪄 <b>Creator Points</b>\nВведи ID игрока.",
            reply_markup=admin_wizard_markup("players"),
        )
    if mode == "premium_toggle":
        return await message.answer(
            "💎 <b>Премиум-статус</b>\nВведи ID игрока.",
            reply_markup=admin_wizard_markup("players"),
        )
    return await message.answer(
        "✨ <b>Титул игрока</b>\nВведи ID игрока.",
        reply_markup=admin_wizard_markup("players"),
    )


async def start_admin_player_delete(message: Message, state: FSMContext) -> Message:
    """Open the admin flow for deleting a player."""

    await state.clear()
    await state.set_state(PlayerDelete.player_id)
    return await message.answer(
        "🗑 <b>Удаление игрока</b>\nВведи ID игрока, которого нужно удалить.",
        reply_markup=admin_wizard_markup("players"),
    )


async def capture_admin_player_id(
    message: Message, services: TelegramServices, state: FSMContext
) -> Message:
    """Store the target player id and ask for the value."""

    player_id = _parse_int(message.text or "0", "player id", positive=True)
    data: dict[str, object] = await state.get_data()
    await state.update_data(player_id=player_id)
    if data.get("mode") == "premium_toggle":
        player = await services.get_player(player_id)
        if player is None:
            await state.clear()
            return await message.answer("❌ player not found")
        await state.set_state(AdminPlayerEdit.value)
        return await message.answer(
            f"Текущий premium-статус игрока <code>{player_id}</code>: "
            f"<code>{'yes' if player.is_premium else 'no'}</code>\n"
            "<i>Нажми «Переключить», чтобы сменить значение, или «Отмена».</i>",
            reply_markup=admin_choice_markup(
                "players_premium_toggle_confirm",
                [("🔁 Переключить", "yes"), ("❌ Отмена", "no")],
                "players",
            ),
        )
    await state.set_state(AdminPlayerEdit.value)
    if data.get("mode") == "creator_points":
        return await message.answer(
            "Введи, сколько Creator Points начислить.",
            reply_markup=admin_wizard_markup("players"),
        )
    return await message.answer(
        "Введи титул для игрока.",
        reply_markup=admin_wizard_markup("players"),
    )


async def capture_admin_player_delete(
    message: Message, services: TelegramServices, state: FSMContext
) -> Message | None:
    """Delete the selected player."""

    player_id = _parse_int(message.text or "0", "player id", positive=True)
    try:
        player = await services.delete_player(player_id)
    except (DomainError, ValidationError) as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    await state.clear()
    await message.answer(f"✅ Игрок <code>{player.telegram_id}</code> удалён.")
    await show_admin(message, services, "players")


async def capture_admin_player_value(
    message: Message, services: TelegramServices, state: FSMContext
) -> Message | None:
    """Apply the admin edit to the selected player."""

    data: dict[str, object] = await state.get_data()
    player_id = data.get("player_id")
    if not isinstance(player_id, int):
        await state.clear()
        return await message.answer("❌ player id is missing")
    mode = data.get("mode")
    try:
        if mode == "creator_points":
            player = await services.add_creator_points(
                player_id,
                _parse_int(message.text or "0", "creator points", positive=True),
            )
            notice = (
                f"✅ Игроку <code>{player.telegram_id}</code> начислено "
                f"<code>{player.creator_points}</code> Creator Points."
            )
        elif mode == "premium_toggle":
            return await message.answer(
                "Используй кнопки «Переключить» или «Отмена» под сообщением."
            )
        else:
            player = await services.set_player_title(player_id, message.text)
            notice = f"✅ Титул игрока <code>{player.telegram_id}</code> обновлён."
    except (DomainError, ValidationError, ValueError) as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    await state.clear()
    await message.answer(notice)
    await show_admin(message, services, "players")


# Universe wizard -----------------------------------------------------------


async def start_universe_create(message: Message, state: FSMContext):
    """Open the universe creation wizard from the first step."""

    await state.clear()
    await state.set_state(UniverseCreate.value)
    await message.answer(
        "Введи название новой вселенной ✍️",
        reply_markup=admin_wizard_markup("universes"),
    )


async def start_universe_delete(message: Message, state: FSMContext):
    """Open the universe deletion wizard from the first step."""

    await state.clear()
    await state.set_state(UniverseDelete.value)
    await message.answer(
        "Введи название вселенной для удаления ✍️",
        reply_markup=admin_wizard_markup("universes"),
    )


async def capture_universe_add(message: Message, services, state: FSMContext):
    """Add a new universe to the local catalog."""

    if not message.text:
        return await message.answer("Введи название вселенной текстом 🙂")
    await services.add_universe(message.text)
    await state.clear()
    await show_admin(message, services, "universes")


async def capture_universe_remove(message: Message, services, state: FSMContext):
    """Remove a universe from the local catalog."""

    if not message.text:
        return await message.answer("Введи название вселенной текстом 🙂")
    await services.remove_universe(message.text)
    await state.clear()
    await show_admin(message, services, "universes")


# Card creation -------------------------------------------------------------


async def start_card_create(message: Message, state: FSMContext):
    """Start the card creation wizard."""

    await state.clear()
    await state.set_state(CardCreate.name)
    await message.answer(
        card_wizard_text("название", {}), reply_markup=admin_wizard_markup("cards")
    )


async def card_name(message: Message, state: FSMContext, services=None):
    """Store the card name and ask for a universe."""

    if not message.text:
        return await message.answer("Напиши название текстом 🙂")
    await state.update_data(name=message.text.strip())
    await state.set_state(CardCreate.universe_value)
    if services is not None:
        universes = await services.list_universes()
        return await message.answer(
            "🌌 <b>Выбери или введи вселенную</b>\n"
            + "\n".join(f"• <code>{item}</code>" for item in universes),
            reply_markup=admin_choice_markup(
                "card_universe_pick",
                [(item, item) for item in universes] + [("➕ Новая", "__new__")],
                "cards",
            ),
        )
    await message.answer("Введите вселенную текстом или нажмите ⬅️ Назад")


async def card_universe_value(message: Message, state: FSMContext):
    """Store a universe name and ask for rarity."""

    if not message.text:
        return await message.answer("Напиши название вселенной текстом 🙂")
    await state.update_data(universe=message.text.strip())
    await state.set_state(CardCreate.rarity)
    await message.answer(
        card_wizard_text("редкость", await state.get_data()),
        reply_markup=admin_choice_markup(
            "card_rarity", [(item.value, item.value) for item in Rarity], "cards"
        ),
    )


async def card_image(message: Message, state: FSMContext):
    """Store the image reference and ask for a class."""

    image_key, _content_type = _media_from_message(message)
    if not image_key:
        return await message.answer("Пришли фото, документ, ссылку или file_id 🖼️")
    await state.update_data(image=image_key)
    await state.set_state(CardCreate.card_class)
    await message.answer(
        card_wizard_text("класс", await state.get_data()),
        reply_markup=admin_choice_markup(
            "card_class", [(item.value, item.value) for item in CardClass], "cards"
        ),
    )


async def card_base_stats(message: Message, state: FSMContext):
    """Store base stats and ask for ascended stats."""

    if not message.text:
        return await message.answer("Напиши три числа через пробел 🙂")
    damage, health, defense = [int(value) for value in message.text.split()[:3]]
    await state.update_data(base_stats=(damage, health, defense))
    await state.set_state(CardCreate.ascended_stats)
    await message.answer("Теперь введи возвышенные статы: урон здоровье защита ✍️")


async def card_ascended_stats(message: Message, state: FSMContext):
    """Store ascended stats and ask for ability cost."""

    if not message.text:
        return await message.answer("Напиши три числа через пробел 🙂")
    damage, health, defense = [int(value) for value in message.text.split()[:3]]
    await state.update_data(ascended_stats=(damage, health, defense))
    await state.set_state(CardCreate.ability_cost)
    await message.answer("Сколько стоит способность в очках?")


async def card_ability_cost(message: Message, state: FSMContext):
    """Store ability cost and ask for cooldown."""

    await state.update_data(
        ability_cost=_parse_int(message.text or "0", "ability cost")
    )
    await state.set_state(CardCreate.ability_cooldown)
    await message.answer("Какой у неё кулдаун? 🔁")


async def card_ability_cooldown(message: Message, state: FSMContext):
    """Store cooldown and ask for effects."""

    await state.update_data(
        ability_cooldown=_parse_int(message.text or "0", "cooldown")
    )
    await state.set_state(CardCreate.ability_effects)
    await message.answer(ability_effects_guide())


async def card_ability_effects(message: Message, state: FSMContext):
    """Store base effects and ask for ascended effects."""

    await state.update_data(ability_effects=message.text or "")
    await state.set_state(CardCreate.ascended_effects)
    await message.answer(ability_effects_guide())


async def card_ascended_effects(message: Message, services, state: FSMContext):
    """Create the card template and finish the wizard."""

    data = await state.get_data()
    try:
        template = await services.create_card_template(
            name=data["name"],
            universe=data["universe"],
            rarity=Rarity(data["rarity"]),
            image_key=data["image"],
            card_class=CardClass(data["card_class"]),
            base_stats=StatBlock(*data["base_stats"]),
            ascended_stats=StatBlock(*data["ascended_stats"]),
            ability=Ability(
                data["ability_cost"],
                data["ability_cooldown"],
                _parse_effects(data.get("ability_effects", "")),
            ),
            ascended_ability=None
            if (message.text or "").strip() in {"", "-", "none", "нет"}
            else Ability(
                data["ability_cost"],
                data["ability_cooldown"],
                _parse_effects(message.text or ""),
            ),
        )
    except (DomainError, ValidationError, KeyError, ValueError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    await message.answer(
        f"✨ <b>Карта создана!</b>\n<code>{template.id}</code> — {template.name}"
    )
    await show_admin(message, services, "cards")


# Profile background creation ----------------------------------------------


async def start_profile_background_create(message: Message, state: FSMContext):
    """Start the profile-background creation wizard."""

    await state.clear()
    await state.set_state(ProfileBackgroundCreate.rarity)
    await message.answer(
        profile_background_wizard_text("редкость", {}),
        reply_markup=admin_choice_markup(
            "profile_background_rarity",
            [(item.value, item.value) for item in ProfileBackgroundRarity],
            "profile_backgrounds",
        ),
    )


async def profile_background_media(message: Message, services, state: FSMContext):
    """Create a profile background after the media step."""

    media_key, content_type = _media_from_message(message)
    if not media_key:
        return await message.answer(
            "Пришли фото, видео, документ, ссылку или file_id 🖼️"
        )
    data = await state.get_data()
    try:
        background = await services.create_profile_background(
            ProfileBackgroundRarity(data["rarity"]),
            media_key,
            content_type=content_type,
        )
    except (DomainError, ValidationError, KeyError, ValueError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    await message.answer(
        f"✨ <b>Фон профиля создан!</b>\n<code>{background.id}</code> · <code>{background.rarity.value}</code>"
    )
    await show_admin(message, services, "profile_backgrounds")


# Banner creation and banner rewards ---------------------------------------


async def start_banner_create(message: Message, state: FSMContext):
    """Start the banner creation wizard."""

    await state.clear()
    await state.set_state(BannerCreate.name)
    await message.answer(
        banner_wizard_text("название", {}), reply_markup=admin_wizard_markup("banners")
    )


async def banner_name(message: Message, state: FSMContext):
    """Store the banner name and ask for a type."""

    if not message.text:
        return await message.answer("Напиши название текстом 🙂")
    await state.update_data(name=message.text.strip())
    await state.set_state(BannerCreate.banner_type)
    await message.answer(
        banner_wizard_text("тип", await state.get_data()),
        reply_markup=admin_choice_markup(
            "banner_type", [(item.value, item.value) for item in BannerType], "banners"
        ),
    )


async def banner_start_at(message: Message, state: FSMContext):
    """Store the start date and ask for the end date."""

    await state.update_data(start_at=_parse_dt(message.text or ""))
    await state.set_state(BannerCreate.end_at)
    await message.answer(
        "Если нужен конец баннера — введи дату ISO. Иначе отправь <code>-</code>"
    )


async def banner_end_at(message: Message, services, state: FSMContext):
    """Create the banner and open the management screen."""

    data = await state.get_data()
    try:
        banner = await services.create_banner(
            data["name"],
            BannerType(data["banner_type"]),
            ResourceType(data["cost_resource"]),
            data["start_at"],
            _parse_dt(message.text or ""),
            True,
        )
    except (DomainError, ValidationError, KeyError, ValueError) as error:
        return await message.answer(f"❌ {error}")
    await state.clear()
    await message.answer(
        text=banner_text(banner, True),
        reply_markup=admin_banner_markup(banner.id, True),
    )


# Banner reward editing ----------------------------------------------------


async def _banner_reward_finish(
    message: Message, services, state: FSMContext, decision: str = "no"
):
    data = await state.get_data()
    try:
        if (
            data.get("reward_action") == "remove"
            and data.get("reward_kind") == "background"
        ):
            await services.remove_banner_reward_profile_background(
                data["banner_id"], data["template_id"]
            )
        elif data.get("reward_action") == "remove":
            await services.remove_banner_reward_card(
                data["banner_id"], data["template_id"]
            )
        elif data.get("reward_kind") == "background":
            await services.add_banner_reward_profile_background(
                data["banner_id"],
                data["template_id"],
                data["weight"],
                decision.lower() in {"yes", "да", "1"},
            )
        else:
            await services.add_banner_reward_card(
                data["banner_id"],
                data["template_id"],
                data["weight"],
                decision.lower() in {"yes", "да", "1"},
            )
    except (DomainError, ValidationError) as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    banner = await services.banners.get_by_id(data["banner_id"])
    await state.clear()
    if banner is None:
        return await message.answer("Баннер не найден")
    await message.answer(
        text=banner_text(banner, banner.can_edit())
        + "\n\n"
        + banner_pool_text(
            banner, _templates(services), _profile_backgrounds(services)
        ),
        reply_markup=admin_banner_markup(banner.id, banner.can_edit()),
    )


# Shop creation ------------------------------------------------------------


async def start_shop_create(message: Message, state: FSMContext):
    """Start the shop item wizard."""

    await state.clear()
    await state.set_state(ShopCreate.sell_resource)
    await message.answer(
        shop_wizard_text("что продаём", {}),
        reply_markup=admin_choice_markup(
            "shop_sell", [(item.value, item.value) for item in ResourceType], "shop"
        ),
    )


async def shop_price(message: Message, state: FSMContext):
    """Store the price and ask for quantity."""

    await state.update_data(
        price=_parse_int(message.text or "0", "price", positive=True)
    )
    await state.set_state(ShopCreate.quantity)
    await message.answer("Сколько товара выдаём? 📦")


async def shop_quantity(message: Message, state: FSMContext):
    """Store the quantity and ask whether the item is active."""

    await state.update_data(
        quantity=_parse_int(message.text or "0", "quantity", positive=True)
    )
    await state.set_state(ShopCreate.active)
    await message.answer(
        "Товар активен?",
        reply_markup=admin_choice_markup(
            "shop_active", [("Да", "yes"), ("Нет", "no")], "shop"
        ),
    )


# Standard cards -----------------------------------------------------------


async def standard_cards_add(message: Message, services, state: FSMContext):
    """Add one starter card template id."""

    template_id = _parse_int(message.text or "0", "template id", positive=True)
    try:
        await services.add_standard_card(template_id)
    except DomainError as error:
        await state.clear()
        return await message.answer(f"❌ {error}")
    await state.clear()
    await show_admin(message, services, "standard_cards")


async def standard_cards_remove(message: Message, services, state: FSMContext):
    """Remove one starter card template id."""

    template_id = _parse_int(message.text or "0", "template id", positive=True)
    await services.remove_standard_card(template_id)
    await state.clear()
    await show_admin(message, services, "standard_cards")


# Battle start and matchmaking --------------------------------------------


async def start_battle(message: Message, services, command: CommandObject):
    """Start a PvP battle from a text command."""

    if not message.from_user:
        return
    if not command.args:
        player = await services.get_or_create_player(message.from_user.id)
        return await message.answer(battle_text(player))
    try:
        battle = await services.start_battle(
            message.from_user.id, int(command.args.strip())
        )
    except ValueError as error:
        return await message.answer(f"❌ {error}")
    except (DomainError, ValidationError) as error:
        return await send_alert(message, f"⛔️ {error}")
    summary = services.battle_round_summary(battle, message.from_user.id)
    await message.answer(
        battle_started_text(battle)
        + "\n"
        + battle_status_text(
            battle,
            message.from_user.id,
            opponent_action_points=summary.opponent_action_points,
            available_action_points=summary.available_action_points,
            attack_count=summary.attack_count,
            block_count=summary.block_count,
            bonus_count=summary.bonus_count,
            ability_used=summary.ability_used,
        ),
        reply_markup=battle_actions_markup(
            can_switch=summary.can_switch,
            ability_cost=summary.ability_cost,
            can_use_ability=(
                not summary.ability_used
                and summary.available_action_points >= summary.ability_cost
            ),
        ),
    )


async def search_battle(event, services, player_id: int, bot=None):
    """Add a player to matchmaking and announce a battle when it is found."""

    try:
        battle = await services.search_battle(player_id)
    except (DomainError, ValidationError) as error:
        return await send_alert(event, f"⛔️ {error}")
    if battle is None:
        await send_or_edit(
            event,
            battle_text(await services.get_or_create_player(player_id), True),
            battle_markup(True),
        )
        return
    summary = services.battle_round_summary(battle, player_id)
    await send_or_edit(
        event,
        battle_started_text(battle)
        + "\n"
        + battle_status_text(
            battle,
            player_id,
            opponent_action_points=summary.opponent_action_points,
            available_action_points=summary.available_action_points,
            attack_count=summary.attack_count,
            block_count=summary.block_count,
            bonus_count=summary.bonus_count,
            ability_used=summary.ability_used,
        ),
        battle_actions_markup(
            can_switch=summary.can_switch,
            ability_cost=summary.ability_cost,
            can_use_ability=(
                not summary.ability_used
                and summary.available_action_points >= summary.ability_cost
            ),
        ),
    )
    if bot is not None and hasattr(bot, "send_message"):
        other_id = (
            battle.player_two_id
            if battle.player_one_id == player_id
            else battle.player_one_id
        )
        opponent_summary = services.battle_round_summary(battle, other_id)
        await bot.send_message(
            other_id,
            battle_started_text(battle)
            + "\n"
            + battle_status_text(
                battle,
                other_id,
                opponent_action_points=opponent_summary.opponent_action_points,
                available_action_points=opponent_summary.available_action_points,
                attack_count=opponent_summary.attack_count,
                block_count=opponent_summary.block_count,
                bonus_count=opponent_summary.bonus_count,
                ability_used=opponent_summary.ability_used,
            ),
            reply_markup=battle_actions_markup(
                can_switch=opponent_summary.can_switch,
                ability_cost=opponent_summary.ability_cost,
                can_use_ability=(
                    not opponent_summary.ability_used
                    and opponent_summary.available_action_points
                    >= opponent_summary.ability_cost
                ),
            ),
        )


async def cancel_battle_search(event, services, player_id: int):
    """Cancel matchmaking for the player."""

    await services.cancel_battle_search(player_id)
    await show_battle(event, services, player_id)


# Router ------------------------------------------------------------------


def build_router(services, settings) -> Router:
    """Build a router that closes over the runtime dependencies."""

    router = Router(name="yuqa")

    @router.message(CommandStart())
    async def start(message: Message):
        if message.from_user:
            await show_home(
                message,
                services,
                message.from_user.id,
                is_admin=message.from_user.id in settings.admin_ids,
            )

    @router.message(Command("menu"))
    async def open_menu(message: Message):
        if message.from_user:
            await show_home(
                message,
                services,
                message.from_user.id,
                is_admin=message.from_user.id in settings.admin_ids,
            )

    @router.message(Command("profile"))
    async def open_profile(message: Message, command: CommandObject):
        if not message.from_user:
            return
        if not command.args:
            return await show_profile(message, services, message.from_user.id)
        try:
            target_id = int(command.args.strip())
        except ValueError:
            return await message.answer(
                "Используй: <code>/profile &lt;player_id&gt;</code>"
            )
        await show_profile(
            message,
            services,
            target_id,
            viewer_player_id=message.from_user.id,
        )

    @router.message(Command("tops"))
    async def open_tops(message: Message):
        await show_tops(message, services)

    @router.message(Command("top"))
    async def open_top(message: Message):
        await show_tops(message, services)

    @router.message(Command("backgrounds"))
    async def open_backgrounds(message: Message):
        if message.from_user:
            await show_profile_backgrounds(message, services, message.from_user.id)

    @router.message(Command("ideas"))
    async def open_ideas(message: Message):
        if message.from_user:
            await show_ideas(message, services, message.from_user.id)

    @router.message(Command("my_ideas"))
    async def open_my_ideas(message: Message):
        if message.from_user:
            await show_idea_collection(message, services, message.from_user.id)

    @router.message(Command("battle"))
    async def open_battle(message: Message, command: CommandObject):
        await start_battle(message, services, command)

    @router.message(Command("deck"))
    async def open_deck(message: Message):
        if message.from_user:
            await show_deck_builder(message, services, message.from_user.id)

    @router.message(Command("clan_create"))
    async def open_clan_create(message: Message, state: FSMContext):
        await start_clan_creation(message, state)

    @router.message(ClanCreation.name)
    async def clan_name(message: Message, state: FSMContext):
        await capture_clan_name(message, state)

    @router.message(ClanCreation.icon)
    async def clan_icon(message: Message, state: FSMContext):
        await capture_clan_icon(message, services, state)

    @router.message(Command("admin"))
    async def open_admin(message: Message):
        if not message.from_user or message.from_user.id not in settings.admin_ids:
            return await message.answer("⛔ Доступ закрыт.")
        await show_admin(message, services)

    @router.message(Command("creator_points"))
    async def award_creator_points(message: Message, command: CommandObject):
        if not message.from_user or message.from_user.id not in settings.admin_ids:
            return await message.answer("⛔ Доступ закрыт.")
        args = (command.args or "").split()
        if len(args) != 2:
            return await message.answer(
                "Используй: <code>/creator_points &lt;player_id&gt; &lt;amount&gt;</code>"
            )
        try:
            player = await services.add_creator_points(int(args[0]), int(args[1]))
        except (ValueError, DomainError, ValidationError) as error:
            return await message.answer(f"❌ {error}")
        await message.answer(
            f"✅ Игроку <code>{player.telegram_id}</code> начислено "
            f"<code>{int(args[1])}</code> Creator Points."
        )

    @router.message(Command("cancel"))
    async def cancel_command(message: Message, state: FSMContext):
        await state.clear()
        if message.from_user and message.from_user.id in settings.admin_ids:
            return await show_admin(message, services)
        await message.answer("🧹 Сбросил текущий шаг.")

    @router.message(lambda message: message.text in MAIN_MENU_BUTTON_TEXTS)
    async def navigate_main_menu(message: Message, state: FSMContext):
        if not message.from_user or message.text is None:
            return
        await state.clear()
        text = message.text
        if text == "👤 Профиль":
            return await show_profile(message, services, message.from_user.id)
        if text == COLLECTION_MENU_BUTTON:
            return await show_collection(message, services, message.from_user.id)
        if text == "📖 Галерея":
            return await show_gallery(message, services)
        if text == "💡 Идеи":
            return await show_ideas(message, services, message.from_user.id)
        if text == "🏆 Топы":
            return await show_tops(message, services)
        if text == "⚔️ Бой":
            return await show_battle(message, services, message.from_user.id)
        if text == "🏁 Battle Pass":
            return await show_battle_pass(message, services, message.from_user.id)
        if text == "💎 Premium Battle Pass":
            return await show_premium_battle_pass(
                message, services, message.from_user.id
            )
        if text == "🏰 Клан":
            return await show_clan(message, services, message.from_user.id)
        if text == "🛒 Магазин":
            return await show_shop(message, services)
        if text == "🎁 Баннеры":
            return await show_banners(message, services)
        if text == "🛠 Админка":
            if message.from_user.id not in settings.admin_ids:
                return await message.answer("⛔ Доступ закрыт.")
            return await show_admin(message, services)

    @router.callback_query(MenuCallback.filter())
    async def navigate_menu(callback: CallbackQuery, callback_data: MenuCallback):
        if not callback.from_user:
            return await callback.answer()
        section = callback_data.section
        if section == "home":
            await show_home(
                callback,
                services,
                callback.from_user.id,
                is_admin=callback.from_user.id in settings.admin_ids,
            )
        elif section == "profile":
            await show_profile(callback, services, callback.from_user.id)
        elif section == "profile_backgrounds":
            await show_profile_backgrounds(callback, services, callback.from_user.id)
        elif section == "cards":
            await show_cards(callback, services, callback.from_user.id)
        elif section == "gallery":
            await show_gallery(callback, services)
        elif section == "ideas":
            await show_ideas(callback, services, callback.from_user.id)
        elif section == "idea_collection":
            await show_idea_collection(callback, services, callback.from_user.id)
        elif section == "tops":
            await show_tops(callback, services)
        elif section == "clan":
            await show_clan(callback, services, callback.from_user.id)
        elif section == "shop":
            await show_shop(callback, services)
        elif section == "banners":
            await show_banners(callback, services)
        elif section == "free_rewards":
            await show_free_rewards(callback, services, callback.from_user.id)
        elif section == "battle":
            await show_battle(callback, services, callback.from_user.id)
        elif section == "deck":
            await show_deck_builder(callback, services, callback.from_user.id)
        elif section == "battle_pass":
            await show_battle_pass(callback, services, callback.from_user.id)
        elif section == "premium_battle_pass":
            await show_premium_battle_pass(callback, services, callback.from_user.id)
        elif section == "admin" and callback.from_user.id in settings.admin_ids:
            await show_admin(callback, services)
        elif section == "admin":
            return await send_notice(callback, "⛔ Доступ закрыт.")
        else:
            return await callback.answer()

    @router.callback_query(TopCallback.filter())
    async def top_actions(callback: CallbackQuery, callback_data: TopCallback):
        await show_tops(callback, services, callback_data.mode)

    @router.callback_query(IdeaCallback.filter())
    async def idea_actions(
        callback: CallbackQuery, callback_data: IdeaCallback, state: FSMContext
    ):
        if not callback.from_user:
            return await callback.answer()
        action = callback_data.action
        page = max(callback_data.page, 1)
        scope = callback_data.scope
        if action == "propose":
            return await start_idea_proposal(callback.message, state)
        if action == "page":
            if scope == "collection":
                return await show_idea_collection(
                    callback, services, callback.from_user.id, page
                )
            return await show_ideas(callback, services, callback.from_user.id, page)
        if action == "open":
            try:
                if scope.startswith("admin_"):
                    if callback.from_user.id not in settings.admin_ids:
                        return await send_notice(callback, "⛔ Доступ закрыт.")
                    return await show_admin_idea_detail(
                        callback,
                        services,
                        callback_data.idea_id,
                        page=page,
                        scope=scope,
                    )
                return await show_idea_detail(
                    callback,
                    services,
                    callback_data.idea_id,
                    callback.from_user.id,
                    page=page,
                    scope=scope,
                )
            except (DomainError, ValidationError) as error:
                return await send_notice(callback, f"❌ {error}")
        if action in {"vote_up", "vote_down"}:
            try:
                await services.vote_for_idea(
                    callback.from_user.id,
                    callback_data.idea_id,
                    1 if action == "vote_up" else -1,
                )
            except (DomainError, ValidationError) as error:
                return await send_notice(callback, f"❌ {error}")
            return await show_idea_detail(
                callback,
                services,
                callback_data.idea_id,
                callback.from_user.id,
                page=page,
                scope=scope,
            )
        if callback.from_user.id not in settings.admin_ids:
            return await send_notice(callback, "⛔ Доступ закрыт.")
        if action == "admin_list":
            return await show_admin(
                callback,
                services,
                _admin_idea_scope_to_section(scope),
                page=page,
            )
        try:
            if action == "admin_publish":
                idea = await services.publish_idea(callback_data.idea_id)
                return await show_admin_idea_detail(
                    callback,
                    services,
                    idea.id,
                    page=page,
                    scope="admin_public",
                )
            if action == "admin_collect":
                idea = await services.collect_idea(callback_data.idea_id)
                return await show_admin_idea_detail(
                    callback,
                    services,
                    idea.id,
                    page=page,
                    scope="admin_collection",
                )
            if action == "admin_reject":
                idea = await services.reject_idea(callback_data.idea_id)
                return await show_admin_idea_detail(
                    callback,
                    services,
                    idea.id,
                    page=page,
                    scope="admin_rejected",
                )
        except (DomainError, ValidationError) as error:
            return await send_notice(callback, f"❌ {error}")
        return await callback.answer()

    @router.callback_query(ProfileCallback.filter())
    async def profile_actions(
        callback: CallbackQuery, callback_data: ProfileCallback, state: FSMContext
    ):
        if not callback.from_user:
            return await callback.answer()
        if callback_data.action == "edit_nickname":
            return await start_profile_nickname_edit(callback.message, state)
        if callback_data.action == "clear_nickname":
            await services.set_player_nickname(callback.from_user.id, None)
            return await show_profile(callback, services, callback.from_user.id)
        if callback_data.action == "clear_background":
            await services.select_profile_background(callback.from_user.id, None)
            return await show_profile_backgrounds(
                callback, services, callback.from_user.id
            )
        if callback_data.action == "set_background":
            try:
                await services.select_profile_background(
                    callback.from_user.id, callback_data.background_id
                )
            except (DomainError, ValidationError) as error:
                return await send_notice(callback, f"❌ {error}")
            return await show_profile(callback, services, callback.from_user.id)
        if callback_data.action == "open_background":
            player = await services.get_or_create_player(callback.from_user.id)
            if callback_data.background_id not in player.owned_profile_background_ids:
                return await send_notice(callback, "Фон не найден в коллекции")
            background = await services.get_profile_background(
                callback_data.background_id
            )
            if background is None:
                return await send_notice(callback, "Фон не найден")
            return await send_media_preview(
                callback,
                background.media.storage_key,
                profile_background_text(
                    background,
                    selected=player.selected_profile_background_id == background.id,
                ),
                content_type=background.media.content_type,
                reply_markup=profile_background_markup(
                    background.id,
                    selected=player.selected_profile_background_id == background.id,
                ),
            )
        return await callback.answer()

    @router.callback_query(CardCallback.filter())
    async def card_actions(callback: CallbackQuery, callback_data: CardCallback):
        if not callback.from_user:
            return await callback.answer()
        try:
            if callback_data.action == "page":
                if callback_data.scope == "gallery":
                    return await show_gallery(
                        callback, services, max(callback_data.page, 1)
                    )
                return await show_cards(
                    callback,
                    services,
                    callback.from_user.id,
                    max(callback_data.page, 1),
                )
            if callback_data.action == "open":
                if callback_data.scope == "gallery":
                    return await show_card_detail(
                        callback,
                        services,
                        callback_data.card_id,
                        callback.from_user.id,
                        page=max(callback_data.page, 1),
                        scope="gallery",
                    )
                return await show_card_detail(
                    callback,
                    services,
                    callback_data.card_id,
                    callback.from_user.id,
                    page=max(callback_data.page, 1),
                    scope="collection",
                )
            if callback_data.action == "template_open":
                return await show_card_detail(
                    callback,
                    services,
                    callback_data.card_id,
                    callback.from_user.id,
                    page=max(callback_data.page, 1),
                    scope="gallery",
                )
            if callback_data.action == "level_up":
                card = await services.get_card(
                    callback_data.card_id, callback.from_user.id
                )
                template = await services.get_template(card.template_id)
                if template is None:
                    raise DomainError("card template not found")
                player = await services.get_or_create_player(callback.from_user.id)
                return await send_or_edit(
                    callback,
                    card_level_up_confirm_text(
                        player, card, template, services.card_progression.level_up_cost
                    ),
                    card_level_up_confirm_markup(
                        card.id,
                        page=max(callback_data.page, 1),
                        scope=callback_data.scope,
                    ),
                )
            if callback_data.action == "confirm_level_up":
                card = await services.level_up_card(
                    callback.from_user.id, callback_data.card_id
                )
            elif callback_data.action == "ascend":
                card = await services.ascend_card(
                    callback.from_user.id, callback_data.card_id
                )
            elif callback_data.action == "toggle_form":
                card = await services.toggle_card_form(
                    callback.from_user.id, callback_data.card_id
                )
            else:
                return await callback.answer()
            template = await services.get_template(card.template_id)
        except DomainError as error:
            return await send_notice(callback, f"❌ {error}")
        await send_or_edit(
            callback,
            card_text(card, template),
            card_markup(
                card.id,
                card.can_level_up(),
                card.can_ascend(),
                card.is_ascended,
                page=max(callback_data.page, 1),
                scope=callback_data.scope,
            ),
        )

    @router.callback_query(ShopCallback.filter())
    async def shop_actions(callback: CallbackQuery, callback_data: ShopCallback):
        if not callback.from_user or callback_data.action != "buy":
            return await callback.answer()
        try:
            await services.purchase_shop_item(
                callback.from_user.id, callback_data.item_id
            )
        except DomainError as error:
            return await send_notice(callback, f"❌ {error}")
        await show_shop(callback, services)

    @router.callback_query(BannerCallback.filter())
    async def banner_actions(callback: CallbackQuery, callback_data: BannerCallback):
        if not callback.from_user or callback_data.action != "pull":
            return await callback.answer()
        try:
            rewards = await services.pull_banner(
                callback.from_user.id, callback_data.banner_id, callback_data.count
            )
            banner = await services.banners.get_by_id(callback_data.banner_id)
            if banner is None:
                raise DomainError("banner not found")
        except DomainError as error:
            return await send_notice(callback, f"❌ {error}")
        await send_or_edit(
            callback,
            banner_text(banner)
            + "\n\n🎁 <b>Награды</b>\n"
            + "\n".join(f"• {reward}" for reward in rewards),
            banner_markup(banner.id),
        )

    @router.callback_query(ClanCallback.filter())
    async def clan_actions(
        callback: CallbackQuery, callback_data: ClanCallback, state: FSMContext
    ):
        if not callback.from_user:
            return await callback.answer()
        if callback_data.action == "create":
            await state.set_state(ClanCreation.name)
            return await send_notice(callback, "Напиши /clan_create, чтобы начать 🌟")
        if callback_data.action == "leave":
            try:
                await services.leave_clan(callback.from_user.id)
            except DomainError as error:
                return await send_notice(callback, f"❌ {error}")
            return await show_clan(callback, services, callback.from_user.id)
        return await callback.answer()

    @router.callback_query(BattleQueueCallback.filter())
    async def battle_queue(callback: CallbackQuery, callback_data: BattleQueueCallback):
        if not callback.from_user:
            return await callback.answer()
        if callback_data.action == "search":
            return await search_battle(
                callback,
                services,
                callback.from_user.id,
                getattr(callback, "bot", None),
            )
        if callback_data.action == "cancel_search":
            return await cancel_battle_search(callback, services, callback.from_user.id)
        return await callback.answer()

    @router.callback_query(BattleCallback.filter())
    async def battle_actions(callback: CallbackQuery, callback_data: BattleCallback):
        if not callback.from_user:
            return await callback.answer()
        player_id = callback.from_user.id
        battle = await services.get_active_battle(player_id)
        if battle is None:
            return await send_notice(callback, "Бой не найден")
        try:
            if callback_data.action == "back":
                return await show_battle_round(
                    callback, services, player_id, battle=battle
                )
            if callback_data.action == "switch":
                return await show_battle_switch(callback, services, player_id)
            if callback_data.action == "switch_choose":
                battle = await services.record_battle_action(
                    player_id, "switch", card_id=callback_data.card_id
                )
            elif callback_data.action == "attack":
                battle = await services.record_battle_action(player_id, "attack")
            elif callback_data.action == "block":
                battle = await services.record_battle_action(player_id, "block")
            elif callback_data.action == "bonus":
                battle = await services.record_battle_action(player_id, "bonus")
            elif callback_data.action == "ability":
                battle = await services.record_battle_action(player_id, "ability")
            else:
                return await callback.answer()
        except (DomainError, ValidationError, BattleRuleViolationError) as error:
            return await send_alert(callback, f"⛔️ {error}")

        await show_battle_round(callback, services, player_id, battle=battle)
        bot = getattr(callback, "bot", None)
        if bot is None or not hasattr(bot, "send_message"):
            return
        other_id = (
            battle.player_two_id
            if battle.player_one_id == player_id
            else battle.player_one_id
        )
        opponent_summary = services.battle_round_summary(battle, other_id)
        await bot.send_message(
            other_id,
            battle_status_text(
                battle,
                other_id,
                opponent_action_points=opponent_summary.opponent_action_points,
                available_action_points=opponent_summary.available_action_points,
                attack_count=opponent_summary.attack_count,
                block_count=opponent_summary.block_count,
                bonus_count=opponent_summary.bonus_count,
                ability_used=opponent_summary.ability_used,
            ),
            reply_markup=battle_actions_markup(
                can_switch=opponent_summary.can_switch,
                ability_cost=opponent_summary.ability_cost,
                can_use_ability=(
                    not opponent_summary.ability_used
                    and opponent_summary.available_action_points
                    >= opponent_summary.ability_cost
                ),
            ),
        )

    @router.callback_query(BattlePassCallback.filter())
    async def battle_pass_actions(
        callback: CallbackQuery, callback_data: BattlePassCallback
    ):
        if not callback.from_user:
            return await callback.answer()
        if callback_data.action != "buy_level":
            return await callback.answer()
        try:
            progress, level_number = await services.buy_battle_pass_level(
                callback.from_user.id
            )
        except (DomainError, ValidationError, EntityNotFoundError) as error:
            return await send_notice(callback, f"❌ {error}")
        return await send_notice(
            callback,
            f"✅ Куплен уровень {level_number}. У тебя {progress.points} очков.",
        )

    @router.callback_query(PremiumBattlePassCallback.filter())
    async def premium_battle_pass_actions(
        callback: CallbackQuery, callback_data: PremiumBattlePassCallback
    ):
        if not callback.from_user:
            return await callback.answer()
        if callback_data.action != "buy_level":
            return await callback.answer()
        try:
            progress, level_number = await services.buy_premium_battle_pass_level(
                callback.from_user.id
            )
        except (DomainError, ValidationError, EntityNotFoundError) as error:
            return await send_notice(callback, f"❌ {error}")
        return await send_notice(
            callback,
            f"✅ Куплен premium-уровень {level_number}. У тебя {progress.points} очков.",
        )

    @router.callback_query(DeckCallback.filter())
    async def deck_actions(callback: CallbackQuery, callback_data: DeckCallback):
        if not callback.from_user:
            return await callback.answer()
        try:
            if callback_data.action == "toggle":
                await services.toggle_deck_draft_card(
                    callback.from_user.id, callback_data.card_id
                )
            elif callback_data.action == "clear":
                await services.clear_deck_draft(callback.from_user.id)
            elif callback_data.action == "save":
                await services.save_deck_draft(callback.from_user.id)
            else:
                return await callback.answer()
        except (DomainError, ValidationError) as error:
            return await send_notice(callback, f"❌ {error}")
        await show_deck_builder(callback, services, callback.from_user.id)

    @router.callback_query(FreeRewardCallback.filter())
    async def free_reward_actions(
        callback: CallbackQuery, callback_data: FreeRewardCallback
    ):
        if not callback.from_user:
            return await callback.answer()
        try:
            if callback_data.action == "claim_card":
                card, template = await services.claim_free_card(callback.from_user.id)
                notice = f"🎉 <b>Награда:</b> карта <b>{template.name}</b> · <code>{template.rarity.value}</code> · card_id <code>{card.id}</code>"
            elif callback_data.action == "claim_resources":
                resource, amount = await services.claim_free_resources(
                    callback.from_user.id
                )
                notice = f"🎉 <b>Награда:</b> <code>{amount}</code> {resource.value}"
            else:
                return await callback.answer()
        except (DomainError, ValidationError) as error:
            return await send_notice(callback, f"❌ {error}")
        await show_free_rewards(callback, services, callback.from_user.id, notice)

    @router.callback_query(AdminCallback.filter())
    async def admin_actions(
        callback: CallbackQuery, callback_data: AdminCallback, state: FSMContext
    ):
        if not callback.from_user or callback.from_user.id not in settings.admin_ids:
            return await send_notice(callback, "⛔ Доступ закрыт.")
        action = callback_data.action
        if action == "section":
            return await show_admin(callback, services, callback_data.value)
        if action == "create_card":
            return await start_card_create(callback.message, state)
        if action == "create_profile_background":
            return await start_profile_background_create(callback.message, state)
        if action == "players_creator_points":
            return await start_admin_player_edit(
                callback.message, state, "creator_points"
            )
        if action == "players_premium_toggle":
            return await start_admin_player_edit(
                callback.message, state, "premium_toggle"
            )
        if action == "players_title":
            return await start_admin_player_edit(callback.message, state, "title")
        if action == "players_premium_toggle_confirm":
            data: dict[str, object] = await state.get_data()
            player_id = data.get("player_id")
            if not isinstance(player_id, int):
                await state.clear()
                return await send_notice(callback, "❌ player id is missing")
            if callback_data.value == "no":
                await state.clear()
                await send_notice(callback, "Переключение отменено.")
                return await show_admin(callback, services, "players")
            try:
                player = await services.toggle_player_premium(player_id)
            except (DomainError, ValidationError, EntityNotFoundError) as error:
                await state.clear()
                return await send_notice(callback, f"❌ {error}")
            await state.clear()
            await callback.message.answer(
                f"✅ Premium-статус игрока <code>{player.telegram_id}</code>: "
                f"<code>{'yes' if player.is_premium else 'no'}</code>"
            )
            return await show_admin(callback, services, "players")
        if action == "delete_player":
            return await start_admin_player_delete(callback.message, state)
        if action == "delete_card":
            await state.clear()
            await state.set_state(CardDelete.item_id)
            return await callback.message.answer(
                "Введи ID карты, которую нужно удалить 🗑️",
                reply_markup=admin_wizard_markup("cards"),
            )
        if action == "create_banner":
            return await start_banner_create(callback.message, state)
        if action == "create_shop_item":
            return await start_shop_create(callback.message, state)
        if action == "delete_shop_item":
            await state.clear()
            await state.set_state(ShopDelete.item_id)
            return await callback.message.answer(
                "Введи ID товара, который нужно удалить 🗑️",
                reply_markup=admin_wizard_markup("shop"),
            )
        if action == "standard_add":
            await state.clear()
            await state.set_state(StandardCardsEdit.value)
            await state.update_data(mode="add")
            return await callback.message.answer(
                "Введите ID шаблона карты, которую нужно добавить в стартовый набор ✍️",
                reply_markup=admin_wizard_markup("standard_cards"),
            )
        if action == "standard_remove":
            await state.clear()
            await state.set_state(StandardCardsEdit.value)
            await state.update_data(mode="remove")
            return await callback.message.answer(
                "Введите ID шаблона карты, которую нужно убрать из стартового набора ✍️",
                reply_markup=admin_wizard_markup("standard_cards"),
            )
        if action == "standard_clear":
            await services.set_standard_cards([])
            return await show_admin(callback, services, "standard_cards")
        if action == "banner_add_card":
            banner = await services.banners.get_by_id(callback_data.banner_id)
            if banner is None:
                return await send_notice(callback, "Баннер не найден")
            if not banner.can_edit():
                return await send_notice(callback, "Баннер уже запущен")
            await state.clear()
            await state.set_state(BannerRewardCreate.template_id)
            await state.update_data(
                banner_id=callback_data.banner_id,
                reward_action="add",
                reward_kind="card",
            )
            return await callback.message.answer(
                "Введи ID карты для баннера ✍️",
                reply_markup=admin_wizard_markup("banners"),
            )
        if action == "banner_remove_card":
            banner = await services.banners.get_by_id(callback_data.banner_id)
            if banner is None:
                return await send_notice(callback, "Баннер не найден")
            if not banner.can_edit():
                return await send_notice(callback, "Баннер уже запущен")
            await state.clear()
            await state.set_state(BannerRewardCreate.template_id)
            await state.update_data(
                banner_id=callback_data.banner_id,
                reward_action="remove",
                reward_kind="card",
            )
            return await callback.message.answer(
                "Введи ID карты, которую нужно убрать из баннера ✍️",
                reply_markup=admin_wizard_markup("banners"),
            )
        if action == "banner_add_background":
            banner = await services.banners.get_by_id(callback_data.banner_id)
            if banner is None:
                return await send_notice(callback, "Баннер не найден")
            if not banner.can_edit():
                return await send_notice(callback, "Баннер уже запущен")
            await state.clear()
            await state.set_state(BannerRewardCreate.template_id)
            await state.update_data(
                banner_id=callback_data.banner_id,
                reward_action="add",
                reward_kind="background",
            )
            return await callback.message.answer(
                "Введи ID фона профиля для баннера ✍️",
                reply_markup=admin_wizard_markup("banners"),
            )
        if action == "banner_remove_background":
            banner = await services.banners.get_by_id(callback_data.banner_id)
            if banner is None:
                return await send_notice(callback, "Баннер не найден")
            if not banner.can_edit():
                return await send_notice(callback, "Баннер уже запущен")
            await state.clear()
            await state.set_state(BannerRewardCreate.template_id)
            await state.update_data(
                banner_id=callback_data.banner_id,
                reward_action="remove",
                reward_kind="background",
            )
            return await callback.message.answer(
                "Введи ID фона профиля, который нужно убрать из баннера ✍️",
                reply_markup=admin_wizard_markup("banners"),
            )
        if action == "delete_banner":
            try:
                await services.delete_banner(callback_data.banner_id)
            except (DomainError, ValidationError) as error:
                return await send_notice(callback, f"❌ {error}")
            return await show_admin(callback, services, "banners")
        if action == "cancel":
            await state.clear()
            return await show_admin(callback, services)
        if action == "card_rarity":
            await state.update_data(rarity=callback_data.value)
            await state.set_state(CardCreate.image)
            return await callback.message.answer(image_input_guide())
        if action == "card_class":
            await state.update_data(card_class=callback_data.value)
            await state.set_state(CardCreate.base_stats)
            return await callback.message.answer(
                "Введи базовые статы: урон здоровье защита ✍️"
            )
        if action == "profile_background_rarity":
            await state.update_data(rarity=callback_data.value)
            await state.set_state(ProfileBackgroundCreate.media)
            return await callback.message.answer(
                profile_background_wizard_text("медиа", await state.get_data())
            )
        if action == "banner_type":
            await state.update_data(banner_type=callback_data.value)
            await state.set_state(BannerCreate.cost_resource)
            return await callback.message.answer(
                banner_wizard_text("валюта", await state.get_data()),
                reply_markup=admin_choice_markup(
                    "banner_cost",
                    [
                        (item.value, item.value)
                        for item in (
                            ResourceType.SILVER_TICKETS,
                            ResourceType.GOLD_TICKETS,
                        )
                    ],
                    "banners",
                ),
            )
        if action == "banner_cost":
            await state.update_data(cost_resource=callback_data.value)
            await state.set_state(BannerCreate.start_at)
            return await callback.message.answer(
                "Введи дату старта в ISO-формате, например <code>2026-04-10T12:00:00+00:00</code> ⏳"
            )
        if action == "shop_sell":
            await state.update_data(sell_resource_type=callback_data.value)
            await state.set_state(ShopCreate.buy_resource)
            return await callback.message.answer(
                shop_wizard_text("что получаем", await state.get_data()),
                reply_markup=admin_choice_markup(
                    "shop_buy",
                    [(item.value, item.value) for item in ResourceType],
                    "shop",
                ),
            )
        if action == "shop_buy":
            await state.update_data(buy_resource_type=callback_data.value)
            await state.set_state(ShopCreate.price)
            return await callback.message.answer("Какова цена? 💰")
        if action == "shop_active":
            data = await state.get_data()
            try:
                await services.create_shop_item(
                    ResourceType(data["sell_resource_type"]),
                    ResourceType(data["buy_resource_type"]),
                    data["price"],
                    data["quantity"],
                    callback_data.value == "yes",
                )
            except (DomainError, ValidationError, KeyError, ValueError) as error:
                await state.clear()
                return await send_notice(callback, f"❌ {error}")
            await state.clear()
            return await show_admin(callback, services, "shop")
        if action == "banner_reward_guaranteed":
            await _banner_reward_finish(
                callback.message, services, state, callback_data.value
            )
            return
        if action == "battle_pass_add_level":
            return await start_battle_pass_level_create(callback.message, state)
        if action == "battle_pass_create_season":
            return await start_battle_pass_season_create(callback.message, state)
        if action == "battle_pass_delete_season":
            return await start_battle_pass_season_delete(callback.message, state)
        if action == "premium_battle_pass_add_level":
            return await start_battle_pass_level_create(
                callback.message, state, premium=True
            )
        if action == "premium_battle_pass_create_season":
            return await start_battle_pass_season_create(
                callback.message, state, premium=True
            )
        if action == "premium_battle_pass_delete_season":
            return await start_battle_pass_season_delete(
                callback.message, state, premium=True
            )
        if action == "free_rewards_card_weights":
            return await start_free_rewards_edit(
                callback.message, state, "card_weights"
            )
        if action == "free_rewards_resource_weights":
            return await start_free_rewards_edit(
                callback.message, state, "resource_weights"
            )
        if action == "free_rewards_resource_values":
            return await start_free_rewards_edit(
                callback.message, state, "resource_values"
            )
        if action == "universe_add":
            return await start_universe_create(callback.message, state)
        if action == "universe_remove":
            return await start_universe_delete(callback.message, state)
        return await callback.answer()

    @router.message(CardDelete.item_id)
    async def _card_delete_item(message: Message, state: FSMContext):
        if not message.text:
            return await message.answer("Введи ID числом 🙂")
        try:
            await services.delete_card_template(
                _parse_int(message.text, "item id", positive=True)
            )
        except (DomainError, ValidationError) as error:
            await state.clear()
            return await message.answer(f"❌ {error}")
        await state.clear()
        await show_admin(message, services, "cards")

    @router.message(ShopDelete.item_id)
    async def _shop_delete_item(message: Message, state: FSMContext):
        if not message.text:
            return await message.answer("Введи ID числом 🙂")
        try:
            await services.remove_shop_item(
                _parse_int(message.text, "item id", positive=True)
            )
        except (DomainError, ValidationError) as error:
            await state.clear()
            return await message.answer(f"❌ {error}")
        await state.clear()
        await show_admin(message, services, "shop")

    @router.message(StandardCardsEdit.value)
    async def _standard_cards(message: Message, state: FSMContext):
        data = await state.get_data()
        template_id = _parse_int(message.text or "0", "template id", positive=True)
        try:
            await services.remove_standard_card(template_id) if data.get(
                "mode"
            ) == "remove" else await services.add_standard_card(template_id)
        except DomainError as error:
            await state.clear()
            return await message.answer(f"❌ {error}")
        await state.clear()
        await show_admin(message, services, "standard_cards")

    @router.message(FreeRewardsEdit.value)
    async def _free_rewards_edit(message: Message, state: FSMContext):
        await capture_free_rewards_edit(message, services, state)

    @router.message(IdeaProposal.title)
    async def _idea_title(message: Message, state: FSMContext):
        await capture_idea_title(message, state)

    @router.message(IdeaProposal.description)
    async def _idea_description(message: Message, state: FSMContext):
        await capture_idea_description(message, services, state)

    @router.message(ProfileEdit.nickname)
    async def _profile_nickname(message: Message, state: FSMContext):
        await capture_profile_nickname(message, services, state)

    @router.message(AdminPlayerEdit.player_id)
    async def _admin_player_id(message: Message, state: FSMContext):
        await capture_admin_player_id(message, services, state)

    @router.message(AdminPlayerEdit.value)
    async def _admin_player_value(message: Message, state: FSMContext):
        await capture_admin_player_value(message, services, state)

    @router.message(PlayerDelete.player_id)
    async def _admin_player_delete(message: Message, state: FSMContext):
        await capture_admin_player_delete(message, services, state)

    @router.message(BattlePassLevelCreate.level_number)
    async def _battle_pass_level_number(message: Message, state: FSMContext):
        await capture_battle_pass_level_number(message, state)

    @router.message(BattlePassLevelCreate.required_points)
    async def _battle_pass_required_points(message: Message, state: FSMContext):
        await capture_battle_pass_required_points(message, state)

    @router.message(BattlePassLevelCreate.reward)
    async def _battle_pass_reward(message: Message, state: FSMContext):
        await capture_battle_pass_reward(message, services, state)

    @router.message(BattlePassSeasonCreate.name)
    async def _battle_pass_season_name(message: Message, state: FSMContext):
        await capture_battle_pass_season_name(message, state)

    @router.message(BattlePassSeasonCreate.start_at)
    async def _battle_pass_season_start(message: Message, state: FSMContext):
        await capture_battle_pass_season_start_at(message, state)

    @router.message(BattlePassSeasonCreate.end_at)
    async def _battle_pass_season_end(message: Message, state: FSMContext):
        await capture_battle_pass_season_end_at(message, services, state)

    @router.message(BattlePassSeasonDelete.season_id)
    async def _battle_pass_season_delete(message: Message, state: FSMContext):
        await capture_battle_pass_season_delete(message, services, state)

    @router.message(UniverseCreate.value)
    async def _universe_add(message: Message, state: FSMContext):
        await capture_universe_add(message, services, state)

    @router.message(UniverseDelete.value)
    async def _universe_remove(message: Message, state: FSMContext):
        await capture_universe_remove(message, services, state)

    @router.message(CardCreate.name)
    async def _card_name(message: Message, state: FSMContext):
        await card_name(message, state)

    @router.message(CardCreate.universe_value)
    async def _card_universe_value(message: Message, state: FSMContext):
        await card_universe_value(message, state)

    @router.message(CardCreate.image)
    async def _card_image(message: Message, state: FSMContext):
        await card_image(message, state)

    @router.message(CardCreate.base_stats)
    async def _card_base_stats(message: Message, state: FSMContext):
        await card_base_stats(message, state)

    @router.message(CardCreate.ascended_stats)
    async def _card_ascended_stats(message: Message, state: FSMContext):
        await card_ascended_stats(message, state)

    @router.message(CardCreate.ability_cost)
    async def _card_ability_cost(message: Message, state: FSMContext):
        await card_ability_cost(message, state)

    @router.message(CardCreate.ability_cooldown)
    async def _card_ability_cooldown(message: Message, state: FSMContext):
        await card_ability_cooldown(message, state)

    @router.message(CardCreate.ability_effects)
    async def _card_ability_effects(message: Message, state: FSMContext):
        await card_ability_effects(message, state)

    @router.message(CardCreate.ascended_effects)
    async def _card_ascended_effects(message: Message, state: FSMContext):
        await card_ascended_effects(message, services, state)

    @router.message(ProfileBackgroundCreate.media)
    async def _profile_background_media(message: Message, state: FSMContext):
        await profile_background_media(message, services, state)

    @router.message(BannerCreate.name)
    async def _banner_name(message: Message, state: FSMContext):
        await banner_name(message, state)

    @router.message(BannerCreate.start_at)
    async def _banner_start_at(message: Message, state: FSMContext):
        await banner_start_at(message, state)

    @router.message(BannerCreate.end_at)
    async def _banner_end_at(message: Message, state: FSMContext):
        await banner_end_at(message, services, state)

    @router.message(BannerRewardCreate.template_id)
    async def _banner_reward_template(message: Message, state: FSMContext):
        template_id = _parse_int(message.text or "0", "template id", positive=True)
        data = await state.get_data()
        await state.update_data(template_id=template_id)
        if data.get("reward_action") == "remove":
            try:
                if data.get("reward_kind") == "background":
                    await services.remove_banner_reward_profile_background(
                        data["banner_id"], template_id
                    )
                else:
                    await services.remove_banner_reward_card(
                        data["banner_id"], template_id
                    )
            except (DomainError, ValidationError) as error:
                await state.clear()
                return await message.answer(f"❌ {error}")

            banner = await services.banners.get_by_id(data["banner_id"])
            await state.clear()
            if banner is None:
                return await message.answer("Баннер не найден")
            return await message.answer(
                text=banner_text(banner, banner.can_edit())
                + "\n\n"
                + banner_pool_text(
                    banner, _templates(services), _profile_backgrounds(services)
                ),
                reply_markup=admin_banner_markup(banner.id, banner.can_edit()),
            )
        await state.set_state(BannerRewardCreate.weight)
        if data.get("reward_kind") == "background":
            await message.answer("Какой вес у этого фона? 🎯")
        else:
            await message.answer("Какой вес у этой карты? 🎯")

    @router.message(BannerRewardCreate.weight)
    async def _banner_reward_weight(message: Message, state: FSMContext):
        await state.update_data(
            weight=_parse_int(message.text or "0", "weight", positive=True)
        )
        await state.set_state(BannerRewardCreate.guaranteed)
        await message.answer(
            "Гарантировать выпадение в 10-крутке?",
            reply_markup=admin_choice_markup(
                "banner_reward_guaranteed", [("Да", "yes"), ("Нет", "no")], "banners"
            ),
        )

    @router.message(ShopCreate.sell_resource)
    async def _shop_sell(message: Message, state: FSMContext):
        if not message.text:
            return await message.answer("Нужно написать тип ресурса текстом 🙂")
        await state.update_data(sell_resource_type=message.text.strip())
        await state.set_state(ShopCreate.buy_resource)
        await message.answer(
            shop_wizard_text("что получаем", await state.get_data()),
            reply_markup=admin_choice_markup(
                "shop_buy", [(item.value, item.value) for item in ResourceType], "shop"
            ),
        )

    @router.message(ShopCreate.buy_resource)
    async def _shop_buy(message: Message, state: FSMContext):
        if not message.text:
            return await message.answer("Нужно написать тип ресурса текстом 🙂")
        await state.update_data(buy_resource_type=message.text.strip())
        await state.set_state(ShopCreate.price)
        await message.answer("Какова цена? 💰")

    @router.message(ShopCreate.price)
    async def _shop_price(message: Message, state: FSMContext):
        await shop_price(message, state)

    @router.message(ShopCreate.quantity)
    async def _shop_quantity(message: Message, state: FSMContext):
        await shop_quantity(message, state)

    @router.message(Command("clan_join"))
    async def join_clan(message: Message, command: CommandObject):
        if not message.from_user:
            return
        if command.args is None:
            return await message.answer(
                "Используй: <code>/clan_join &lt;clan_id&gt;</code>"
            )
        try:
            await services.join_clan(message.from_user.id, int(command.args.strip()))
        except (ValueError, DomainError, ValidationError) as error:
            return await message.answer(f"❌ {error}")
        await show_clan(message, services, message.from_user.id)

    @router.message(Command("clan_leave"))
    async def leave_clan(message: Message):
        if not message.from_user:
            return
        try:
            await services.leave_clan(message.from_user.id)
        except DomainError as error:
            return await message.answer(f"❌ {error}")
        await show_clan(message, services, message.from_user.id)

    @router.message(Command("cards"))
    async def open_cards(message: Message):
        if message.from_user:
            await show_cards(message, services, message.from_user.id)

    @router.message(Command("gallery"))
    async def open_gallery(message: Message):
        await show_gallery(message, services)

    @router.message(Command("free"))
    async def open_free_rewards(message: Message):
        if message.from_user:
            await show_free_rewards(message, services, message.from_user.id)

    @router.message(Command("battle_pass"))
    async def open_battle_pass(message: Message):
        if message.from_user:
            await show_battle_pass(message, services, message.from_user.id)

    @router.message(Command("premium_battle_pass"))
    async def open_premium_battle_pass(message: Message):
        if message.from_user:
            await show_premium_battle_pass(message, services, message.from_user.id)

    return router
