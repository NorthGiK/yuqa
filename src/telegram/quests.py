from datetime import timedelta

from src.quests import (
    QuestDefinition,
    QuestReward,
    QuestPeriod,
    QuestActionType,
)


_counter = 0

def _create_quest_definition(
    reward: QuestReward,
    period: QuestPeriod = QuestPeriod.DAILY,
    action_type: QuestActionType = QuestActionType.DAILY_ROUTINE,
    cooldown: timedelta = timedelta(days=1)
) -> QuestDefinition:
    global _counter
    _counter += 1
    
    return QuestDefinition(
        id=_counter,
        period=period,
        action_type=action_type,
        reward=reward,
        cooldown=cooldown,
    )

DAILITY_START = _create_quest_definition(QuestReward(coins=500))
