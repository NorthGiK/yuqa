"""Persistence tests for the database-backed runtime."""

from pathlib import Path

import pytest

from yuqa.cards.domain.entities import Ability
from yuqa.cards.domain.entities import PlayerCard
from yuqa.infrastructure.sqlalchemy.migrations import upgrade_head
from yuqa.shared.enums import CardClass, CardForm, IdeaStatus, Rarity, ResourceType, Universe
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.telegram.services import TelegramServices


def _sqlite_url(path: Path) -> str:
    """Build a SQLite URL for a temporary database file."""

    return f"sqlite:///{path.resolve().as_posix()}"


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
