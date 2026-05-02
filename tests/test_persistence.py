"""Persistence tests for the database-backed runtime."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.quests import QuestDefinition, QuestPeriod
from src.cards.domain.entities import Ability
from src.cards.domain.entities import PlayerCard
from src.infrastructure.sqlalchemy.migrations import upgrade_head
from src.infrastructure.sqlalchemy.repositories import create_sync_engine
from src.infrastructure.sqlalchemy.urls import sync_database_url
from src.quests.domain.entities import QuestReward
from src.shared.enums import (
    CardClass,
    CardForm,
    IdeaStatus,
    QuestActionType,
    Rarity,
    ResourceType,
    Universe,
)
from src.shared.value_objects.deck_slots import DeckSlots
from src.shared.value_objects.stat_block import StatBlock
from src.telegram.services.services import TelegramServices


def _sqlite_url(path: Path) -> str:
    """Build a SQLite URL for a temporary database file."""

    return f"sqlite:///{path.resolve().as_posix()}"


def _async_sqlite_url(path: Path) -> str:
    """Build an async-driver SQLite URL for runtime compatibility tests."""

    return f"sqlite+aiosqlite:///{path.resolve().as_posix()}"


def test_sync_database_url_strips_async_sqlite_driver(tmp_path: Path) -> None:
    """Synchronous startup paths should not use the aiosqlite driver."""

    database_url = _async_sqlite_url(tmp_path / "yuqa.db")

    assert sync_database_url(database_url) == _sqlite_url(tmp_path / "yuqa.db")


def test_migrations_accept_async_sqlite_url(tmp_path: Path) -> None:
    """Auto-migration should work when DATABASE_URL names aiosqlite."""

    database_url = _async_sqlite_url(tmp_path / "yuqa.db")

    upgrade_head(database_url)
    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE name = 'state_documents'"
            ).all()
    finally:
        engine.dispose()

    assert rows == [("state_documents",)]


@pytest.mark.asyncio
async def test_database_services_persist_state_between_restarts(tmp_path: Path) -> None:
    """Runtime and catalog state should survive a service restart."""

    catalog_path = tmp_path / "catalog.json"
    database_url = _sqlite_url(tmp_path / "yuqa.db")
    upgrade_head(database_url)

    services = TelegramServices(catalog_path, database_url=database_url)
    template = await services.create_card_template(
        name="Persisted",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="persisted.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(5, 10, 3),
        ascended_stats=StatBlock(8, 12, 5),
        ability=Ability(0, 0),
    )
    await services.set_standard_cards([template.id])

    player = await services.get_or_create_player(1)
    player.rating = 777
    player.wallet.add(ResourceType.COINS, 321)
    await services.set_player_nickname(1, "persist_1")
    await services.propose_idea(1, "Persistent idea", "Should survive restart")
    player.battle_deck = DeckSlots((1, 2, 3, 4, 5))
    for card_id in player.battle_deck.card_ids:
        await services.player_cards.add(
            PlayerCard(
                id=card_id,
                owner_player_id=1,
                template_id=template.id,
                current_form=CardForm.BASE,
            )
        )
    draft = await services.deck_draft(1)
    await services.search_battle(1)
    await services.shutdown()

    reloaded = TelegramServices(catalog_path, database_url=database_url)
    reloaded_player = await reloaded.get_player(1)
    pending, _, _ = await reloaded.list_ideas(IdeaStatus.PENDING)

    assert reloaded_player is not None
    assert reloaded_player.rating == 777
    assert reloaded_player.wallet.coins == 321
    assert reloaded_player.nickname == "persist_1"
    assert reloaded.card_templates.items[template.id].name == "Persisted"
    assert len(await reloaded.list_player_cards(1)) == 5
    assert pending[0].title == "Persistent idea"
    assert reloaded.deck_drafts[1] == draft
    assert not await reloaded.is_searching(1)

    await reloaded.shutdown()


@pytest.mark.asyncio
async def test_database_services_clear_battles_on_restart(tmp_path: Path) -> None:
    """A fresh service boot should drop any lingering stored battles."""

    catalog_path = tmp_path / "catalog.json"
    database_url = _sqlite_url(tmp_path / "yuqa.db")
    upgrade_head(database_url)

    services = TelegramServices(catalog_path, database_url=database_url)
    template = await services.create_card_template(
        name="Battle",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="battle.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(5, 10, 3),
        ascended_stats=StatBlock(8, 12, 5),
        ability=Ability(0, 0),
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
        for card_id in player.battle_deck.card_ids:
            await services.player_cards.add(
                PlayerCard(
                    id=card_id,
                    owner_player_id=player_id,
                    template_id=template.id,
                    current_form=CardForm.BASE,
                )
            )
    battle = await services.start_battle(1, 2)
    assert battle.id in services.battles.items
    services.search_queue[3] = 999
    assert await services.is_searching(3)

    reloaded = TelegramServices(catalog_path, database_url=database_url)

    assert reloaded.battles.items == {}
    assert reloaded.search_queue == {}
    assert not await reloaded.is_searching(3)
    await services.shutdown()
    await reloaded.shutdown()


@pytest.mark.asyncio
async def test_database_services_persist_battle_results(tmp_path: Path) -> None:
    """Finished battle results should survive a database restart."""

    catalog_path = tmp_path / "catalog.json"
    database_url = _sqlite_url(tmp_path / "yuqa.db")
    upgrade_head(database_url)

    services = TelegramServices(catalog_path, database_url=database_url)
    attacker_template = await services.create_card_template(
        name="Attacker",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image_key="attacker.png",
        card_class=CardClass.MELEE,
        base_stats=StatBlock(100, 100, 0),
        ascended_stats=StatBlock(100, 100, 0),
        ability=Ability(0, 0),
    )
    defender_template = await services.create_card_template(
        name="Defender",
        universe=Universe.ORIGINAL,
        rarity=Rarity.RARE,
        image_key="defender.png",
        card_class=CardClass.TANK,
        base_stats=StatBlock(1, 1, 0),
        ascended_stats=StatBlock(1, 1, 0),
        ability=Ability(0, 0),
    )
    for player_id, template_id in (
        (1, attacker_template.id),
        (2, defender_template.id),
    ):
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
        for card_id in player.battle_deck.card_ids:
            await services.player_cards.add(
                PlayerCard(
                    id=card_id,
                    owner_player_id=player_id,
                    template_id=template_id,
                    current_form=CardForm.BASE,
                )
            )

    battle = await services.start_battle(1, 2)
    battle.first_turn_player_id = 1
    services._set_current_turn_player_id(battle, 1)
    battle.current_round = 5
    defender_side = battle.opponent_side_for(1)
    for card in defender_side.cards.values():
        if card.player_card_id != defender_side.active_card_id:
            card.current_health = 0
            card.alive = False
    await services.battles.save(battle)
    for _ in range(5):
        battle = await services.record_battle_action(1, "bonus")
    for _ in range(5):
        battle = await services.record_battle_action(2, "block")
    assert battle.current_round == 6
    for _ in range(5):
        battle = await services.record_battle_action(1, "attack")
    for _ in range(5):
        battle = await services.record_battle_action(1, "bonus")
    for _ in range(5):
        battle = await services.record_battle_action(2, "block")
    assert battle.status.value == "finished"

    await services.shutdown()

    reloaded = TelegramServices(catalog_path, database_url=database_url)
    player_one = await reloaded.get_player(1)
    player_two = await reloaded.get_player(2)

    assert player_one is not None
    assert player_two is not None
    assert player_one.wins == 1
    assert player_one.losses == 0
    assert player_one.draws == 0
    assert player_two.wins == 0
    assert player_two.losses == 1
    assert player_two.draws == 0

    await reloaded.shutdown()


@pytest.mark.asyncio
async def test_database_services_persist_quest_cooldowns(tmp_path: Path) -> None:
    """Quest cooldowns should survive a database-backed service restart."""

    catalog_path = tmp_path / "catalog.json"
    database_url = _sqlite_url(tmp_path / "quests.db")
    upgrade_head(database_url)
    started_at = datetime(2026, 5, 1, 10, tzinfo=timezone.utc)
    player_id = 500
    quest_id = 3
    reward = QuestReward(coins=10)

    services = TelegramServices(catalog_path, database_url=database_url)
    quest = QuestDefinition(
        id=quest_id,
        period=QuestPeriod.DAILY,
        action_type=QuestActionType.DAILY_ROUTINE,
        reward=reward,
        cooldown=timedelta(hours=1),
    )
    first = await services.complete_action_quest(
        player_id=player_id,
        quest=quest,
        now=started_at,
    )
    await services.shutdown()
    
    reloaded = TelegramServices(catalog_path, database_url=database_url)
    blocked = await reloaded.complete_action_quest(
        player_id=player_id,
        quest=quest,
        now=started_at + timedelta(minutes=30),
    )
    second = await reloaded.complete_action_quest(
        player_id=player_id,
        quest=quest,
        now=started_at + timedelta(hours=2),
    )
    player = await reloaded.get_player(player_id)
    progress = await reloaded.quests.get_progress(player_id, quest_id)
    
    assert first.completed
    assert blocked.completed is False
    assert second.completed
    assert player is not None
    assert player.wallet.coins == 20
    assert progress is not None
    assert progress.completed_count == 2
    
    await reloaded.shutdown()


@pytest.mark.asyncio
async def test_database_services_import_legacy_catalog_once(tmp_path: Path) -> None:
    """The first database boot should import the legacy catalog JSON."""
    
    catalog_path = tmp_path / "catalog.json"
    legacy = TelegramServices(catalog_path)
    template = await legacy.create_card_template(
        name="Legacy",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image_key="legacy.png",
        card_class=CardClass.SUPPORT,
        base_stats=StatBlock(2, 6, 1),
        ascended_stats=StatBlock(4, 8, 2),
        ability=Ability(0, 0),
    )
    await legacy.create_shop_item(
        ResourceType.COINS,
        ResourceType.CRYSTALS,
        100,
        5,
        True,
    )
    
    database_url = _sqlite_url(tmp_path / "import.db")
    upgrade_head(database_url)
    
    imported = TelegramServices(catalog_path, database_url=database_url)
    
    assert imported.card_templates.items[template.id].name == "Legacy"
    assert imported.shop.items[1].price == 100
    
    await imported.shutdown()
