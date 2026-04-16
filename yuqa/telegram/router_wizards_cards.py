"""Card and related content-admin wizard flows."""

from yuqa.cards.domain.entities import Ability
from yuqa.shared.errors import DomainError, ValidationError
from yuqa.shared.enums import CardClass, ProfileBackgroundRarity, Rarity
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.telegram.compat import FSMContext, Message
from yuqa.telegram.router_helpers import _media_from_message, _parse_effects, _parse_int
from yuqa.telegram.router_views import show_admin
from yuqa.telegram.states import (
    CardCreate,
    ProfileBackgroundCreate,
    UniverseCreate,
    UniverseDelete,
)
from yuqa.telegram.texts import (
    ability_effects_guide,
    card_wizard_text,
    profile_background_wizard_text,
)
from yuqa.telegram.ui import admin_choice_markup, admin_wizard_markup


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


__all__ = [
    "card_ability_cooldown",
    "card_ability_cost",
    "card_ability_effects",
    "card_ascended_effects",
    "card_ascended_stats",
    "card_base_stats",
    "card_image",
    "card_name",
    "card_universe_value",
    "capture_universe_add",
    "capture_universe_remove",
    "profile_background_media",
    "standard_cards_add",
    "standard_cards_remove",
    "start_card_create",
    "start_profile_background_create",
    "start_universe_create",
    "start_universe_delete",
]
