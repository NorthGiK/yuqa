"""Battle command helpers shared by router registrations."""

from yuqa.shared.errors import DomainError, ValidationError
from yuqa.telegram.compat import CommandObject, Message
from yuqa.telegram.reply import send_alert, send_or_edit
from yuqa.telegram.router_views import show_battle
from yuqa.telegram.texts import (
    battle_result_text,
    battle_started_text,
    battle_status_text,
    battle_text,
)
from yuqa.telegram.ui import battle_actions_markup, battle_markup


async def start_battle(message: Message, services, command: CommandObject):
    """Start a PvP battle from a text command."""

    if not message.from_user:
        return
    if not command.args:
        player = await services.get_or_create_player(message.from_user.id)
        return await message.answer(battle_text(player))
    try:
        battle = await services.start_battle(
            message.from_user.id, int(command.args.strip())
        )
    except ValueError as error:
        return await message.answer(f"❌ {error}")
    except (DomainError, ValidationError) as error:
        return await send_alert(message, f"⛔️ {error}")
    summary = services.battle_round_summary(battle, message.from_user.id)
    await message.answer(
        battle_started_text(battle)
        + "\n"
        + battle_status_text(
            battle,
            message.from_user.id,
            current_turn_player_id=summary.current_turn_player_id,
            opponent_spent_action_points=summary.opponent_spent_action_points,
            available_action_points=summary.available_action_points,
            total_action_points=summary.total_action_points,
            attack_count=summary.attack_count,
            block_count=summary.block_count,
            bonus_count=summary.bonus_count,
            ability_used=summary.ability_used,
        ),
        reply_markup=battle_actions_markup(
            can_switch=summary.can_switch,
            ability_cost=summary.ability_cost,
            can_use_ability=(
                summary.is_player_turn
                and not summary.ability_used
                and summary.ability_cooldown_remaining <= 0
                and summary.available_action_points >= summary.ability_cost
            ),
        )
        if summary.is_player_turn and summary.available_action_points > 0
        else None,
    )


async def search_battle(event, services, player_id: int, bot=None):
    """Add a player to matchmaking and announce a battle when it is found."""

    try:
        battle = await services.search_battle(player_id)
    except (DomainError, ValidationError) as error:
        return await send_alert(event, f"⛔️ {error}")
    if battle is None:
        await send_or_edit(
            event,
            battle_text(await services.get_or_create_player(player_id), True),
            battle_markup(True),
        )
        return
    summary = services.battle_round_summary(battle, player_id)
    await send_or_edit(
        event,
        battle_started_text(battle)
        + "\n"
        + battle_status_text(
            battle,
            player_id,
            current_turn_player_id=summary.current_turn_player_id,
            opponent_spent_action_points=summary.opponent_spent_action_points,
            available_action_points=summary.available_action_points,
            total_action_points=summary.total_action_points,
            attack_count=summary.attack_count,
            block_count=summary.block_count,
            bonus_count=summary.bonus_count,
            ability_used=summary.ability_used,
        ),
        battle_actions_markup(
            can_switch=summary.can_switch,
            ability_cost=summary.ability_cost,
            can_use_ability=(
                summary.is_player_turn
                and not summary.ability_used
                and summary.ability_cooldown_remaining <= 0
                and summary.available_action_points >= summary.ability_cost
            ),
        )
        if summary.is_player_turn and summary.available_action_points > 0
        else None,
    )
    if bot is not None and hasattr(bot, "send_message"):
        other_id = (
            battle.player_two_id
            if battle.player_one_id == player_id
            else battle.player_one_id
        )
        opponent_summary = services.battle_round_summary(battle, other_id)
        await bot.send_message(
            other_id,
            battle_result_text(
                battle, await services.get_player(other_id) or await services.get_or_create_player(other_id)
            )
            if battle.status.value != "active"
            else battle_started_text(battle)
            + "\n"
            + battle_status_text(
                battle,
                other_id,
                current_turn_player_id=opponent_summary.current_turn_player_id,
                opponent_spent_action_points=opponent_summary.opponent_spent_action_points,
                available_action_points=opponent_summary.available_action_points,
                total_action_points=opponent_summary.total_action_points,
                attack_count=opponent_summary.attack_count,
                block_count=opponent_summary.block_count,
                bonus_count=opponent_summary.bonus_count,
                ability_used=opponent_summary.ability_used,
            ),
            reply_markup=None
            if battle.status.value != "active"
            or not opponent_summary.is_player_turn
            or opponent_summary.available_action_points <= 0
            else battle_actions_markup(
                can_switch=opponent_summary.can_switch,
                ability_cost=opponent_summary.ability_cost,
                can_use_ability=(
                    opponent_summary.is_player_turn
                    and not opponent_summary.ability_used
                    and opponent_summary.ability_cooldown_remaining <= 0
                    and opponent_summary.available_action_points
                    >= opponent_summary.ability_cost
                ),
            ),
        )


async def cancel_battle_search(event, services, player_id: int):
    """Cancel matchmaking for the player."""

    await services.cancel_battle_search(player_id)
    await show_battle(event, services, player_id)


__all__ = ["cancel_battle_search", "search_battle", "start_battle"]
