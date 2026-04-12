"""Tests for the Telegram presentation layer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from yuqa.cards.domain.entities import Ability, AbilityEffect, CardTemplate, PlayerCard
from yuqa.players.domain.entities import Player, ProfileBackgroundTemplate
from yuqa.shared.enums import (
    AbilityStat,
    AbilityTarget,
    CardClass,
    ProfileBackgroundRarity,
    Rarity,
    Universe,
)
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.resource_wallet import ResourceWallet
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.telegram.compat import (
    CallbackQuery,
    FSMContext,
    Message,
    TelegramBadRequest,
    User,
)
from yuqa.telegram.reply import safe_edit, send_card_preview
from yuqa.telegram.router import (
    show_admin,
    show_card_detail,
    show_gallery,
    show_idea_collection,
    show_idea_detail,
    show_ideas,
    show_cards,
    show_deck_builder,
    show_free_rewards,
    show_profile,
    show_tops,
)
from yuqa.telegram.services import TelegramServices
from yuqa.telegram.texts import (
    admin_text,
    battle_text,
    cards_text,
    menu_text,
    profile_backgrounds_text,
    profile_text,
    tops_text,
)
from yuqa.telegram.ui import (
    admin_banner_markup,
    admin_markup,
    battle_markup,
    cards_markup,
    main_menu_markup,
    tops_markup,
)


def _button_texts(markup) -> set[str]:
    """Collect button captions from a markup in a test-friendly way."""

    texts = set()
    for row in markup.inline_keyboard:
        for button in row:
            if hasattr(button, "text"):
                texts.add(button.text)
            else:
                texts.add(button[0])
    return texts


@pytest.mark.asyncio
async def test_home_and_menu_are_localized() -> None:
    """The main screen should be Russian and visually richer."""

    player = Player(telegram_id=1, wallet=ResourceWallet(coins=7))
    text = menu_text(player)
    markup = main_menu_markup()

    assert "Добро пожаловать" in text
    assert "⚔️" in text
    buttons = _button_texts(markup)
    assert "👤 Профиль" in buttons
    assert "📖 Галерея" in buttons
    assert "💡 Идеи" in buttons
    assert "🏆 Топы" in buttons
    assert "⚔️ Бой" in buttons
    assert "🏁 Battle Pass" in buttons
    assert "🎁 Бесплатно" in buttons
    assert "🛠 Админка" not in buttons
    assert "🛠 Админка" in _button_texts(main_menu_markup(is_admin=True))
    assert "🗑 Удалить игрока" in _button_texts(admin_markup("players"))


@pytest.mark.asyncio
async def test_safe_edit_skips_duplicate_content() -> None:
    """Duplicate edits must not call the Telegram API."""

    message = Message(text="То же самое", reply_markup=None)
    with patch.object(
        Message, "edit_text", new=AsyncMock(return_value=message)
    ) as edit_text:
        await safe_edit(message, "То же самое")
        edit_text.assert_not_called()


@pytest.mark.asyncio
async def test_admin_screen_is_safe_and_changes_section() -> None:
    """Admin callbacks should skip duplicate edits and still render new sections."""

    services = TelegramServices()
    callback = CallbackQuery(
        from_user=User(1), message=Message(text="", reply_markup=admin_markup())
    )
    callback.message.text = admin_text(await services.admin_counts(), "dashboard")

    async def edit_side_effect(text, reply_markup=None):
        callback.message.text = text
        callback.message.reply_markup = reply_markup
        return callback.message

    with patch.object(
        Message, "edit_text", new=AsyncMock(side_effect=edit_side_effect)
    ) as edit_text:
        await show_admin(callback, services, "dashboard")
        edit_text.assert_not_called()

        await show_admin(callback, services, "cards")
        edit_text.assert_called_once()

    assert "Управление картами" in callback.message.text
    assert "Арена PvP" in battle_text(Player(telegram_id=1))


@pytest.mark.asyncio
async def test_card_collection_and_buttons_are_readable() -> None:
    """Card lists should use human-friendly Russian copy."""

    template = CardTemplate(
        id=1,
        name="Рейна",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("reina.png"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(
            cost=0,
            cooldown=0,
            effects=(AbilityEffect(AbilityTarget.SELF, AbilityStat.DEFENSE, 1, 2),),
        ),
    )
    card = PlayerCard(id=7, owner_player_id=1, template_id=1)

    text = cards_text([card], {1: template})
    markup = cards_markup([card])

    assert "Коллекция" in text
    assert "Рейна" in text
    assert "🎴 Карта #7" in _button_texts(markup)
    assert "⬅️ В меню" in _button_texts(battle_markup())
    assert "Пока пусто" in cards_text([], {})


@pytest.mark.asyncio
async def test_show_cards_renders_collection_list_without_crashing() -> None:
    """Collection view should use the list renderer, not single-card renderer."""

    services = TelegramServices()
    template = CardTemplate(
        id=1,
        name="Рейна",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("reina.png"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(cost=0, cooldown=0),
    )
    await services.card_templates.add(template)
    await services.player_cards.add(PlayerCard(id=7, owner_player_id=1, template_id=1))

    callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    await show_cards(callback, services, 1)

    assert callback.message.text is not None
    assert "Коллекция" in callback.message.text
    assert "Рейна" in callback.message.text


@pytest.mark.asyncio
async def test_card_gallery_and_collection_paginate_after_ten_items() -> None:
    """Gallery and collection screens should page through long card lists."""

    services = TelegramServices()
    template = CardTemplate(
        id=1,
        name="Рейна",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("reina.png"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(cost=0, cooldown=0),
    )
    await services.card_templates.add(template)
    for template_id in range(2, 12):
        await services.card_templates.add(
            CardTemplate(
                id=template_id,
                name=f"Карта {template_id}",
                universe=Universe.ORIGINAL,
                rarity=Rarity.RARE,
                image=ImageRef(f"card-{template_id}.png"),
                card_class=CardClass.MELEE,
                base_stats=StatBlock(10, 10, 10),
                ascended_stats=StatBlock(15, 15, 15),
                ability=Ability(cost=0, cooldown=0),
            )
        )
    for card_id in range(1, 12):
        await services.player_cards.add(
            PlayerCard(id=card_id, owner_player_id=1, template_id=1)
        )

    collection_callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    gallery_callback = CallbackQuery(from_user=User(1), message=Message(text="old"))

    await show_cards(collection_callback, services, 1, page=2)
    await show_gallery(gallery_callback, services, page=2)

    assert collection_callback.message.text is not None
    assert "2/2" in collection_callback.message.text
    assert "Рейна" in collection_callback.message.text
    assert "<code>11</code>" in collection_callback.message.text
    assert "➡️" not in _button_texts(collection_callback.message.reply_markup)
    assert "⬅️" in _button_texts(collection_callback.message.reply_markup)

    assert gallery_callback.message.text is not None
    assert "2/2" in gallery_callback.message.text
    assert "Карта 11" in gallery_callback.message.text
    assert "➡️" not in _button_texts(gallery_callback.message.reply_markup)
    assert "⬅️" in _button_texts(gallery_callback.message.reply_markup)


@pytest.mark.asyncio
async def test_show_card_detail_opens_from_collection_and_gallery() -> None:
    """Card detail callbacks should render a preview for both scopes."""

    services = TelegramServices()
    template = CardTemplate(
        id=1,
        name="Рейна",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("reina-file-id"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(cost=0, cooldown=0),
    )
    await services.card_templates.add(template)
    await services.player_cards.add(PlayerCard(id=7, owner_player_id=1, template_id=1))

    collection_callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    gallery_callback = CallbackQuery(from_user=User(1), message=Message(text="old"))

    await show_card_detail(collection_callback, services, 7, 1, page=1, scope="collection")
    await show_card_detail(gallery_callback, services, 1, 1, page=1, scope="gallery")

    assert collection_callback.message.answered_photo == "reina-file-id"
    assert "Карта" in (collection_callback.message.caption or "")
    assert gallery_callback.message.answered_photo == "reina-file-id"
    assert "Рейна" in (gallery_callback.message.caption or "")


@pytest.mark.asyncio
async def test_card_preview_falls_back_to_text_when_photo_send_fails() -> None:
    """Card detail screens should fall back to a document before text."""

    from aiogram.methods import SendPhoto

    callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    with patch.object(
        Message,
        "answer_photo",
        new=AsyncMock(
            side_effect=TelegramBadRequest(
                SendPhoto(chat_id=1, photo="broken-photo"),
                "bad photo",
            )
        ),
    ):
        await send_card_preview(
            callback,
            "broken-photo",
            "🎴 <b>Рейна</b>",
            content_type="image/png",
        )

    assert callback.message.answered_document == "broken-photo"
    assert callback.message.caption == "🎴 <b>Рейна</b>"


@pytest.mark.asyncio
async def test_card_image_accepts_photo_and_effects_are_human_friendly() -> None:
    """The wizard should accept Telegram photos and readable effect syntax."""

    from yuqa.telegram.router import _parse_effects
    from yuqa.telegram.texts import ability_effects_guide

    photo = [SimpleNamespace(file_id="photo-file-id")]
    message = Message(from_user=User(1), photo=photo)
    state = FSMContext()

    from yuqa.telegram.router import card_image

    await card_image(message, state)
    assert (await state.get_data())["image"] == "photo-file-id"

    effects = _parse_effects("OpponentDeck:Defense:100:-999")
    assert effects[0].target.value == "opponents_deck"
    assert effects[0].stat.value == "defense"
    assert effects[0].duration == 100
    assert effects[0].value == -999

    guide = ability_effects_guide()
    assert "TargetType" in guide and "StatType" in guide


@pytest.mark.asyncio
async def test_battle_markup_switches_between_search_and_cancel() -> None:
    """The battle screen should switch button text while searching."""

    assert "🔍 Поиск соперника" in _button_texts(battle_markup(False))
    assert "⏳ Отменить поиск" in _button_texts(battle_markup(True))
    assert "🧱 Конструктор колоды" in _button_texts(battle_markup(False))


def test_admin_banner_markup_has_delete_button_only_when_editable() -> None:
    """Delete-banner button should only appear for editable banners."""

    editable = _button_texts(admin_banner_markup(1, True))
    locked = _button_texts(admin_banner_markup(1, False))
    assert "🗑 Удалить баннер" in editable
    assert "🗑 Удалить баннер" not in locked


@pytest.mark.asyncio
async def test_show_free_rewards_renders_status_screen() -> None:
    """Free rewards screen should render both cooldown blocks."""

    services = TelegramServices()
    callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    await show_free_rewards(callback, services, 1)

    assert callback.message.text is not None
    assert "Бесплатные награды" in callback.message.text
    assert "Карта" in callback.message.text
    assert "Ресурсы" in callback.message.text


@pytest.mark.asyncio
async def test_show_deck_builder_renders_for_player_cards() -> None:
    """Deck constructor should render current draft and card toggles."""

    services = TelegramServices()
    template = CardTemplate(
        id=1,
        name="Рейна",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("reina.png"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(cost=0, cooldown=0),
    )
    await services.card_templates.add(template)
    for card_id in range(1, 6):
        await services.player_cards.add(
            PlayerCard(id=card_id, owner_player_id=1, template_id=1)
        )

    callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    await show_deck_builder(callback, services, 1)

    assert callback.message.text is not None
    assert "Конструктор колоды" in callback.message.text
    assert "0/5" in callback.message.text


@pytest.mark.asyncio
async def test_profile_and_top_texts_include_new_user_fields() -> None:
    """Profile and tops should render nicknames, titles, creator points, and backgrounds."""

    player = Player(
        telegram_id=1,
        nickname="alpha_one",
        title="The First",
        creator_points=77,
        owned_profile_background_ids=[5],
    )
    background = ProfileBackgroundTemplate(
        id=5,
        rarity=ProfileBackgroundRarity.EPIC,
        media=ImageRef("bg.png"),
    )
    top_text = tops_text(
        [type("Entry", (), {"rank": 1, "player": player, "value": 77})()],
        "creator_points",
    )
    profile = profile_text(player, None, background)

    assert "alpha_one" in profile
    assert "The First" in profile
    assert "Creator Points" in profile
    assert "#5" in profile
    assert "alpha_one" in top_text
    assert "77" in top_text
    assert "Creator Points" in top_text


@pytest.mark.asyncio
async def test_show_profile_uses_selected_background_media() -> None:
    """Profile view should send the selected background media when present."""

    services = TelegramServices()
    player = await services.get_or_create_player(1)
    player.nickname = "alpha_one"
    background = await services.create_profile_background(
        ProfileBackgroundRarity.EPIC,
        "bg-file-id",
    )
    player.grant_profile_background(background.id)
    player.selected_profile_background_id = background.id
    await services.players.save(player)

    message = Message(from_user=User(1), text="/profile")
    await show_profile(message, services, 1)

    assert message.answered_photo == "bg-file-id"
    assert message.caption is not None
    assert "alpha_one" in message.caption


@pytest.mark.asyncio
async def test_show_tops_renders_rating_leaderboard() -> None:
    """The top screen should render the requested leaderboard without crashing."""

    services = TelegramServices()
    player = await services.get_or_create_player(1)
    player.rating = 1500
    player.nickname = "alpha_one"

    callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    await show_tops(callback, services, "rating")

    assert callback.message.text is not None
    assert "Топ" in callback.message.text
    assert "alpha_one" in callback.message.text
    assert "Рейтинг" in "".join(sorted(_button_texts(tops_markup("rating"))))


@pytest.mark.asyncio
async def test_ideas_views_render_public_list_detail_and_collection() -> None:
    """Ideas pages should show public entries, details, and the author's collection."""

    services = TelegramServices()
    await services.set_player_nickname(1, "alpha_one")
    await services.set_player_title(1, "Inventor")
    public_idea = await services.propose_idea(
        1,
        "Draft Arena",
        "Players draft modifiers before each battle starts.",
    )
    await services.publish_idea(public_idea.id)
    await services.vote_for_idea(2, public_idea.id, 1)

    callback = CallbackQuery(from_user=User(3), message=Message(text="old"))
    await show_ideas(callback, services, 3)

    assert callback.message.text is not None
    assert "Идеи" in callback.message.text
    assert "Draft Arena" in callback.message.text

    await show_idea_detail(callback, services, public_idea.id, 3)
    assert callback.message.text is not None
    assert "alpha_one" in callback.message.text
    assert "Inventor" in callback.message.text
    assert "За" in "".join(sorted(_button_texts(callback.message.reply_markup)))

    await services.collect_idea(public_idea.id)
    owner_callback = CallbackQuery(from_user=User(1), message=Message(text="old"))
    await show_idea_collection(owner_callback, services, 1)

    assert owner_callback.message.text is not None
    assert "Моя коллекция" in owner_callback.message.text
    assert "Draft Arena" in owner_callback.message.text


@pytest.mark.asyncio
async def test_admin_ideas_section_renders_pending_list() -> None:
    """Admin ideas section should render moderation candidates without crashing."""

    services = TelegramServices()
    await services.propose_idea(
        1,
        "New mechanic",
        "A queued mechanic should appear in the admin moderation list.",
    )
    callback = CallbackQuery(from_user=User(1), message=Message(text="old"))

    await show_admin(callback, services, "ideas_pending")

    assert callback.message.text is not None
    assert "Идеи" in callback.message.text
    assert "New mechanic" in callback.message.text


def test_profile_backgrounds_text_handles_empty_collection() -> None:
    """Profile-background text should explain when the collection is empty."""

    assert "пустая" in profile_backgrounds_text([], None)


@pytest.mark.asyncio
async def test_card_preview_shows_photo_and_caption() -> None:
    """Card previews should send the image together with the stats caption."""

    template = CardTemplate(
        id=1,
        name="Рейна",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("reina-file-id"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(cost=0, cooldown=0),
    )
    message = Message(from_user=User(1))

    await send_card_preview(message, template.image.storage_key, "🎴 <b>Рейна</b>")

    assert message.answered_photo == "reina-file-id"
    assert "Рейна" in (message.caption or "")
