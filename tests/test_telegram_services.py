"""Tests for the Telegram presentation service container and battle start flow."""

from datetime import datetime, timedelta, timezone

import pytest

from yuqa.cards.domain.entities import Ability, AbilityEffect, CardTemplate, PlayerCard
from yuqa.battle_pass.domain.entities import BattlePassProgress
from yuqa.shared.enums import ProfileBackgroundRarity
from yuqa.shared.enums import (
    AbilityStat,
    AbilityTarget,
    BannerType,
    BattleStatus,
    CardClass,
    CardForm,
    IdeaStatus,
    Rarity,
    ResourceType,
    Universe,
)
from yuqa.shared.errors import (
    EntityNotFoundError,
    ForbiddenActionError,
    ValidationError,
)
from yuqa.shared.value_objects.date_range import DateRange
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.resource_wallet import ResourceWallet
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.telegram.compat import CommandObject, FSMContext, Message, User
from yuqa.telegram.router import (
    capture_admin_player_id,
    capture_admin_player_value,
    capture_battle_pass_level_number,
    capture_battle_pass_required_points,
    capture_battle_pass_reward,
    capture_clan_name,
    capture_clan_icon,
    capture_universe_add,
    capture_universe_remove,
    capture_admin_player_delete,
    start_battle,
    start_battle_pass_level_create,
    start_admin_player_edit,
    start_admin_player_delete,
    start_clan_creation,
    start_universe_create,
    start_universe_delete,
)
from yuqa.telegram.services import TelegramServices
from yuqa.telegram.texts import battle_started_text


@pytest.fixture()
def sample_template() -> CardTemplate:
    """Build a reusable card template for tests."""

    return CardTemplate(
        id=1,
        name="Hero",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("hero.png"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 10, 10),
        ascended_stats=StatBlock(15, 15, 15),
        ability=Ability(
            cost=0,
            cooldown=0,
            effects=(AbilityEffect(AbilityTarget.SELF, AbilityStat.DEFENSE, 1, 1),),
        ),
    )


@pytest.mark.asyncio
async def test_player_and_clan_flows() -> None:
    """The service container should create, join, and leave clans."""

    services = TelegramServices()

    owner = await services.get_or_create_player(1)
    owner.rating = 1200
    owner.wallet.coins = 10_000

    clan = await services.create_clan(1, "Shinobi", "🐺")
    assert clan.name == "Shinobi"
    assert owner.clan_id == clan.id

    member = await services.get_or_create_player(2)
    member.rating = 1200

    joined = await services.join_clan(2, clan.id)
    assert joined.id == clan.id
    assert member.clan_id == clan.id

    await services.leave_clan(2)
    assert member.clan_id is None


@pytest.mark.asyncio
async def test_admin_player_delete_flow_removes_related_state() -> None:
    """Deleting a player from the admin panel should clear their runtime state."""

    services = TelegramServices()
    state = FSMContext()
    admin = User(1)

    owner = await services.get_or_create_player(1)
    owner.rating = 1200
    owner.wallet.coins = 10_000
    clan = await services.create_clan(1, "Shinobi", "🐺")
    member = await services.get_or_create_player(2)
    member.rating = 1200
    await services.join_clan(2, clan.id)
    await services.player_cards.add(
        PlayerCard(
            id=1,
            owner_player_id=1,
            template_id=1,
            level=1,
            copies_owned=1,
            current_form=CardForm.BASE,
        )
    )
    services.search_queue[1] = owner.rating
    services.deck_drafts[1] = [1, 2, 3]
    services.action_events.append((1, "opened-admin"))
    services.battle_pass_progress.items[(1, 1)] = BattlePassProgress(
        player_id=1, season_id=1
    )

    await start_admin_player_delete(Message(from_user=admin, text="/admin"), state)
    assert state.state is not None

    await capture_admin_player_delete(
        Message(from_user=admin, text="1"), services, state
    )

    assert state.state is None
    assert await services.get_player(1) is None
    assert await services.get_player(2) is not None
    assert services.players.items[2].clan_id is None
    assert services.clans.items == {}
    assert services.player_cards.items == {}
    assert services.search_queue == {}
    assert services.deck_drafts == {}
    assert services.action_events == []
    assert services.battle_pass_progress.items == {}


