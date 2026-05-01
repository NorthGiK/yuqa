"""Player, clan, profile, and idea wizard flows."""

from src.shared.errors import DomainError, ValidationError
from src.telegram.compat import FSMContext, Message
from src.telegram.router.helpers import _parse_int
from src.telegram.router.views import show_admin, show_ideas, show_profile
from src.telegram.services.services import TelegramServices
from src.telegram.states import (
    AdminPlayerEdit,
    ClanCreation,
    IdeaProposal,
    PlayerDelete,
    ProfileEdit,
)
from src.telegram.texts import clan_text, idea_wizard_text
from src.telegram.ui import admin_choice_markup, admin_wizard_markup, clan_markup


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


__all__ = [
    "capture_admin_player_delete",
    "capture_admin_player_id",
    "capture_admin_player_value",
    "capture_clan_icon",
    "capture_clan_name",
    "capture_idea_description",
    "capture_idea_title",
    "capture_profile_nickname",
    "start_admin_player_delete",
    "start_admin_player_edit",
    "start_clan_creation",
    "start_idea_proposal",
    "start_profile_nickname_edit",
]
