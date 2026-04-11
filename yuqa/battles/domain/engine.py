"""Battle resolution engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from random import Random

from yuqa.battles.domain.actions import (
    AttackAction,
    BattleAction,
    BlockAction,
    SwitchCardAction,
    UseAbilityAction,
)
from yuqa.battles.domain.entities import Battle, StatModifier
from yuqa.cards.domain.entities import AbilityEffect
from yuqa.shared.enums import AbilityStat, AbilityTarget, BattleActionType, BattleStatus
from yuqa.shared.errors import BattleRuleViolationError, ValidationError


@dataclass(slots=True)
class BattlePlanResult:
    """Result wrapper returned by the engine."""

    battle: Battle
    log: list[str] = field(default_factory=list)


class BattleEngine:
    """Resolve a battle round by round."""

    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()

    def start_battle(self, battle: Battle) -> None:
        """Activate a waiting battle and choose the first turn."""

        battle.status = BattleStatus.ACTIVE
        battle.first_turn_player_id = self.rng.choice(
            [battle.player_one_id, battle.player_two_id]
        )
        battle.current_round = 1

    def resolve_round(
        self,
        battle: Battle,
        actions_by_player: dict[int, list[BattleAction]],
        timed_out_players: set[int] | None = None,
    ) -> BattlePlanResult:
        """Execute one round of planned actions."""

        if battle.status != BattleStatus.ACTIVE:
            raise BattleRuleViolationError("battle not active")
        timed_out_players = timed_out_players or set()
        order = [
            battle.first_turn_player_id,
            battle.player_two_id
            if battle.first_turn_player_id == battle.player_one_id
            else battle.player_one_id,
        ]
        log: list[str] = []
        for player_id in order:
            if player_id in timed_out_players:
                continue
            self._resolve_player_actions(
                battle, player_id, actions_by_player.get(player_id, []), log
            )
        self._tick_effects(battle)
        self._cleanup_dead_cards(battle)
        self._finish_if_needed(battle)
        battle.current_round += 1
        return BattlePlanResult(battle=battle, log=log)

    def _resolve_player_actions(
        self,
        battle: Battle,
        player_id: int,
        actions: list[BattleAction],
        log: list[str],
    ) -> None:
        """Resolve one player's action list."""

        side = battle.side_for(player_id)
        side.ensure_active_alive()
        spent_ap = 0
        used_ability = False
        switched = False
        bonus_ap = 0
        for action in actions:
            if action.ap_cost < 0 or action.ap_cost > 5:
                raise ValidationError("ap_cost must be between 0 and 5")
            if (
                spent_ap + action.ap_cost
                > self._round_ap(battle.current_round) + bonus_ap
            ):
                raise BattleRuleViolationError("cannot spend more AP than available")
            if action.action_type == BattleActionType.BONUS:
                bonus_ap += max(0, action.power_spent)
                spent_ap += action.ap_cost
                log.append(f"player {player_id} gains {bonus_ap} bonus AP")
                continue
            if action.action_type == BattleActionType.SWITCH_CARD:
                if switched:
                    raise BattleRuleViolationError(
                        "switch can be used only once per round"
                    )
                if (
                    not isinstance(action, SwitchCardAction)
                    or action.new_active_card_id is None
                ):
                    raise ValidationError("switch requires new_active_card_id")
                if (
                    action.new_active_card_id not in side.cards
                    or not side.cards[action.new_active_card_id].alive
                ):
                    raise BattleRuleViolationError("cannot switch to dead/unknown card")
                side.active_card_id = action.new_active_card_id
                switched = True
                spent_ap += action.ap_cost
                continue
            if action.action_type == BattleActionType.USE_ABILITY:
                if used_ability:
                    raise BattleRuleViolationError(
                        "ability can be used only once per round"
                    )
                if (
                    not isinstance(action, UseAbilityAction)
                    or action.player_card_id is None
                ):
                    raise ValidationError("ability requires player_card_id")
                self._use_ability(
                    battle, player_id, action.player_card_id, action.ap_cost, log
                )
                used_ability = True
                spent_ap += action.ap_cost
                continue
            if action.action_type == BattleActionType.ATTACK:
                if not isinstance(action, AttackAction):
                    raise ValidationError("attack action malformed")
                self._attack(battle, player_id, log)
                spent_ap += action.ap_cost
                continue
            if action.action_type == BattleActionType.BLOCK:
                if not isinstance(action, BlockAction):
                    raise ValidationError("block action malformed")
                self._block(battle, player_id, action.power_spent, log)
                spent_ap += action.ap_cost
                continue
            raise ValidationError("unsupported action")

    @staticmethod
    def _round_ap(round_number: int) -> int:
        """Return the base AP for a round."""

        return min(5, round_number)

    def _attack(self, battle: Battle, player_id: int, log: list[str]) -> None:
        """Deal damage to the opponent's active card."""

        attacker = battle.side_for(player_id).active_card()
        defender_side = battle.opponent_side_for(player_id)
        defender_side.ensure_active_alive()
        defender = defender_side.active_card()
        if not attacker.alive:
            raise BattleRuleViolationError("attacker is dead")
        damage = max(0, attacker.damage - defender.defense)
        defender.current_health -= damage
        log.append(f"player {player_id} attacks for {damage}")

    def _block(
        self, battle: Battle, player_id: int, power_spent: int, log: list[str]
    ) -> None:
        """Add a short-lived defense modifier."""

        active = battle.side_for(player_id).active_card()
        active.effect_modifiers.append(
            StatModifier(
                stat=AbilityStat.DEFENSE, value=max(0, power_spent), remaining_rounds=1
            )
        )
        active.recalc()
        log.append(f"player {player_id} blocks +{power_spent} defense")

    def _use_ability(
        self,
        battle: Battle,
        player_id: int,
        player_card_id: int,
        ap_cost: int,
        log: list[str],
    ) -> None:
        """Apply the current card ability."""

        side = battle.side_for(player_id)
        active = side.active_card()
        if active.player_card_id != player_card_id:
            raise BattleRuleViolationError("ability can only be used by active card")
        ability = active.template.ability_for(active.form)
        if ability.cost > ap_cost:
            raise BattleRuleViolationError("Не достаточно Очков Действия для способности")
        for effect in ability.effects:
            self._apply_effect(battle, player_id, effect, log)

    def _apply_effect(
        self, battle: Battle, player_id: int, effect: AbilityEffect, log: list[str]
    ) -> None:
        """Apply one ability effect immediately or queue it for later."""

        if effect.target == AbilityTarget.SELF:
            targets = [battle.side_for(player_id).active_card()]
        elif effect.target == AbilityTarget.TEAMMATES_DECK:
            targets = battle.side_for(player_id).alive_cards()
        else:
            battle.pending_enemy_effects.append(
                (
                    player_id,
                    StatModifier(
                        stat=effect.stat,
                        value=effect.value,
                        remaining_rounds=effect.duration,
                    ),
                )
            )
            log.append(f"queue enemy effect {effect.stat.value} {effect.value}")
            return
        for target in targets:
            target.effect_modifiers.append(
                StatModifier(
                    stat=effect.stat,
                    value=effect.value,
                    remaining_rounds=effect.duration,
                )
            )
            target.recalc()
        log.append(f"apply effect {effect.stat.value} {effect.value}")

    def _tick_effects(self, battle: Battle) -> None:
        """Decrease effect timers and apply delayed enemy effects."""

        for player_id, modifier in list(battle.pending_enemy_effects):
            targets = battle.opponent_side_for(player_id).alive_cards()
            for target in targets:
                target.effect_modifiers.append(
                    StatModifier(
                        stat=modifier.stat,
                        value=modifier.value,
                        remaining_rounds=modifier.remaining_rounds,
                    )
                )
                target.recalc()
        battle.pending_enemy_effects.clear()
        for side in (battle.player_one_side, battle.player_two_side):
            for card in side.cards.values():
                for modifier in card.effect_modifiers:
                    modifier.remaining_rounds -= 1
                card.effect_modifiers = [
                    modifier
                    for modifier in card.effect_modifiers
                    if modifier.remaining_rounds > 0
                ]
                card.recalc()

    @staticmethod
    def _cleanup_dead_cards(battle: Battle) -> None:
        """Mark cards with zero health as dead and move active pointers if needed."""

        for side in (battle.player_one_side, battle.player_two_side):
            for card in side.cards.values():
                if card.current_health <= 0:
                    card.alive = False
                    card.current_health = 0
            side.ensure_active_alive()

    @staticmethod
    def _finish_if_needed(battle: Battle) -> None:
        """Finish the battle when one side has no surviving cards."""

        p1_alive = any(card.alive for card in battle.player_one_side.cards.values())
        p2_alive = any(card.alive for card in battle.player_two_side.cards.values())
        if p1_alive and p2_alive:
            return
        battle.status = BattleStatus.FINISHED
        battle.winner_id = (
            battle.player_one_id
            if p1_alive
            else battle.player_two_id
            if p2_alive
            else None
        )
        battle.finished_at = datetime.now(timezone.utc)