@pytest.mark.asyncio
async def test_admin_player_delete_rejects_missing_player() -> None:
    """Deleting a missing player should surface a validation error."""

    services = TelegramServices()
    state = FSMContext()
    admin = User(1)

    with pytest.raises(EntityNotFoundError):
        await services.delete_player(99)

    await start_admin_player_delete(Message(from_user=admin, text="/admin"), state)
    await capture_admin_player_delete(
        Message(from_user=admin, text="99"), services, state
    )

    assert state.state is None
    assert await services.get_player(99) is None


@pytest.mark.asyncio
async def test_battle_can_start_and_is_saved(sample_template: CardTemplate) -> None:
    """A battle should be created from two valid five-card decks."""

    services = TelegramServices()
    await services.card_templates.add(sample_template)
    await services.card_templates.add(
        CardTemplate(
            id=2,
            name="Villain",
            universe=Universe.ORIGINAL,
            rarity=Rarity.RARE,
            image=ImageRef("villain.png"),
            card_class=CardClass.TANK,
            base_stats=StatBlock(8, 12, 7),
            ascended_stats=StatBlock(10, 15, 9),
            ability=Ability(cost=0, cooldown=0),
        )
    )

    for player_id in (1, 2):
        player = await services.get_or_create_player(player_id)
        player.wallet = ResourceWallet()
        player.battle_deck = DeckSlots(
            (
                player_id * 10 + 1,
                player_id * 10 + 2,
                player_id * 10 + 3,
                player_id * 10 + 4,
                player_id * 10 + 5,
            )
        )
        for index, card_id in enumerate(player.battle_deck.card_ids, start=1):
            await services.player_cards.add(
                PlayerCard(
                    id=card_id,
                    owner_player_id=player_id,
                    template_id=1 if index % 2 else 2,
                    level=1,
                    copies_owned=1,
                    current_form=CardForm.BASE,
                )
            )

    battle = await services.start_battle(1, 2)

    assert battle.status == BattleStatus.ACTIVE
    assert battle.first_turn_player_id in {1, 2}
    assert battle.id in services.battles.items
    assert battle_started_text(battle).startswith("💥 <b>Бой начался!</b>")


@pytest.mark.asyncio
async def test_battle_command_flow_works(sample_template: CardTemplate) -> None:
    """The /battle command should start a battle and answer with a useful message."""

    services = TelegramServices()
    await services.card_templates.add(sample_template)
    await services.card_templates.add(
        CardTemplate(
            id=2,
            name="Villain",
            universe=Universe.ORIGINAL,
            rarity=Rarity.RARE,
            image=ImageRef("villain.png"),
            card_class=CardClass.TANK,
            base_stats=StatBlock(8, 12, 7),
            ascended_stats=StatBlock(10, 15, 9),
            ability=Ability(cost=0, cooldown=0),
        )
    )

    for player_id in (1, 2):
        player = await services.get_or_create_player(player_id)
        player.battle_deck = DeckSlots(
            (
                player_id * 10 + 1,
                player_id * 10 + 2,
                player_id * 10 + 3,
                player_id * 10 + 4,
                player_id * 10 + 5,
            )
        )
        for index, card_id in enumerate(player.battle_deck.card_ids, start=1):
            await services.player_cards.add(
                PlayerCard(
                    id=card_id,
                    owner_player_id=player_id,
                    template_id=1 if index % 2 else 2,
                    level=1,
                    copies_owned=1,
                    current_form=CardForm.BASE,
                )
            )

    message = Message(from_user=User(1), text="/battle 2")
    await start_battle(message, services, CommandObject(args="2"))

    assert message.text is not None
    assert "Бой начался" in message.text
    assert services.battles.items


