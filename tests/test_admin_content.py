"""Tests for the admin content wizard and local catalog storage."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.banners.domain.entities import Banner
from src.cards.domain.entities import Ability, AbilityEffect, PlayerCard
from src.quests.domain.entities import QuestReward
from src.shared.enums import (
    AbilityStat,
    AbilityTarget,
    BannerType,
    CardClass,
    CardForm,
    ProfileBackgroundRarity,
    ResourceType,
    Rarity,
    Universe,
)
from src.shared.errors import ForbiddenActionError
from src.shared.value_objects.date_range import DateRange
from src.shared.value_objects.deck_slots import DeckSlots
from src.shared.value_objects.resource_wallet import ResourceWallet
from src.shared.value_objects.stat_block import StatBlock
from src.telegram.callbacks import AdminCallback
from src.telegram.compat import CallbackQuery, FSMContext, Message, User
from src.telegram.config import Settings
from src.telegram.router import (
    build_router,
    capture_admin_player_card_player_id,
    capture_admin_player_card_template_id,
    card_ability_cost,
    card_ability_cooldown,
    card_ability_effects,
    card_ascended_effects,
    card_ascended_stats,
    card_base_stats,
    card_image,
    card_name,
    capture_clan_icon,
    capture_clan_name,
    capture_free_rewards_edit,
    start_admin_player_card_edit,
    start_card_create,
    start_clan_creation,
    start_free_rewards_edit,
)
from src.telegram.states import AdminPlayerCardEdit, CardCreate
from src.telegram.services.services import TelegramServices


@pytest.mark.asyncio
async def test_card_creation_wizard_can_finish_and_reset() -> None:
    """The admin should be able to create a card step by step and reset the flow."""

    services = TelegramServices()
    state = FSMContext()
    admin = User(1)

    await start_card_create(Message(from_user=admin, text="/admin"), state)
    assert state.state is not None

    await card_name(Message(from_user=admin, text="Рейна"), state)
    await card_image(
        Message(from_user=admin, photo=[SimpleNamespace(file_id="reina-file-id")]),
        state,
    )
    await state.update_data(
        universe=Universe.ORIGINAL.value,
        rarity=Rarity.EPIC.value,
        card_class=CardClass.MELEE.value,
    )
    await card_base_stats(Message(from_user=admin, text="10 20 5"), state)
    await card_ascended_stats(Message(from_user=admin, text="15 25 8"), state)
    await card_ability_cost(Message(from_user=admin, text="1"), state)
    await card_ability_cooldown(Message(from_user=admin, text="2"), state)
    await card_ability_effects(Message(from_user=admin, text="self:defense:1:2"), state)
    await card_ascended_effects(Message(from_user=admin, text="-"), services, state)

    assert len(services.card_templates.items) == 1
    assert services.card_templates.items[1].name == "Рейна"

    await start_card_create(Message(from_user=admin, text="/admin"), state)
    await state.clear()
    assert state.state is None


@pytest.mark.asyncio
async def test_card_wizard_can_pick_existing_universe_from_admin_callback() -> None:
    """The universe picker buttons should advance the card wizard."""

    services = TelegramServices()
    await services.add_universe("naruto")
    state = FSMContext()
    admin = User(1)

    await start_card_create(Message(from_user=admin, text="/admin"), state)
    await card_name(Message(from_user=admin, text="Рейна"), state, services)

    router = build_router(
        services,
        Settings(
            token="test-token",
            admin_ids={1},
            content_dir=None,
            database_url=None,
            auto_migrate=False,
        ),
    )
    if hasattr(router, "observers"):
        admin_actions = next(
            handler.callback
            for handler in router.observers["callback_query"].handlers
            if handler.callback.__name__ == "admin_actions"
        )
    else:
        admin_actions = next(
            callback
            for event_type, _filters, callback in router.handlers
            if event_type == "callback_query" and callback.__name__ == "admin_actions"
        )
    callback = CallbackQuery(from_user=admin, message=Message(from_user=admin, text=""))

    await admin_actions(
        callback,
        AdminCallback(action="card_universe_pick", value="naruto"),
        state,
    )

    assert state.state == CardCreate.rarity
    assert state.data["universe"] == "naruto"
    assert callback.message.text is not None
    assert "редкость" in callback.message.text


@pytest.mark.asyncio
async def test_standard_cards_only_affect_new_players() -> None:
    """Starter cards should be granted only to players created after the list is set."""

    services = TelegramServices()
    template = await services.create_card_template(
        name="Стартовый",
        universe=Universe.ORIGINAL,
        rarity=Rarity.COMMON,
        image_key="start.png",
        card_class=CardClass.SUPPORT,
        base_stats=StatBlock(1, 1, 1),
        ascended_stats=StatBlock(2, 2, 2),
        ability=Ability(
            0, 0, (AbilityEffect(AbilityTarget.SELF, AbilityStat.DEFENSE, 1, 1),)
        ),
    )

    old_player = await services.get_or_create_player(1)
    assert await services.list_player_cards(old_player.telegram_id) == []

    await services.set_standard_cards([template.id])
    new_player = await services.get_or_create_player(2)

    assert len(await services.list_player_cards(new_player.telegram_id)) == 1
    assert await services.list_player_cards(old_player.telegram_id) == []


@pytest.mark.asyncio
async def test_admin_can_grant_and_revoke_card_by_player_id() -> None:
    """Admin card flow should add and remove a template for a specific player id."""

    services = TelegramServices()
    template = await services.create_card_template(
        name="Админка",
        universe=Universe.ORIGINAL,
        rarity=Rarity.COMMON,
        image_key="admin.png",
        card_class=CardClass.SUPPORT,
        base_stats=StatBlock(1, 1, 1),
        ascended_stats=StatBlock(2, 2, 2),
        ability=Ability(0, 0),
    )
    state = FSMContext()
    admin = User(1)

    await start_admin_player_card_edit(
        Message(from_user=admin, text="/admin"), state, "add"
    )
    assert state.state == AdminPlayerCardEdit.player_id

    await capture_admin_player_card_player_id(
        Message(from_user=admin, text="42"), state
    )
    assert state.state == AdminPlayerCardEdit.template_id

    await capture_admin_player_card_template_id(
        Message(from_user=admin, text=str(template.id)), services, state
    )
    cards = await services.list_player_cards(42)
    assert len(cards) == 1
    assert cards[0].template_id == template.id

    await start_admin_player_card_edit(
        Message(from_user=admin, text="/admin"), state, "remove"
    )
    await capture_admin_player_card_player_id(
        Message(from_user=admin, text="42"), state
    )
    await capture_admin_player_card_template_id(
        Message(from_user=admin, text=str(template.id)), services, state
    )
    assert await services.list_player_cards(42) == []


@pytest.mark.asyncio
async def test_remove_card_from_player_cleans_deck_and_draft_for_last_copy() -> None:
    """Revoking the last owned copy should clean the saved deck and draft."""

    services = TelegramServices()
    removed_template = await services.create_card_template(
        name="Убираем",
        universe=Universe.ORIGINAL,
        rarity=Rarity.COMMON,
        image_key="remove.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(1, 2, 3),
        ascended_stats=StatBlock(4, 5, 6),
        ability=Ability(0, 0),
    )
    kept_template = await services.create_card_template(
        name="Оставляем",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="keep.png",
        card_class=CardClass.TANK,
        base_stats=StatBlock(2, 3, 4),
        ascended_stats=StatBlock(5, 6, 7),
        ability=Ability(0, 0),
    )

    player = await services.get_or_create_player(77)
    removed_card = await services.grant_card_to_player(
        player.telegram_id, removed_template.id
    )
    kept_cards = []
    for _ in range(4):
        kept_cards.append(
            await services.grant_card_to_player(player.telegram_id, kept_template.id)
        )

    kept_ids = {card.id for card in kept_cards}
    assert len(kept_ids) == 1
    extra_cards = []
    for card_id in (300, 301, 302, 303):
        extra = PlayerCard(
            id=card_id,
            owner_player_id=player.telegram_id,
            template_id=kept_template.id,
            level=1,
            copies_owned=1,
            current_form=CardForm.BASE,
        )
        await services.player_cards.add(extra)
        extra_cards.append(extra)
    player.collection_count = 5
    deck_ids = (removed_card.id, *(card.id for card in extra_cards))
    player.battle_deck = DeckSlots(deck_ids)
    services.deck_drafts[player.telegram_id] = list(deck_ids)

    await services.remove_card_from_player(player.telegram_id, removed_template.id)

    assert player.battle_deck is None
    assert services.deck_drafts[player.telegram_id] == [card.id for card in extra_cards]
    assert all(
        card.template_id == kept_template.id
        for card in await services.list_player_cards(player.telegram_id)
    )


@pytest.mark.asyncio
async def test_local_catalog_persists_models(tmp_path) -> None:
    """Local catalog content should survive service recreation."""

    catalog_path = tmp_path / "catalog.json"
    services = TelegramServices(catalog_path)

    template = await services.create_card_template(
        name="Локальная",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image_key="local.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 20, 5),
        ascended_stats=StatBlock(15, 25, 8),
        ability=Ability(
            0, 0, (AbilityEffect(AbilityTarget.SELF, AbilityStat.DEFENSE, 1, 2),)
        ),
    )
    background = await services.create_profile_background(
        ProfileBackgroundRarity.EPIC,
        "bg-local.png",
    )
    banner = await services.create_banner(
        "Событие",
        BannerType.EVENT,
        ResourceType.GOLD_TICKETS,
        datetime.now(timezone.utc) + timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=10),
    )
    await services.add_banner_reward_profile_background(
        banner.id, background.id, weight=5, guaranteed_for_10_pull=True
    )
    await services.create_shop_item(
        ResourceType.COINS, ResourceType.CRYSTALS, 100, 10, True
    )
    await services.set_standard_cards([template.id])
    await services.set_free_resource_values(
        {
            ResourceType.COINS: 2222,
            ResourceType.CRYSTALS: 33,
            ResourceType.ORBS: 4,
        }
    )

    reloaded = TelegramServices(catalog_path)

    assert reloaded.card_templates.items[template.id].name == "Локальная"
    assert (
        reloaded.profile_backgrounds.items[background.id].rarity
        == ProfileBackgroundRarity.EPIC
    )
    assert reloaded.banners.items[banner.id].name == "Событие"
    assert (
        reloaded.banners.items[banner.id].pools[0].profile_background_id
        == background.id
    )
    assert reloaded.shop.items[1].price == 100
    assert await reloaded.list_standard_cards() == [template.id]
    assert reloaded.free_reward_settings()["resource_values"]["coins"] == 2222

    player = await reloaded.get_or_create_player(99)
    assert len(await reloaded.list_player_cards(player.telegram_id)) == 1


@pytest.mark.asyncio
async def test_banner_pool_can_change_before_start_and_is_locked_after_start() -> None:
    """A banner should accept card pool edits only before the start moment."""

    services = TelegramServices()
    template = await services.create_card_template(
        name="Редкая",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="rare.png",
        card_class=CardClass.RANGER,
        base_stats=StatBlock(7, 8, 3),
        ascended_stats=StatBlock(9, 11, 4),
        ability=Ability(0, 0),
    )

    banner = await services.create_banner(
        "До старта",
        BannerType.NORMAL,
        ResourceType.SILVER_TICKETS,
        datetime.now(timezone.utc) + timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=3),
    )

    banner = await services.add_banner_reward_card(banner.id, template.id, 10, False)
    assert any(item.card_template_id == template.id for item in banner.pools)

    banner = await services.remove_banner_reward_card(banner.id, template.id)
    assert not any(item.card_template_id == template.id for item in banner.pools)

    started = Banner(
        id=99,
        name="Уже идёт",
        banner_type=BannerType.EVENT,
        cost_resource=ResourceType.GOLD_TICKETS,
        date_range=DateRange(
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc) + timedelta(days=1),
        ),
    )
    await services.banners.add(started)

    with pytest.raises(ForbiddenActionError):
        await services.add_banner_reward_card(started.id, template.id, 10, False)


@pytest.mark.asyncio
async def test_admin_can_delete_banner_before_start_or_while_active() -> None:
    """Banner deletion should work before start and while the banner is active."""

    services = TelegramServices()
    editable = await services.create_banner(
        "Скоро старт",
        BannerType.NORMAL,
        ResourceType.SILVER_TICKETS,
        datetime.now(timezone.utc) + timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=2),
    )
    await services.delete_banner(editable.id)
    assert editable.id not in services.banners.items

    started = await services.create_banner(
        "Уже стартовал",
        BannerType.EVENT,
        ResourceType.GOLD_TICKETS,
        datetime.now(timezone.utc) - timedelta(hours=1),
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    await services.delete_banner(started.id)
    assert started.id not in services.banners.items

    expired = Banner(
        id=100,
        name="Уже завершился",
        banner_type=BannerType.EVENT,
        cost_resource=ResourceType.GOLD_TICKETS,
        date_range=DateRange(
            datetime.now(timezone.utc) - timedelta(days=3),
            datetime.now(timezone.utc) - timedelta(days=1),
        ),
    )
    await services.banners.add(expired)

    with pytest.raises(ForbiddenActionError):
        await services.delete_banner(expired.id)


@pytest.mark.asyncio
async def test_clan_creation_flow_is_stepwise() -> None:
    """The clan wizard should collect the fields step by step."""

    services = TelegramServices()
    owner = await services.get_or_create_player(1)
    owner.rating = 1201
    owner.wallet = ResourceWallet(coins=10_000)
    state = FSMContext()

    await start_clan_creation(Message(from_user=User(1), text="/clan_create"), state)
    await capture_clan_name(Message(from_user=User(1), text="Shinobi"), state)
    await capture_clan_icon(Message(from_user=User(1), text="🐺"), services, state)

    assert owner.clan_id is not None
    assert services.players.items[1].clan_id == owner.clan_id


@pytest.mark.asyncio
async def test_admin_can_edit_free_reward_settings_via_wizard() -> None:
    """Admin free reward settings should be editable via the wizard helpers."""

    services = TelegramServices()
    state = FSMContext()

    await start_free_rewards_edit(
        Message(from_user=User(1), text="/admin"), state, "resource_values"
    )
    await capture_free_rewards_edit(
        Message(from_user=User(1), text="coins=5000 crystals=77 orbs=9"),
        services,
        state,
    )

    settings = services.free_reward_settings()
    assert settings["resource_values"]["coins"] == 5000
    assert settings["resource_values"]["crystals"] == 77
    assert settings["resource_values"]["orbs"] == 9


@pytest.mark.asyncio
async def test_admin_can_delete_shop_item() -> None:
    """Shop items should be removable from the admin panel."""

    services = TelegramServices()
    item = await services.create_shop_item(
        ResourceType.COINS, ResourceType.CRYSTALS, 100, 10, True
    )

    await services.remove_shop_item(item.id)

    assert item.id not in services.shop.items


@pytest.mark.asyncio
async def test_admin_can_delete_card_and_manage_universes() -> None:
    """Deleting cards should clean dependent content and universes should be editable."""

    services = TelegramServices()
    template = await services.create_card_template(
        name="Удаляемая",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="deleted.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(1, 2, 3),
        ascended_stats=StatBlock(4, 5, 6),
        ability=Ability(0, 0),
    )
    await services.set_standard_cards([template.id])
    player = await services.get_or_create_player(10)
    assert len(await services.list_player_cards(player.telegram_id)) == 1

    await services.delete_card_template(template.id)

    assert await services.get_template(template.id) is None
    assert await services.list_standard_cards() == []
    assert await services.list_player_cards(player.telegram_id) == []

    universes = await services.add_universe("myverse")
    assert "myverse" in universes
    universes = await services.remove_universe("myverse")
    assert "myverse" not in universes


@pytest.mark.asyncio
async def test_delete_card_template_cleans_saved_decks_and_runtime_drafts() -> None:
    """Deleting a template should drop removed cards from saved decks and drafts."""

    services = TelegramServices()
    removed_template = await services.create_card_template(
        name="Удаляемая",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="removed.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(1, 2, 3),
        ascended_stats=StatBlock(4, 5, 6),
        ability=Ability(0, 0),
    )
    kept_template = await services.create_card_template(
        name="Остается",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image_key="kept.png",
        card_class=CardClass.TANK,
        base_stats=StatBlock(2, 3, 4),
        ascended_stats=StatBlock(5, 6, 7),
        ability=Ability(0, 0),
    )

    player = await services.get_or_create_player(42)
    removed_card_id = 100
    kept_card_ids = [200, 201, 202, 203]
    await services.player_cards.add(
        PlayerCard(
            id=removed_card_id,
            owner_player_id=player.telegram_id,
            template_id=removed_template.id,
            level=1,
            copies_owned=1,
            current_form=CardForm.BASE,
        )
    )
    for card_id in kept_card_ids:
        await services.player_cards.add(
            PlayerCard(
                id=card_id,
                owner_player_id=player.telegram_id,
                template_id=kept_template.id,
                level=1,
                copies_owned=1,
                current_form=CardForm.BASE,
            )
        )
    player.collection_count = 5
    player.battle_deck = DeckSlots((removed_card_id, *kept_card_ids))
    services.deck_drafts[player.telegram_id] = [removed_card_id, *kept_card_ids]

    await services.delete_card_template(removed_template.id)

    assert player.battle_deck is None
    assert services.deck_drafts[player.telegram_id] == kept_card_ids
    remaining_cards = await services.list_player_cards(player.telegram_id)
    assert {card.id for card in remaining_cards} == set(kept_card_ids)
    assert player.collection_count == 4


@pytest.mark.asyncio
async def test_admin_can_add_battle_pass_level(tmp_path) -> None:
    """Battle pass levels should be addable and persist locally."""

    services = TelegramServices(tmp_path / "catalog.json")
    await services.add_battle_pass_level(
        4, 40, QuestReward(coins=123, crystals=4, orbs=1)
    )

    season = await services.active_battle_pass()
    assert season is not None
    assert any(
        level.level_number == 4 and level.required_points == 40
        for level in season.levels
    )

    reloaded = TelegramServices(tmp_path / "catalog.json")
    season = await reloaded.active_battle_pass()
    assert season is not None
    assert any(level.level_number == 4 for level in season.levels)


@pytest.mark.asyncio
async def test_admin_can_create_and_delete_battle_pass_season(tmp_path) -> None:
    """Ended battle passes should be removable and new ones should persist."""

    services = TelegramServices(tmp_path / "catalog.json")
    now = datetime.now(timezone.utc)

    future = await services.create_battle_pass_season(
        "Сезон 2",
        now + timedelta(days=40),
        now + timedelta(days=50),
    )
    assert future.name == "Сезон 2"

    ended = await services.create_battle_pass_season(
        "Архив",
        now - timedelta(days=20),
        now - timedelta(days=10),
    )
    await services.delete_battle_pass_season(ended.id)
    assert await services.battle_pass_seasons.get_by_id(ended.id) is None

    reloaded = TelegramServices(tmp_path / "catalog.json")
    assert await reloaded.battle_pass_seasons.get_by_id(future.id) is not None
