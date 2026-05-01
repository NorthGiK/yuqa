"""Tests for quests and battle pass."""

from datetime import datetime, timedelta, timezone

import pytest

from src.battle_pass.domain.entities import (
    BattlePassLevel,
    BattlePassProgress,
    BattlePassSeason,
)
from src.battle_pass.domain.services import BattlePassService
from src.players.domain.entities import Player
from src.quests.domain.entities import QuestDefinition, QuestProgress, QuestReward
from src.quests.domain.services import QuestResetService, QuestService
from src.shared.enums import QuestActionType, QuestPeriod
from src.telegram.services.services import TelegramServices


def test_quest_completion_and_reset():
    player = Player(telegram_id=1)
    quest = QuestDefinition(
        id=1,
        period=QuestPeriod.DAILY,
        action_type=QuestActionType.BATTLE_WIN,
        reward=QuestReward(coins=50, battle_pass_points=20),
    )
    progress = QuestProgress(player_id=1, quest_id=1)
    reward = QuestService().complete(player, quest, progress)
    assert (
        progress.completed
        and player.wallet.coins == 50
        and player.battle_pass_progress == [20]
        and reward.coins == 50
    )
    QuestResetService().reset_daily([progress])
    assert not progress.completed


def test_quest_completion_sets_cooldown_and_count() -> None:
    """Completing a quest should track count and next ready time."""

    completed_at = datetime(2026, 5, 1, 8, tzinfo=timezone.utc)
    quest = QuestDefinition(
        id=7,
        period=QuestPeriod.DAILY,
        action_type=QuestActionType.SHOP_PURCHASE,
        reward=QuestReward(crystals=3),
        cooldown=timedelta(hours=6),
    )
    player = Player(telegram_id=1)
    progress = QuestProgress(player_id=1, quest_id=7)

    result = QuestService().complete_if_ready(
        player,
        quest,
        progress,
        completed_at=completed_at,
    )
    blocked = QuestService().complete_if_ready(
        player,
        quest,
        progress,
        completed_at=completed_at + timedelta(hours=1),
    )

    assert result.completed
    assert result.cooldown_until == completed_at + timedelta(hours=6)
    assert blocked.completed is False
    assert player.wallet.crystals == 3
    assert progress.completed_count == 1


def test_battle_pass_rewards():
    season = BattlePassSeason(
        id=1,
        name="S1",
        start_at=datetime.now(timezone.utc) - timedelta(days=1),
        end_at=datetime.now(timezone.utc) + timedelta(days=1),
        levels=[
            BattlePassLevel(1, 10, QuestReward(coins=5)),
            BattlePassLevel(2, 20, QuestReward(coins=10)),
        ],
    )
    progress = BattlePassProgress(player_id=1, season_id=1, points=20)
    claimed = BattlePassService().claim_available_rewards(progress, season)
    assert claimed == [1, 2] and progress.claimed_levels == {1, 2}


@pytest.mark.asyncio
async def test_battle_pass_service_can_buy_next_level():
    season = BattlePassSeason(
        id=1,
        name="S1",
        start_at=datetime.now(timezone.utc) - timedelta(days=1),
        end_at=datetime.now(timezone.utc) + timedelta(days=1),
        levels=[
            BattlePassLevel(1, 10, QuestReward(coins=5, battle_pass_points=2)),
            BattlePassLevel(2, 20, QuestReward(coins=10)),
        ],
    )
    services = TelegramServices()
    services.battle_pass_seasons.items.clear()
    services.battle_pass_seasons.items[1] = season
    player = services.players.items.setdefault(1, Player(telegram_id=1))
    player.wallet.coins = 300

    bought_progress, level_number = await services.buy_battle_pass_level(1)
    assert level_number == 1
    assert bought_progress.claimed_levels == {1}


@pytest.mark.asyncio
async def test_action_quest_completion_respects_player_cooldown() -> None:
    """The service helper should grant rewards only after cooldown expiry."""

    services = TelegramServices()
    reward = QuestReward(coins=25, battle_pass_points=4)
    started_at = datetime(2026, 5, 1, 9, tzinfo=timezone.utc)

    first = await services.complete_action_quest(
        player_id=1,
        quest_id=101,
        action_type=QuestActionType.CARD_LEVEL_UP,
        reward=reward,
        cooldown=timedelta(hours=2),
        now=started_at,
    )
    blocked = await services.complete_action_quest(
        player_id=1,
        quest_id=101,
        action_type=QuestActionType.CARD_LEVEL_UP,
        reward=reward,
        cooldown=timedelta(hours=2),
        now=started_at + timedelta(minutes=30),
    )
    second = await services.complete_action_quest(
        player_id=1,
        quest_id=101,
        action_type=QuestActionType.CARD_LEVEL_UP,
        reward=reward,
        cooldown=timedelta(hours=2),
        now=started_at + timedelta(hours=2),
    )

    player = await services.get_player(1)
    progress = await services.quests.get_progress(1, 101)

    assert first.completed
    assert blocked.completed is False
    assert second.completed
    assert player is not None
    assert player.wallet.coins == 50
    assert player.battle_pass_progress == [4, 4]
    assert progress is not None
    assert progress.completed_count == 2
