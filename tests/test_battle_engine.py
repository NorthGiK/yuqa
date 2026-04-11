"""Tests for the battle engine."""

from yuqa.battles.domain.actions import AttackAction, BlockAction, BonusAction, SwitchCardAction, UseAbilityAction
from yuqa.battles.domain.engine import BattleEngine
from yuqa.battles.domain.entities import Battle, BattleCardState, BattleSide
from yuqa.cards.domain.entities import Ability, AbilityEffect, CardTemplate
from yuqa.shared.enums import AbilityStat, AbilityTarget, BattleActionType, BattleStatus, CardClass, CardForm, Rarity, Universe
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.stat_block import StatBlock


def make_template():
    return CardTemplate(id=1, name="Soldier", universe=Universe.ORIGINAL, rarity=Rarity.COMMON, image=ImageRef("s.png"), card_class=CardClass.MELEE, base_stats=StatBlock(10, 1, 0), ascended_stats=StatBlock(10, 1, 0), ability=Ability(cost=0, cooldown=0, effects=(AbilityEffect(AbilityTarget.SELF, AbilityStat.DEFENSE, 1, 1),)))


def make_side(player_id: int, template: CardTemplate, start_id: int):
    cards = {start_id + index: BattleCardState(player_card_id=start_id + index, template=template, form=CardForm.BASE, max_health=template.base_stats.health, current_health=template.base_stats.health, damage=template.base_stats.damage, defense=template.base_stats.defense) for index in range(5)}
    return BattleSide(player_id=player_id, cards=cards, active_card_id=start_id)


def test_battle_engine_can_finish():
    template = make_template()
    battle = Battle(id=1, player_one_id=1, player_two_id=2, player_one_side=make_side(1, template, 100), player_two_side=make_side(2, template, 200))
    engine = BattleEngine()
    engine.start_battle(battle)
    killer = battle.first_turn_player_id
    victim = 2 if killer == 1 else 1
    for _ in range(5):
        engine.resolve_round(battle, actions_by_player={killer: [AttackAction(action_type=BattleActionType.ATTACK, ap_cost=1)], victim: []})
    assert battle.status == BattleStatus.FINISHED and battle.winner_id == killer


def test_battle_ap_rules_and_effects():
    template = make_template()
    battle = Battle(id=2, player_one_id=1, player_two_id=2, player_one_side=make_side(1, template, 300), player_two_side=make_side(2, template, 400))
    engine = BattleEngine()
    engine.start_battle(battle)
    killer = battle.first_turn_player_id
    active_card_id = battle.side_for(killer).active_card_id
    actions = [BonusAction(action_type=BattleActionType.BONUS, ap_cost=0, power_spent=2), BlockAction(action_type=BattleActionType.BLOCK, ap_cost=1, power_spent=1), UseAbilityAction(action_type=BattleActionType.USE_ABILITY, ap_cost=0, player_card_id=active_card_id), SwitchCardAction(action_type=BattleActionType.SWITCH_CARD, ap_cost=1, new_active_card_id=active_card_id + 1)]
    result = engine.resolve_round(battle, actions_by_player={killer: actions, 1 if killer == 2 else 2: []})
    assert result.battle.current_round == 2
