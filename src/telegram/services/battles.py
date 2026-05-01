"""Battle and matchmaking operations for TelegramServices."""

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.battles.domain.actions import (
    AttackAction,
    BattleAction,
    BlockAction,
    BonusAction,
    SwitchCardAction,
    UseAbilityAction,
)
from src.battles.domain.entities import Battle, BattleCardState, BattleSide
from src.players.domain.entities import Player
from src.shared.enums import BattleActionType
from src.shared.errors import (
    BattleRuleViolationError,
    EntityNotFoundError,
    ValidationError,
)
from src.telegram.services.contracts import TelegramServiceContext
from src.telegram.services.support import BattleRoundSummary, _next_id


if TYPE_CHECKING:

    class _BattleServiceMixinBase(TelegramServiceContext):
        """Type-only base for mixin attribute and method completion."""

else:

    class _BattleServiceMixinBase:
        """Runtime base without protocol method stubs."""


class BattleServiceMixin(_BattleServiceMixinBase):
    """Battle creation, round drafting, and matchmaking helpers."""

    @staticmethod
    def _base_round_ap(round_number: int) -> int:
        """Return the non-bonus action-point budget for the round."""

        return min(5, round_number)

    async def start_battle(self, player_one_id: int, player_two_id: int) -> Battle:
        """Create and activate a new PvP battle."""

        if player_one_id == player_two_id:
            raise ValidationError("cannot battle yourself")
        player_one = await self.get_or_create_player(player_one_id)
        player_two = await self.get_or_create_player(player_two_id)
        battle = Battle(
            id=await self._next_battle_id(),
            player_one_id=player_one.telegram_id,
            player_two_id=player_two.telegram_id,
            player_one_side=await self._battle_side_for(player_one),
            player_two_side=await self._battle_side_for(player_two),
        )
        self.battle_engine.start_battle(battle)
        await self.battles.add(battle)
        self._set_current_turn_player_id(battle, battle.first_turn_player_id)
        self._start_battle_round(battle)
        return battle

    async def get_active_battle(self, telegram_id: int) -> Battle | None:
        """Return the active battle for one player, if any."""

        return await self.battles.get_active_by_player(telegram_id)

    def _battle_round_key(
        self, battle_id: int, round_number: int, player_id: int
    ) -> tuple[int, int, int]:
        """Return the lookup key for one round draft."""

        return battle_id, round_number, player_id

    def _battle_round_actions(
        self, battle_id: int, round_number: int, player_id: int
    ) -> list[BattleAction]:
        """Return the pending actions for one player in one round."""

        return self.battle_action_drafts.setdefault(
            self._battle_round_key(battle_id, round_number, player_id),
            [],
        )

    def _battle_round_totals(
        self, battle: Battle, player_id: int
    ) -> tuple[int, int, int, bool, int]:
        """Return the current draft totals for one player."""

        actions = self.battle_action_drafts.get(
            self._battle_round_key(battle.id, battle.current_round, player_id),
            [],
        )
        attack_count = 0
        block_count = 0
        bonus_count = 0
        ability_used = False
        spent_ap = 0
        for action in actions:
            spent_ap += action.ap_cost
            if action.action_type == BattleActionType.ATTACK:
                attack_count += 1
            elif action.action_type == BattleActionType.BLOCK:
                block_count += 1
            elif action.action_type == BattleActionType.BONUS:
                bonus_count += 1
            elif action.action_type == BattleActionType.USE_ABILITY:
                ability_used = True
        return attack_count, block_count, bonus_count, ability_used, spent_ap

    def _bonus_carryover_points(self, battle: Battle, player_id: int) -> int:
        """Return bonus AP granted from the previous resolved round."""

        return self.battle_bonus_carryover.get(
            self._battle_round_key(battle.id, battle.current_round, player_id),
            0,
        )

    def _set_current_turn_player_id(self, battle: Battle, player_id: int) -> None:
        """Remember which player may currently draft actions."""

        self.battle_current_turn_player_ids[battle.id] = player_id
        battle.current_turn_player_id = player_id

    def _battle_action_lock(self, battle_id: int) -> asyncio.Lock:
        """Return a per-battle lock used to serialize combat mutations."""

        lock = self.battle_action_locks.get(battle_id)
        if lock is None:
            lock = asyncio.Lock()
            self.battle_action_locks[battle_id] = lock
        return lock

    def _has_switch_target(self, battle: Battle, player_id: int) -> bool:
        """Return True when the player can switch to a different alive card."""

        side = battle.side_for(player_id)
        return any(
            card.alive and card.player_card_id != side.active_card_id
            for card in side.cards.values()
        )

    def _current_turn_player_id(self, battle: Battle) -> int:
        """Return the player who is currently allowed to draft actions."""

        first_player_id = battle.first_turn_player_id or battle.player_one_id
        opponent_id = battle.opponent_side_for(first_player_id).player_id
        first_total_action_points = (
            self._base_round_ap(battle.current_round)
            + self._bonus_carryover_points(battle, first_player_id)
        )
        opponent_total_action_points = (
            self._base_round_ap(battle.current_round)
            + self._bonus_carryover_points(battle, opponent_id)
        )
        (
            _first_attack_count,
            _first_block_count,
            _first_bonus_count,
            _first_ability_used,
            first_spent_ap,
        ) = self._battle_round_totals(battle, first_player_id)
        (
            _opponent_attack_count,
            _opponent_block_count,
            _opponent_bonus_count,
            _opponent_ability_used,
            opponent_spent_ap,
        ) = self._battle_round_totals(battle, opponent_id)
        inferred_turn_player_id = (
            first_player_id
            if first_spent_ap < first_total_action_points
            else opponent_id
            if opponent_spent_ap < opponent_total_action_points
            else None
        )
        current_turn_player_id = self.battle_current_turn_player_ids.get(battle.id)
        if (
            inferred_turn_player_id is not None
            and current_turn_player_id == inferred_turn_player_id
        ):
            battle.current_turn_player_id = current_turn_player_id
            return current_turn_player_id
        if inferred_turn_player_id is not None:
            battle.current_turn_player_id = inferred_turn_player_id
            self.battle_current_turn_player_ids[battle.id] = inferred_turn_player_id
            return inferred_turn_player_id
        if current_turn_player_id in {battle.player_one_id, battle.player_two_id}:
            battle.current_turn_player_id = current_turn_player_id
            return current_turn_player_id
        battle.current_turn_player_id = first_player_id
        self.battle_current_turn_player_ids[battle.id] = first_player_id
        return first_player_id

    def _battle_round_summary(
        self, battle: Battle, player_id: int
    ) -> BattleRoundSummary:
        """Summarize one player's draft for the current round."""

        (
            attack_count,
            block_count,
            bonus_count,
            ability_used,
            spent_ap,
        ) = self._battle_round_totals(battle, player_id)
        actions = self.battle_action_drafts.get(
            self._battle_round_key(battle.id, battle.current_round, player_id),
            [],
        )
        active_card = battle.side_for(player_id).active_card()
        ability_cost = active_card.template.ability_for(active_card.form).cost
        ability_cooldown_remaining = active_card.ability_cooldown_remaining
        base_ap = self._base_round_ap(battle.current_round)
        carryover_bonus = self._bonus_carryover_points(battle, player_id)
        total_action_points = base_ap + carryover_bonus
        available_action_points = max(0, total_action_points - spent_ap)
        opponent_id = battle.opponent_side_for(player_id).player_id
        (
            _opponent_attacks,
            _opponent_blocks,
            _opponent_bonuses,
            _opponent_ability_used,
            opponent_spent_ap,
        ) = self._battle_round_totals(battle, opponent_id)
        current_turn_player_id = self._current_turn_player_id(battle)
        if player_id != current_turn_player_id:
            available_action_points = 0
        return BattleRoundSummary(
            current_turn_player_id=current_turn_player_id,
            is_player_turn=player_id == current_turn_player_id,
            attack_count=attack_count,
            block_count=block_count,
            bonus_count=bonus_count,
            ability_used=ability_used,
            available_action_points=available_action_points,
            total_action_points=total_action_points,
            opponent_spent_action_points=opponent_spent_ap,
            ability_cost=ability_cost,
            ability_cooldown_remaining=ability_cooldown_remaining,
            can_switch=not actions
            and available_action_points > 0
            and self._has_switch_target(battle, player_id),
        )

    async def _apply_battle_result(self, battle: Battle) -> None:
        """Persist the final win/loss/draw outcome for both players."""

        if battle.status.value != "finished":
            return
        player_one = await self.get_or_create_player(battle.player_one_id)
        player_two = await self.get_or_create_player(battle.player_two_id)
        if battle.winner_id is None:
            player_one.add_draw()
            player_two.add_draw()
        elif battle.winner_id == battle.player_one_id:
            player_one.add_win()
            player_two.add_loss()
        else:
            player_two.add_win()
            player_one.add_loss()
        await self.players.save(player_one)
        await self.players.save(player_two)

    def battle_round_summary(
        self, battle: Battle, player_id: int
    ) -> BattleRoundSummary:
        """Expose the current round summary for Telegram presentation."""

        return self._battle_round_summary(battle, player_id)

    def _clear_battle_round_drafts(self, battle_id: int) -> None:
        """Drop all drafts for a battle."""

        self.battle_action_drafts = {
            key: value
            for key, value in self.battle_action_drafts.items()
            if key[0] != battle_id
        }
        self._cancel_battle_timeout_task(battle_id)
        self.battle_round_started_at.pop(battle_id, None)

    def _clear_battle_runtime_state(self, battle_id: int) -> None:
        """Drop every runtime-only entry for a finished or deleted battle."""

        self._clear_battle_round_drafts(battle_id)
        self.battle_inactive_rounds = {
            key: value
            for key, value in self.battle_inactive_rounds.items()
            if key[0] != battle_id
        }
        self.battle_bonus_carryover = {
            key: value
            for key, value in self.battle_bonus_carryover.items()
            if key[0] != battle_id
        }
        self.battle_current_turn_player_ids.pop(battle_id, None)
        self.battle_action_locks.pop(battle_id, None)

    def _clear_all_battles(self) -> None:
        """Remove every stored battle, queue entry, and round draft."""

        if self.battles.items:
            self.battles.items.clear()
        if self.search_queue:
            self.search_queue.clear()
        self.battle_action_drafts.clear()
        self.battle_bonus_carryover.clear()
        self.battle_current_turn_player_ids.clear()
        self.battle_action_locks.clear()
        for battle_id in list(self.battle_timeout_tasks):
            self._cancel_battle_timeout_task(battle_id)
        self.battle_round_started_at.clear()
        self.battle_inactive_rounds.clear()
        if self.store is not None:
            self.store.save()

    def _start_battle_round(self, battle: Battle) -> None:
        """Remember the current phase start and optionally schedule a timeout."""

        self._current_turn_player_id(battle)
        self.battle_round_started_at[battle.id] = datetime.now(timezone.utc)
        self._cancel_battle_timeout_task(battle.id)
        if not self.enable_background_battle_timers:
            return
        self.battle_timeout_tasks[battle.id] = asyncio.create_task(
            self._battle_round_timeout_worker(battle.id, battle.current_round)
        )

    def _cancel_battle_timeout_task(self, battle_id: int) -> None:
        """Cancel the background timeout task for one battle."""

        task = self.battle_timeout_tasks.pop(battle_id, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    async def _battle_round_timeout_worker(
        self, battle_id: int, round_number: int
    ) -> None:
        """Resolve one round after the configured timeout."""

        try:
            await asyncio.sleep(self.battle_round_timeout_seconds)
            battle = await self.battles.get_by_id(battle_id)
            if battle is None or battle.status.value != "active":
                return
            async with self._battle_action_lock(battle_id):
                battle = await self.battles.get_by_id(battle_id)
                if battle is None or battle.status.value != "active":
                    return
                if battle.current_round != round_number:
                    return
                current_turn_player_id = self._current_turn_player_id(battle)
                if current_turn_player_id == battle.first_turn_player_id:
                    battle = await self._advance_battle_turn(
                        battle, notify_timeout=False
                    )
                else:
                    battle = await self._resolve_current_round(
                        battle,
                        notify_timeout=False,
                    )
            if (
                battle.status.value == "active"
                and self.battle_timeout_notifier is not None
            ):
                await self.battle_timeout_notifier(
                    battle,
                    reason="⌛ Время на ход вышло. Новый ход уже начался.",
                )
            elif self.battle_timeout_notifier is not None:
                await self.battle_timeout_notifier(
                    battle,
                    reason="⌛ Время на ход вышло. Бой завершён.",
                )
        except asyncio.CancelledError:
            raise
        finally:
            task = self.battle_timeout_tasks.get(battle_id)
            if task is asyncio.current_task():
                self.battle_timeout_tasks.pop(battle_id, None)

    async def _resolve_expired_round_if_needed(self, battle: Battle) -> Battle:
        """Finish the current round immediately when its timer already expired."""

        started_at = self.battle_round_started_at.get(battle.id)
        if started_at is None or battle.status.value != "active":
            return battle
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        if elapsed < self.battle_round_timeout_seconds:
            return battle
        return await self._resolve_current_round(
            battle,
            notify_timeout=False,
            reason="⌛ Время на ход вышло. Раунд завершён автоматически.",
        )

    async def _advance_battle_turn(
        self,
        battle: Battle,
        *,
        notify_timeout: bool,
        reason: str | None = None,
    ) -> Battle:
        """Pass the current round from the first player to the second player."""

        if battle.status.value != "active":
            return battle
        current_turn_player_id = self._current_turn_player_id(battle)
        next_player_id = battle.opponent_side_for(current_turn_player_id).player_id
        self._set_current_turn_player_id(battle, next_player_id)
        self._start_battle_round(battle)
        await self.battles.save(battle)
        if notify_timeout and self.battle_timeout_notifier is not None:
            with suppress(Exception):
                await self.battle_timeout_notifier(battle, reason=reason)
        return battle

    async def _resolve_current_round(
        self,
        battle: Battle,
        *,
        notify_timeout: bool,
        reason: str | None = None,
    ) -> Battle:
        """Resolve the current round from drafted actions."""

        actions_by_player = {
            battle.player_one_id: list(
                self.battle_action_drafts.get(
                    self._battle_round_key(
                        battle.id, battle.current_round, battle.player_one_id
                    ),
                    [],
                )
            ),
            battle.player_two_id: list(
                self.battle_action_drafts.get(
                    self._battle_round_key(
                        battle.id, battle.current_round, battle.player_two_id
                    ),
                    [],
                )
            ),
        }
        carryover_action_points_by_player = {
            player_id: self._bonus_carryover_points(battle, player_id)
            for player_id in actions_by_player
        }
        result = self.battle_engine.resolve_round(
            battle,
            actions_by_player,
            bonus_action_points_by_player=carryover_action_points_by_player,
        )
        next_round = result.battle.current_round
        self.battle_bonus_carryover = {
            key: value
            for key, value in self.battle_bonus_carryover.items()
            if key[0] != battle.id or key[1] == next_round
        }
        for player_id, actions in actions_by_player.items():
            bonus_count = sum(
                1 for action in actions if action.action_type == BattleActionType.BONUS
            )
            self.battle_bonus_carryover[
                self._battle_round_key(battle.id, next_round, player_id)
            ] = bonus_count
        self._apply_inactive_round_penalty(result.battle, actions_by_player)
        self._clear_battle_round_drafts(result.battle.id)
        await self.battles.save(result.battle)
        if result.battle.status.value == "active":
            self._set_current_turn_player_id(
                result.battle, result.battle.first_turn_player_id
            )
            self._start_battle_round(result.battle)
        else:
            self._clear_battle_runtime_state(result.battle.id)
            await self._apply_battle_result(result.battle)
        if notify_timeout and self.battle_timeout_notifier is not None:
            with suppress(Exception):
                await self.battle_timeout_notifier(result.battle, reason=reason)
        return result.battle

    def _apply_inactive_round_penalty(
        self, battle: Battle, actions_by_player: dict[int, list[BattleAction]]
    ) -> None:
        """Kill the active card after too many rounds without any attacks."""

        punished_sides: list[BattleSide] = []
        for player_id in (battle.player_one_id, battle.player_two_id):
            attacked = any(
                action.action_type == BattleActionType.ATTACK
                for action in actions_by_player.get(player_id, [])
            )
            key = (battle.id, player_id)
            if attacked:
                self.battle_inactive_rounds[key] = 0
                continue
            streak = self.battle_inactive_rounds.get(key, 0) + 1
            self.battle_inactive_rounds[key] = streak
            if streak < self.battle_inactive_round_limit:
                continue
            side = battle.side_for(player_id)
            active = side.active_card()
            active.alive = False
            active.current_health = 0
            punished_sides.append(side)
            self.battle_inactive_rounds[key] = 0
        for side in punished_sides:
            side.ensure_active_alive()
        if punished_sides:
            self.battle_engine._finish_if_needed(battle)

    async def record_battle_action(
        self,
        player_id: int,
        action: str,
        *,
        card_id: int | None = None,
    ) -> Battle:
        """Append one action to the player's draft and resolve finished rounds."""

        battle = await self.get_active_battle(player_id)
        if battle is None:
            raise EntityNotFoundError("battle not found")
        async with self._battle_action_lock(battle.id):
            battle = await self._resolve_expired_round_if_needed(battle)
            if battle.status.value != "active":
                return battle
            summary = self._battle_round_summary(battle, player_id)
            if not summary.is_player_turn:
                raise BattleRuleViolationError("wait for your turn")
            actions = self._battle_round_actions(
                battle.id, battle.current_round, player_id
            )
            if action == "switch" and actions:
                raise BattleRuleViolationError(
                    "switch can be used only as the first choice"
                )
            if action == "attack":
                if summary.available_action_points < 1:
                    raise BattleRuleViolationError("not enough action points")
                actions.append(
                    AttackAction(action_type=BattleActionType.ATTACK, ap_cost=1)
                )
            elif action == "block":
                if summary.available_action_points < 1:
                    raise BattleRuleViolationError("not enough action points")
                actions.append(
                    BlockAction(action_type=BattleActionType.BLOCK, ap_cost=1)
                )
            elif action == "bonus":
                if summary.available_action_points < 1:
                    raise BattleRuleViolationError("not enough action points")
                if summary.bonus_count >= self.battle_engine.MAX_BONUSES_PER_TURN:
                    raise BattleRuleViolationError(
                        "cannot choose more than 5 bonuses per turn"
                    )
                actions.append(
                    BonusAction(action_type=BattleActionType.BONUS, ap_cost=1)
                )
            elif action == "ability":
                if summary.ability_used:
                    raise BattleRuleViolationError(
                        "ability can be used only once per round"
                    )
                if summary.ability_cooldown_remaining > 0:
                    raise BattleRuleViolationError("ability is on cooldown")
                if summary.available_action_points < summary.ability_cost:
                    raise BattleRuleViolationError(
                        "Не достаточно Очков Действия для способности"
                    )
                active_card = battle.side_for(player_id).active_card()
                actions.append(
                    UseAbilityAction(
                        action_type=BattleActionType.USE_ABILITY,
                        ap_cost=summary.ability_cost,
                        player_card_id=active_card.player_card_id,
                    )
                )
            elif action == "switch":
                if card_id is None:
                    raise ValidationError("switch requires card_id")
                if summary.available_action_points < 1:
                    raise BattleRuleViolationError("not enough action points")
                side = battle.side_for(player_id)
                card = side.cards.get(card_id)
                if card is None or not card.alive:
                    raise BattleRuleViolationError(
                        "cannot switch to dead/unknown card"
                    )
                actions.append(
                    SwitchCardAction(
                        action_type=BattleActionType.SWITCH_CARD,
                        ap_cost=1,
                        new_active_card_id=card_id,
                    )
                )
            else:
                raise ValidationError("unsupported battle action")

            current_summary = self._battle_round_summary(battle, player_id)
            if current_summary.available_action_points > 0:
                self._start_battle_round(battle)
                await self.battles.save(battle)
                return battle

            if player_id == battle.first_turn_player_id:
                self._set_current_turn_player_id(
                    battle, battle.opponent_side_for(player_id).player_id
                )
                self._start_battle_round(battle)
                await self.battles.save(battle)
                return battle

            return await self._resolve_current_round(battle, notify_timeout=False)

    async def search_battle(self, telegram_id: int) -> Battle | None:
        """Join the matchmaking queue and start a battle when possible."""

        player = await self.get_or_create_player(telegram_id)
        if player.battle_deck is None:
            raise ValidationError("Колода не полностью собрана")
        self._ensure_valid_battle_deck_ids(player.battle_deck.card_ids)
        self.search_queue[player.telegram_id] = player.rating
        self._persist_runtime_state()
        return await self.process_matchmaking()

    async def cancel_battle_search(self, telegram_id: int) -> None:
        """Remove a player from the matchmaking queue."""

        self.search_queue.pop(telegram_id, None)
        self._persist_runtime_state()

    async def process_matchmaking(self) -> Battle | None:
        """Pair the first two compatible players from the queue."""

        ids = list(self.search_queue)
        for index, player_one_id in enumerate(ids):
            player_one_rating = self.search_queue.get(player_one_id)
            if player_one_rating is None:
                continue
            for player_two_id in ids[index + 1 :]:
                player_two_rating = self.search_queue.get(player_two_id)
                if player_two_rating is None:
                    continue
                if abs(player_one_rating - player_two_rating) > 100:
                    continue
                self.search_queue.pop(player_one_id, None)
                self.search_queue.pop(player_two_id, None)
                self._persist_runtime_state()
                return await self.start_battle(player_one_id, player_two_id)
        return None

    async def is_searching(self, telegram_id: int) -> bool:
        """Return True when a player is in the queue."""

        return telegram_id in self.search_queue

    async def _battle_side_for(self, player: Player) -> BattleSide:
        """Build one battle side from the player's battle deck."""

        cards = await self.list_player_cards(player.telegram_id)
        if player.battle_deck is None:
            raise ValidationError("Колода не полностью собрана")
        deck_ids = player.battle_deck.card_ids
        self._ensure_valid_battle_deck_ids(deck_ids)
        by_id = {card.id: card for card in cards}
        selected: list[BattleCardState] = []
        for card_id in deck_ids:
            card = by_id.get(card_id)
            if card is None:
                raise ValidationError("battle deck contains unknown card")
            template = await self.get_template(card.template_id)
            if template is None:
                raise EntityNotFoundError("card template not found")
            stats = template.stats_for(card.current_form)
            selected.append(
                BattleCardState(
                    card.id,
                    template,
                    card.current_form,
                    stats.health,
                    stats.health,
                    stats.damage,
                    stats.defense,
                )
            )
        return BattleSide(
            player.telegram_id,
            {card.player_card_id: card for card in selected},
            selected[0].player_card_id,
        )

    async def _next_battle_id(self) -> int:
        return _next_id(self.battles.items)


__all__ = ["BattleServiceMixin"]
