"""Public command, callback, and wizard handler registration."""

from src.shared.errors import (
    BattleRuleViolationError,
    DomainError,
    EntityNotFoundError,
    ValidationError,
)
from src.telegram.callbacks import (
    BannerCallback,
    BattleCallback,
    BattlePassCallback,
    BattleQueueCallback,
    CardCallback,
    ClanCallback,
    DeckCallback,
    FreeRewardCallback,
    IdeaCallback,
    MenuCallback,
    PremiumBattlePassCallback,
    ProfileCallback,
    ShopCallback,
    TopCallback,
)
from src.telegram.compat import (
    CallbackQuery,
    Command,
    CommandObject,
    CommandStart,
    FSMContext,
    Message,
    Router,
)
from src.telegram.config import Settings
from src.telegram.services.services import TelegramServices
from src.telegram.reply import (
    send_alert,
    send_media_preview,
    send_notice,
    send_or_edit,
)
from src.telegram.router.battle import (
    cancel_battle_search,
    search_battle,
    start_battle,
)
from src.telegram.router.helpers import _admin_idea_scope_to_section
from src.telegram.router.views import (
    show_admin,
    show_admin_idea_detail,
    show_banners,
    show_battle,
    show_battle_pass,
    show_battle_round,
    show_battle_switch,
    show_card_detail,
    show_cards,
    show_clan,
    show_collection,
    show_deck_builder,
    show_free_rewards,
    show_gallery,
    show_home,
    show_idea_collection,
    show_idea_detail,
    show_ideas,
    show_premium_battle_pass,
    show_profile,
    show_profile_backgrounds,
    show_shop,
    show_tops,
)
from src.telegram.states import ClanCreation, IdeaProposal, ProfileEdit
from src.telegram.texts import (
    banner_text,
    battle_result_text,
    battle_started_text,
    battle_status_text,
    card_level_up_confirm_text,
    profile_background_text,
)
from src.telegram.quests import (
    DAILITY_START,
)
from src.telegram.ui import (
    COLLECTION_MENU_BUTTON,
    MAIN_MENU_BUTTON_TEXTS,
    banner_markup,
    battle_actions_markup,
    card_level_up_confirm_markup,
    profile_background_markup,
)
from src.telegram.router.wizards_players import (
    capture_clan_icon,
    capture_clan_name,
    capture_idea_description,
    capture_idea_title,
    capture_profile_nickname,
    start_clan_creation,
    start_idea_proposal,
    start_profile_nickname_edit,
)


def register_public_handlers(
    router: Router,
    services: TelegramServices,
    settings: Settings,
) -> None:
    """Register non-admin commands, callbacks, and state handlers."""

    _register_public_commands(router, services, settings)
    _register_public_callbacks(router, services, settings)


def _register_public_commands(
    router: Router,
    services: TelegramServices,
    settings: Settings,
) -> None:
    """Register public command and menu handlers."""

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
            await services.complete_action_quest(
                player_id=message.from_user.id,
                quest=DAILITY_START,
            )
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

    @router.message(ClanCreation.name)
    async def clan_name(message: Message, state: FSMContext):
        await capture_clan_name(message, state)

    @router.message(ClanCreation.icon)
    async def clan_icon(message: Message, state: FSMContext):
        await capture_clan_icon(message, services, state)

    @router.message(IdeaProposal.title)
    async def _idea_title(message: Message, state: FSMContext):
        await capture_idea_title(message, state)

    @router.message(IdeaProposal.description)
    async def _idea_description(message: Message, state: FSMContext):
        await capture_idea_description(message, services, state)

    @router.message(ProfileEdit.nickname)
    async def _profile_nickname(message: Message, state: FSMContext):
        await capture_profile_nickname(message, services, state)

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


def _register_public_callbacks(router: Router, services, settings) -> None:
    """Register non-admin callback families."""

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
            return await start_idea_proposal(callback.message, state)  # type:ignore
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
            return await start_profile_nickname_edit(callback.message, state)  # type:ignore
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
        except DomainError as error:
            return await send_notice(callback, f"❌ {error}")
        return await show_card_detail(
            callback,
            services,
            card.id,
            callback.from_user.id,
            page=max(callback_data.page, 1),
            scope="collection",
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
            return await show_battle(callback, services, player_id)
        previous_round = battle.current_round
        previous_status = battle.status.value
        previous_turn_player_id = services.battle_round_summary(
            battle, player_id
        ).current_turn_player_id
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
        except EntityNotFoundError:
            return await show_battle(callback, services, player_id)
        except (DomainError, ValidationError, BattleRuleViolationError) as error:
            return await send_alert(callback, f"⛔️ {error}")

        await show_battle_round(callback, services, player_id, battle=battle)
        current_turn_player_id = services.battle_round_summary(
            battle, player_id
        ).current_turn_player_id
        if (
            battle.current_round != previous_round
            or battle.status.value != previous_status
            or current_turn_player_id != previous_turn_player_id
        ):
            bot = getattr(callback, "bot", None)
            if bot is not None and hasattr(bot, "send_message"):
                other_id = (
                    battle.player_two_id
                    if battle.player_one_id == player_id
                    else battle.player_one_id
                )
                opponent_player = await services.get_player(other_id)
                if opponent_player is None:
                    opponent_player = await services.get_or_create_player(other_id)
                opponent_summary = services.battle_round_summary(battle, other_id)
                await bot.send_message(
                    other_id,
                    battle_result_text(battle, opponent_player)
                    if battle.status.value != "active"
                    else battle_started_text(battle)
                    + "\n"
                    + battle_status_text(
                        battle,
                        other_id,
                        current_turn_player_id=opponent_summary.current_turn_player_id,
                        opponent_spent_action_points=opponent_summary.opponent_spent_action_points,
                        available_action_points=opponent_summary.available_action_points,
                        total_action_points=opponent_summary.total_action_points,
                        attack_count=opponent_summary.attack_count,
                        block_count=opponent_summary.block_count,
                        bonus_count=opponent_summary.bonus_count,
                        ability_used=opponent_summary.ability_used,
                    ),
                    reply_markup=None
                    if battle.status.value != "active"
                    or not opponent_summary.is_player_turn
                    or opponent_summary.available_action_points <= 0
                    else battle_actions_markup(
                        can_switch=opponent_summary.can_switch,
                        ability_cost=opponent_summary.ability_cost,
                        can_use_ability=(
                            opponent_summary.is_player_turn
                            and not opponent_summary.ability_used
                            and opponent_summary.ability_cooldown_remaining <= 0
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