@pytest.mark.asyncio
async def test_clan_creation_flow_has_all_steps() -> None:
    """The clan creation flow should collect name and icon in two steps."""

    services = TelegramServices()
    owner = await services.get_or_create_player(1)
    owner.rating = 1201
    owner.wallet.coins = 10_000

    state = FSMContext()

    message = Message(from_user=User(1), text="/clan_create")
    await start_clan_creation(message, state)
    assert state.state is not None

    await capture_clan_name(Message(from_user=User(1), text="Shinobi"), state)
    assert state.data["name"] == "Shinobi"

    await capture_clan_icon(Message(from_user=User(1), text="🐺"), services, state)
    assert owner.clan_id is not None
    assert services.players.items[1].clan_id is not None


@pytest.mark.asyncio
async def test_matchmaking_finds_close_opponents_and_can_cancel(
    sample_template: CardTemplate,
) -> None:
    """Matchmaking should pair players within rating range and allow cancellation."""

    services = TelegramServices()
    await services.card_templates.add(sample_template)

    for player_id, rating in ((1, 1000), (2, 1070)):
        player = await services.get_or_create_player(player_id)
        player.rating = rating
        player.battle_deck = DeckSlots(
            (
                player_id * 10 + 1,
                player_id * 10 + 2,
                player_id * 10 + 3,
                player_id * 10 + 4,
                player_id * 10 + 5,
            )
        )
        for card_id in player.battle_deck.card_ids:
            await services.player_cards.add(
                PlayerCard(
                    id=card_id,
                    owner_player_id=player_id,
                    template_id=1,
                    level=1,
                    copies_owned=1,
                    current_form=CardForm.BASE,
                )
            )

    assert await services.search_battle(1) is None
    assert await services.is_searching(1)
    battle = await services.search_battle(2)

    assert battle is not None
    assert battle.status == BattleStatus.ACTIVE
    assert services.search_queue == {}
    assert battle.id in services.battles.items

    await services.search_battle(1)
    await services.cancel_battle_search(1)
    assert not await services.is_searching(1)


@pytest.mark.asyncio
async def test_deck_constructor_can_toggle_clear_and_save(
    sample_template: CardTemplate,
) -> None:
    """Players should be able to build and save a five-card battle deck."""

    services = TelegramServices()
    await services.card_templates.add(sample_template)

    player = await services.get_or_create_player(1)
    for card_id in range(1, 7):
        await services.player_cards.add(
            PlayerCard(
                id=card_id,
                owner_player_id=player.telegram_id,
                template_id=1,
                level=1,
                copies_owned=1,
                current_form=CardForm.BASE,
            )
        )

    assert await services.deck_draft(1) == []
    await services.toggle_deck_draft_card(1, 1)
    await services.toggle_deck_draft_card(1, 2)
    await services.toggle_deck_draft_card(1, 3)
    await services.toggle_deck_draft_card(1, 4)
    await services.toggle_deck_draft_card(1, 5)
    assert await services.deck_draft(1) == [1, 2, 3, 4, 5]

    with pytest.raises(ValidationError):
        await services.toggle_deck_draft_card(1, 6)

    saved = await services.save_deck_draft(1)
    assert saved.card_ids == (1, 2, 3, 4, 5)
    assert player.battle_deck is not None
    assert player.battle_deck.card_ids == (1, 2, 3, 4, 5)

    await services.clear_deck_draft(1)
    assert await services.deck_draft(1) == []


@pytest.mark.asyncio
async def test_card_progression_wrappers_work_through_telegram_services() -> None:
    """TelegramServices should expose card progression operations to the router."""

    services = TelegramServices()
    await services.card_templates.add(
        CardTemplate(
            id=1,
            name="Hero",
            universe=Universe.ORIGINAL,
            rarity=Rarity.EPIC,
            image=ImageRef("hero.png"),
            card_class=CardClass.MELEE,
            base_stats=StatBlock(10, 10, 10),
            ascended_stats=StatBlock(15, 15, 15),
            ability=Ability(cost=0, cooldown=0),
            ascended_ability=Ability(cost=0, cooldown=0),
        )
    )

    player = await services.get_or_create_player(1)
    player.wallet.coins = 2_000
    player.wallet.orbs = 10
    await services.player_cards.add(
        PlayerCard(
            id=1,
            owner_player_id=1,
            template_id=1,
            level=9,
            copies_owned=2,
            current_form=CardForm.BASE,
        )
    )

    leveled = await services.level_up_card(1, 1)
    assert leveled.level == 10
    assert leveled.copies_owned == 1
    assert player.wallet.coins == 2_000 - services.card_progression.level_up_cost

    ascended = await services.ascend_card(1, 1)
    assert ascended.is_ascended is True
    assert ascended.current_form == CardForm.ASCENDED

    toggled = await services.toggle_card_form(1, 1)
    assert toggled.current_form == CardForm.BASE


