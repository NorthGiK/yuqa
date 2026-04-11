"""Tests for shared value objects and enums."""

import pytest

from yuqa.shared.enums import BattleActionType, CardForm, Rarity, ResourceType, RewardType, Universe
from yuqa.shared.errors import NotEnoughResourcesError, ValidationError
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.shared.value_objects.date_range import DateRange
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.probability import ProbabilityWeight
from yuqa.shared.value_objects.resource_wallet import ResourceWallet
from yuqa.shared.value_objects.stat_block import StatBlock


def test_enums_are_strings():
    assert Universe.ORIGINAL.value == "original"
    assert Rarity.EPIC.value == "epic"
    assert CardForm.BASE.value == "base"
    assert RewardType.CARD.value == "card"
    assert BattleActionType.ATTACK.value == "attack"


def test_value_objects_validate():
    DeckSlots((1, 2, 3, 4, 5))
    with pytest.raises(ValidationError):
        DeckSlots((1, 1, 3, 4, 5))
    StatBlock(1, 2, 3)
    ImageRef("image.png")
    ProbabilityWeight(1)
    DateRange()


def test_wallet_spend_and_add():
    wallet = ResourceWallet(coins=100)
    wallet.spend(ResourceType.COINS, 40)
    wallet.add(ResourceType.COINS, 10)
    assert wallet.coins == 70
    with pytest.raises(NotEnoughResourcesError):
        wallet.spend(ResourceType.COINS, 999)
