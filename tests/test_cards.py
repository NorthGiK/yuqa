"""Tests for card progression."""

import pytest

from yuqa.cards.domain.entities import Ability, AbilityEffect, CardTemplate, PlayerCard
from yuqa.cards.domain.services import CardProgressionService, get_effective_stats
from yuqa.shared.enums import (
    AbilityStat,
    AbilityTarget,
    CardClass,
    CardForm,
    Rarity,
    Universe,
)
from yuqa.shared.errors import ValidationError
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.resource_wallet import ResourceWallet
from yuqa.shared.value_objects.stat_block import StatBlock


def make_template() -> CardTemplate:
    return CardTemplate(
        id=1,
        name="Hero",
        universe=Universe.ORIGINAL,
        rarity=Rarity.EPIC,
        image=ImageRef("hero.png"),
        card_class=CardClass.MELEE,
        base_stats=StatBlock(10, 100, 5),
        ascended_stats=StatBlock(20, 200, 10),
        ability=Ability(
            cost=1,
            cooldown=1,
            effects=(AbilityEffect(AbilityTarget.SELF, AbilityStat.DEFENSE, 1, 2),),
        ),
        ascended_ability=Ability(
            cost=2,
            cooldown=2,
            effects=(
                AbilityEffect(AbilityTarget.TEAMMATES_DECK, AbilityStat.DAMAGE, 1, 3),
            ),
        ),
    )


def test_progression_flow():
    card = PlayerCard(id=10, owner_player_id=1, template_id=1, level=9, copies_owned=2)
    wallet = ResourceWallet(coins=2000, orbs=10)
    service = CardProgressionService()
    service.level_up(card, wallet)
    assert (
        card.level == 10
        and wallet.coins == 2000 - service.level_up_cost
        and card.copies_owned == 1
    )
    service.ascend(card, wallet)
    assert (
        card.is_ascended
        and card.current_form == CardForm.ASCENDED
        and wallet.orbs == 10 - service.ascend_orb_cost
    )
    service.toggle_form(card)
    assert card.current_form == CardForm.BASE


def test_invalid_progression_is_rejected():
    card = PlayerCard(id=1, owner_player_id=1, template_id=1)
    with pytest.raises(ValidationError):
        card.toggle_form()
    with pytest.raises(ValidationError):
        PlayerCard(id=2, owner_player_id=1, template_id=1, copies_owned=-1)


def test_effective_stats_switch_with_form():
    template = make_template()
    card = PlayerCard(
        id=10,
        owner_player_id=1,
        template_id=1,
        level=10,
        copies_owned=1,
        is_ascended=True,
        current_form=CardForm.ASCENDED,
    )
    assert get_effective_stats(template, card).damage == 20