@pytest.mark.asyncio
async def test_free_rewards_grant_card_and_resources_with_cooldowns() -> None:
    """Free rewards should grant configured loot and then enforce a 2-hour cooldown."""

    services = TelegramServices()
    await services.card_templates.add(
        CardTemplate(
            id=1,
            name="Common Hero",
            universe=Universe.ORIGINAL,
            rarity=Rarity.COMMON,
            image=ImageRef("common.png"),
            card_class=CardClass.MELEE,
            base_stats=StatBlock(1, 1, 1),
            ascended_stats=StatBlock(2, 2, 2),
            ability=Ability(cost=0, cooldown=0),
        )
    )
    await services.set_free_card_weights(
        {
            Rarity.COMMON: 100,
            Rarity.RARE: 0,
            Rarity.EPIC: 0,
            Rarity.MYTHIC: 0,
            Rarity.LEGENDARY: 0,
            Rarity.GODLY: 0,
        }
    )
    await services.set_free_resource_weights(
        {
            ResourceType.COINS: 100,
            ResourceType.CRYSTALS: 0,
            ResourceType.ORBS: 0,
        }
    )
    await services.set_free_resource_values(
        {
            ResourceType.COINS: 777,
            ResourceType.CRYSTALS: 25,
            ResourceType.ORBS: 1,
        }
    )

    card, template = await services.claim_free_card(1)
    resource, amount = await services.claim_free_resources(1)
    player = await services.get_or_create_player(1)

    assert template.rarity == Rarity.COMMON
    assert card.template_id == template.id
    assert resource == ResourceType.COINS
    assert amount == 777
    assert player.wallet.coins == 777

    with pytest.raises(ValidationError):
        await services.claim_free_card(1)
    with pytest.raises(ValidationError):
        await services.claim_free_resources(1)

    player.last_free_card_claim_at = datetime.now(timezone.utc) - timedelta(
        hours=2, seconds=1
    )
    player.last_free_resources_claim_at = datetime.now(timezone.utc) - timedelta(
        hours=2, seconds=1
    )
    await services.claim_free_card(1)
    await services.claim_free_resources(1)


@pytest.mark.asyncio
async def test_battle_pass_progress_is_visible() -> None:
    """The active battle pass screen should expose the season and player points."""

    services = TelegramServices()
    player = await services.get_or_create_player(1)
    player.battle_pass_progress = [10, 15]

    season = await services.active_battle_pass()
    assert season is not None
    from yuqa.telegram.texts import battle_pass_text

    text = battle_pass_text(season, player)

    assert "Сезон 1" in text
    assert "25" in text


@pytest.mark.asyncio
async def test_profile_cosmetics_and_tops_work_through_services() -> None:
    """Players should be able to manage cosmetics and appear in multiple tops."""

    services = TelegramServices()
    badenko = await services.create_card_template(
        name="Badenko Hero",
        universe=Universe.ORIGINAL,
        rarity=Rarity.BADENKO,
        image_key="badenko.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(5, 5, 5),
        ascended_stats=StatBlock(6, 6, 6),
        ability=Ability(cost=0, cooldown=0),
    )

    player_one = await services.get_or_create_player(1)
    player_one.rating = 1400
    player_two = await services.get_or_create_player(2)
    player_two.rating = 1200

    await services.set_player_nickname(1, "alpha_one")
    await services.set_player_title(1, "The First")
    await services.add_creator_points(1, 50)
    await services.add_creator_points(2, 10)

    with pytest.raises(ValidationError):
        await services.set_player_nickname(2, "alpha_one")

    await services.player_cards.add(
        PlayerCard(id=1, owner_player_id=1, template_id=badenko.id)
    )
    await services.player_cards.add(
        PlayerCard(id=2, owner_player_id=1, template_id=badenko.id)
    )
    await services.player_cards.add(
        PlayerCard(id=3, owner_player_id=2, template_id=badenko.id)
    )

    background = await services.create_profile_background(
        ProfileBackgroundRarity.EPIC,
        "profile-bg.png",
    )
    assert player_one.grant_profile_background(background.id) is True
    await services.players.save(player_one)
    await services.select_profile_background(1, background.id)

    rating_top = await services.list_top_players("rating")
    badenko_top = await services.list_top_players("badenko_cards")
    creator_top = await services.list_top_players("creator_points")

    assert rating_top[0].player.telegram_id == 1
    assert badenko_top[0].player.telegram_id == 1
    assert badenko_top[0].value == 2
    assert creator_top[0].player.telegram_id == 1
    assert creator_top[0].value == 50
    assert player_one.selected_profile_background_id == background.id


