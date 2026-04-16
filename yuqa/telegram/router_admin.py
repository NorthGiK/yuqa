"""Admin command, callback, and wizard handler registration."""

from yuqa.shared.errors import DomainError, EntityNotFoundError, ValidationError
from yuqa.shared.enums import Rarity, ResourceType
from yuqa.telegram.callbacks import AdminCallback
from yuqa.telegram.compat import CallbackQuery, Command, CommandObject, FSMContext, Message, Router
from yuqa.telegram.reply import send_notice
from yuqa.telegram.router_helpers import _parse_int, _profile_backgrounds, _templates
from yuqa.telegram.router_views import show_admin
from yuqa.telegram.states import (
    AdminPlayerCardEdit,
    AdminPlayerEdit,
    BannerCreate,
    BannerRewardCreate,
    BattlePassLevelCreate,
    BattlePassSeasonCreate,
    BattlePassSeasonDelete,
    CardCreate,
    CardDelete,
    FreeRewardsEdit,
    PlayerDelete,
    ProfileBackgroundCreate,
    ShopCreate,
    ShopDelete,
    StandardCardsEdit,
    UniverseCreate,
    UniverseDelete,
)
from yuqa.telegram.texts import (
    banner_pool_text,
    banner_text,
    banner_wizard_text,
    card_wizard_text,
    image_input_guide,
    profile_background_wizard_text,
    shop_wizard_text,
)
from yuqa.telegram.ui import admin_banner_markup, admin_choice_markup, admin_wizard_markup
from yuqa.telegram.router_wizards_banners import (
    _banner_reward_finish,
    banner_end_at,
    banner_name,
    banner_start_at,
    start_banner_create,
)
from yuqa.telegram.router_wizards_cards import (
    capture_admin_player_card_player_id,
    capture_admin_player_card_template_id,
    card_ability_cooldown,
    card_ability_cost,
    card_ability_effects,
    card_ascended_effects,
    card_ascended_stats,
    card_base_stats,
    card_image,
    card_name,
    card_universe_value,
    capture_universe_add,
    capture_universe_remove,
    profile_background_media,
    start_admin_player_card_edit,
    start_card_create,
    start_profile_background_create,
    start_universe_create,
    start_universe_delete,
)
from yuqa.telegram.router_wizards_shop import (
    shop_price,
    shop_quantity,
    start_shop_create,
)
from yuqa.telegram.router_wizards_players import (
    capture_admin_player_delete,
    capture_admin_player_id,
    capture_admin_player_value,
    start_admin_player_delete,
    start_admin_player_edit,
)
from yuqa.telegram.router_wizards_progression import (
    capture_battle_pass_level_number,
    capture_battle_pass_required_points,
    capture_battle_pass_reward,
    capture_battle_pass_season_delete,
    capture_battle_pass_season_end_at,
    capture_battle_pass_season_name,
    capture_battle_pass_season_start_at,
    capture_free_rewards_edit,
    start_battle_pass_level_create,
    start_battle_pass_season_create,
    start_battle_pass_season_delete,
    start_free_rewards_edit,
)


def register_admin_handlers(router: Router, services, settings) -> None:
    """Register admin-only commands, callbacks, and state handlers."""

    _register_admin_commands(router, services, settings)
    _register_admin_callbacks(router, services, settings)
    _register_admin_state_handlers(router, services)


def _register_admin_commands(router: Router, services, settings) -> None:
    """Register admin-only commands."""

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


def _register_admin_callbacks(router: Router, services, settings) -> None:
    """Register the admin callback family."""

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
        if action == "player_add_card":
            return await start_admin_player_card_edit(callback.message, state, "add")
        if action == "player_remove_card":
            return await start_admin_player_card_edit(
                callback.message, state, "remove"
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
            return await _start_banner_reward_edit(
                callback, state, services, callback_data.banner_id, "add", "card"
            )
        if action == "banner_remove_card":
            return await _start_banner_reward_edit(
                callback, state, services, callback_data.banner_id, "remove", "card"
            )
        if action == "banner_add_background":
            return await _start_banner_reward_edit(
                callback,
                state,
                services,
                callback_data.banner_id,
                "add",
                "background",
            )
        if action == "banner_remove_background":
            return await _start_banner_reward_edit(
                callback,
                state,
                services,
                callback_data.banner_id,
                "remove",
                "background",
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
        if action == "card_universe_pick":
            if callback_data.value == "__new__":
                await state.set_state(CardCreate.universe_value)
                return await callback.message.answer("Введи название новой вселенной ✍️")
            await state.update_data(universe=callback_data.value)
            await state.set_state(CardCreate.rarity)
            return await callback.message.answer(
                card_wizard_text("редкость", await state.get_data()),
                reply_markup=admin_choice_markup(
                    "card_rarity",
                    [(item.value, item.value) for item in Rarity],
                    "cards",
                ),
            )
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


def _register_admin_state_handlers(router: Router, services) -> None:
    """Register admin-only state handlers."""

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

    @router.message(AdminPlayerEdit.player_id)
    async def _admin_player_id(message: Message, state: FSMContext):
        await capture_admin_player_id(message, services, state)

    @router.message(AdminPlayerEdit.value)
    async def _admin_player_value(message: Message, state: FSMContext):
        await capture_admin_player_value(message, services, state)

    @router.message(AdminPlayerCardEdit.player_id)
    async def _admin_player_card_id(message: Message, state: FSMContext):
        await capture_admin_player_card_player_id(message, state)

    @router.message(AdminPlayerCardEdit.template_id)
    async def _admin_player_card_template(message: Message, state: FSMContext):
        await capture_admin_player_card_template_id(message, services, state)

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
        await card_name(message, state, services)

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


async def _start_banner_reward_edit(
    callback: CallbackQuery,
    state: FSMContext,
    services,
    banner_id: int,
    reward_action: str,
    reward_kind: str,
):
    """Open banner reward editing for one banner and reward kind."""

    banner = await services.banners.get_by_id(banner_id)
    if banner is None:
        return await send_notice(callback, "Баннер не найден")
    if not banner.can_edit():
        return await send_notice(callback, "Баннер уже запущен")
    await state.clear()
    await state.set_state(BannerRewardCreate.template_id)
    await state.update_data(
        banner_id=banner_id,
        reward_action=reward_action,
        reward_kind=reward_kind,
    )
    label = "фона профиля" if reward_kind == "background" else "карты"
    verb = "для баннера" if reward_action == "add" else "который нужно убрать из баннера"
    return await callback.message.answer(
        f"Введи ID {label} {verb} ✍️",
        reply_markup=admin_wizard_markup("banners"),
    )


__all__ = ["register_admin_handlers"]
