"""Banner wizard flows for admin content management."""

from yuqa.shared.errors import DomainError, ValidationError
from yuqa.shared.enums import BannerType, ResourceType
from yuqa.telegram.compat import FSMContext, Message
from yuqa.telegram.router.router_helpers import (
    _parse_dt,
    _profile_backgrounds,
    _templates,
)
from yuqa.telegram.states import BannerCreate
from yuqa.telegram.texts.texts import banner_pool_text, banner_text, banner_wizard_text
from yuqa.telegram.ui.ui import (
    admin_banner_markup,
    admin_choice_markup,
    admin_wizard_markup,
)


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
        reply_markup=admin_banner_markup(banner.id, True, banner.is_available()),
    )


async def _banner_reward_finish(
    message: Message, services, state: FSMContext, decision: str = "no"
):
    """Finish banner reward editing and reopen the banner management screen."""

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
        reply_markup=admin_banner_markup(
            banner.id, banner.can_edit(), banner.is_available()
        ),
    )


__all__ = [
    "_banner_reward_finish",
    "banner_end_at",
    "banner_name",
    "banner_start_at",
    "start_banner_create",
]