@pytest.mark.asyncio
async def test_admin_panel_can_set_title_and_creator_points_by_player_id() -> None:
    """Admin editing should apply to the target player, not the caller."""

    services = TelegramServices()
    admin = User(1)
    target = await services.get_or_create_player(2)
    state = FSMContext()

    await start_admin_player_edit(
        Message(from_user=admin, text="/admin"), state, "creator_points"
    )
    await capture_admin_player_id(Message(from_user=admin, text="2"), state)
    await capture_admin_player_value(
        Message(from_user=admin, text="25"), services, state
    )

    assert target.creator_points == 25
    assert state.state is None

    await start_admin_player_edit(
        Message(from_user=admin, text="/admin"), state, "title"
    )
    await capture_admin_player_id(Message(from_user=admin, text="2"), state)
    await capture_admin_player_value(
        Message(from_user=admin, text="Champion"), services, state
    )

    assert target.title == "Champion"
    assert state.state is None


@pytest.mark.asyncio
async def test_banner_can_grant_profile_background_rewards() -> None:
    """Banner pulls should award profile backgrounds from the reward pool."""

    services = TelegramServices()
    background = await services.create_profile_background(
        ProfileBackgroundRarity.LEGENDARY,
        "legend-bg.png",
    )
    banner = await services.create_banner(
        "BG Banner",
        BannerType.EVENT,
        ResourceType.GOLD_TICKETS,
        datetime.now(timezone.utc) + timedelta(hours=1),
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    await services.add_banner_reward_profile_background(
        banner.id,
        background.id,
        weight=1,
        guaranteed_for_10_pull=False,
    )
    banner.date_range = DateRange(
        datetime.now(timezone.utc) - timedelta(hours=1),
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    player = await services.get_or_create_player(7)
    player.wallet.gold_tickets = 1

    rewards = await services.pull_banner(player.telegram_id, banner.id, 1)

    assert any("фон профиля" in reward for reward in rewards)
    assert background.id in player.owned_profile_background_ids


@pytest.mark.asyncio
async def test_battle_pass_wizard_walks_all_steps(tmp_path) -> None:
    """Battle Pass level creation should advance one clear step at a time."""

    services = TelegramServices(tmp_path / "catalog.json")
    state = FSMContext()

    message = Message(from_user=User(1), text="/admin")
    await start_battle_pass_level_create(message, state)

    assert state.state is not None
    assert "Добавление уровня Battle Pass" in message.answered_text

    await capture_battle_pass_level_number(Message(from_user=User(1), text="7"), state)
    assert state.data["level_number"] == 7
    assert state.state is not None

    await capture_battle_pass_required_points(
        Message(from_user=User(1), text="70"), state
    )
    assert state.data["required_points"] == 70
    assert state.state is not None

    await capture_battle_pass_reward(
        Message(from_user=User(1), text="100 5 1"), services, state
    )
    assert state.state is None

    season = await services.active_battle_pass()
    assert season is not None
    assert any(
        level.level_number == 7 and level.required_points == 70
        for level in season.levels
    )


@pytest.mark.asyncio
async def test_battle_pass_season_lifecycle(tmp_path) -> None:
    """Admins should be able to create future seasons and delete finished ones."""

    services = TelegramServices(tmp_path / "catalog.json")
    services.battle_pass_seasons.items.clear()
    now = datetime.now(timezone.utc)

    season = await services.create_battle_pass_season(
        "Season 2",
        now + timedelta(days=1),
        now + timedelta(days=10),
    )
    assert (await services.active_battle_pass()) is None

    ended = await services.create_battle_pass_season(
        "Archive",
        now - timedelta(days=10),
        now - timedelta(days=5),
    )
    await services.delete_battle_pass_season(ended.id)
    assert await services.battle_pass_seasons.get_by_id(ended.id) is None
    assert await services.battle_pass_seasons.get_by_id(season.id) is not None


@pytest.mark.asyncio
async def test_universe_wizard_adds_and_removes_names(tmp_path) -> None:
    """Universe admin helpers should add and delete local universe names."""

    services = TelegramServices(tmp_path / "catalog.json")
    state = FSMContext()

    await start_universe_create(Message(from_user=User(1), text="/admin"), state)
    assert state.state is not None

    await capture_universe_add(
        Message(from_user=User(1), text="newverse"), services, state
    )
    assert state.state is None
    assert "newverse" in await services.list_universes()

    await start_universe_delete(Message(from_user=User(1), text="/admin"), state)
    await capture_universe_remove(
        Message(from_user=User(1), text="newverse"), services, state
    )
    assert state.state is None
    assert "newverse" not in await services.list_universes()


@pytest.mark.asyncio
async def test_ideas_support_review_voting_pagination_and_collection() -> None:
    """Ideas should move through moderation, public voting, and player collection."""

    services = TelegramServices()
    await services.set_player_nickname(1, "alpha_one")
    await services.set_player_title(1, "Inventor")

    created_ids: list[int] = []
    for index in range(11):
        idea = await services.propose_idea(
            1,
            f"Idea {index + 1}",
            f"Detailed description for idea {index + 1}.",
        )
        await services.publish_idea(idea.id)
        created_ids.append(idea.id)

    await services.vote_for_idea(2, created_ids[0], 1)
    await services.vote_for_idea(3, created_ids[0], 1)
    await services.vote_for_idea(4, created_ids[1], -1)

    with pytest.raises(ForbiddenActionError):
        await services.vote_for_idea(2, created_ids[0], 1)

    page_one, has_prev, has_next = await services.list_ideas(
        IdeaStatus.PUBLISHED, page=1
    )
    page_two, second_prev, second_next = await services.list_ideas(
        IdeaStatus.PUBLISHED, page=2
    )

    assert len(page_one) == 10
    assert len(page_two) == 1
    assert has_prev is False and has_next is True
    assert second_prev is True and second_next is False
    assert page_one[0].id == created_ids[0]
    assert page_one[0].upvotes == 2
    assert page_one[1].id != created_ids[0]

    collected = await services.collect_idea(created_ids[0])
    rejected = await services.reject_idea(created_ids[1])

    assert collected.status == IdeaStatus.COLLECTED
    assert rejected.status == IdeaStatus.REJECTED

    public_ideas, _, _ = await services.list_ideas(IdeaStatus.PUBLISHED, page=1)
    collection, _, _ = await services.list_ideas(
        IdeaStatus.COLLECTED, page=1, player_id=1
    )

    assert created_ids[0] not in {idea.id for idea in public_ideas}
    assert created_ids[1] not in {idea.id for idea in public_ideas}
    assert [idea.id for idea in collection] == [created_ids[0]]


@pytest.mark.asyncio
async def test_ideas_persist_in_local_catalog(tmp_path) -> None:
    """Idea status and votes should survive catalog reloads."""

    path = tmp_path / "catalog.json"
    services = TelegramServices(path)
    idea = await services.propose_idea(
        7,
        "Persistent idea",
        "Persistent descriptions should survive service reloads.",
    )
    await services.publish_idea(idea.id)
    await services.vote_for_idea(9, idea.id, 1)

    reloaded = TelegramServices(path)
    ideas, has_prev, has_next = await reloaded.list_ideas(IdeaStatus.PUBLISHED)

    assert has_prev is False and has_next is False
    assert len(ideas) == 1
    assert ideas[0].title == "Persistent idea"
    assert ideas[0].upvotes == 1
