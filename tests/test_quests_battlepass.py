"""Tests for quests and battle pass."""

from datetime import datetime, timedelta, timezone

import pytest

from yuqa.battle_pass.domain.entities import (
    BattlePassLevel,
    BattlePassProgress,
    BattlePassSeason,
)
from yuqa.battle_pass.domain.services import BattlePassService
from yuqa.players.domain.entities import Player
from yuqa.quests.domain.entities import QuestDefinition, QuestProgress, QuestReward
from yuqa.quests.domain.services import QuestResetService, QuestService
from yuqa.shared.enums import QuestActionType, QuestPeriod
from yuqa.telegram.services.services import TelegramServices


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
