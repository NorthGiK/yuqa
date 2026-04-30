"""Battle pass and free-reward wizard flows."""

from yuqa.shared.errors import DomainError, ValidationError
from yuqa.shared.enums import Rarity, ResourceType
from yuqa.telegram.compat import FSMContext, Message
from yuqa.telegram.router.router_helpers import (
    _parse_dt,
    _parse_int,
    _parse_mapping,
    _parse_reward_bundle,
)
from yuqa.telegram.router.router_views import show_admin
from yuqa.telegram.states import (
    BattlePassLevelCreate,
    BattlePassSeasonCreate,
    BattlePassSeasonDelete,
    FreeRewardsEdit,
)
from yuqa.telegram.texts.texts import (
    battle_pass_level_wizard_text,
    battle_pass_season_wizard_text,
    free_rewards_edit_guide,
)
from yuqa.telegram.ui.ui import admin_wizard_markup


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


__all__ = [
    "capture_battle_pass_level_number",
    "capture_battle_pass_required_points",
    "capture_battle_pass_reward",
    "capture_battle_pass_season_delete",
    "capture_battle_pass_season_end_at",
    "capture_battle_pass_season_name",
    "capture_battle_pass_season_start_at",
    "capture_free_rewards_edit",
    "start_battle_pass_level_create",
    "start_battle_pass_season_create",
    "start_battle_pass_season_delete",
    "start_free_rewards_edit",
]
