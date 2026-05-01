"""Battle state used by the engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.cards.domain.entities import CardTemplate
from src.shared.enums import BattleStatus, CardForm, AbilityStat


@dataclass(slots=True)
class StatModifier:
    """Timed modifier that changes a stat."""

    stat: AbilityStat
    value: int
    remaining_rounds: int
    source_player_card_id: int | None = None


@dataclass(slots=True)
class BattleCardState:
    """Card snapshot inside a battle."""

    player_card_id: int
    template: CardTemplate
    form: CardForm
    max_health: int
    current_health: int
    damage: int
    defense: int
    alive: bool = True
    ability_cooldown_remaining: int = 0
    effect_modifiers: list[StatModifier] = field(default_factory=list)

    def recalc(self) -> None:
        """Recompute derived stats from the template and modifiers."""

        stats = self.template.stats_for(self.form)
        damage = stats.damage
        health = stats.health
        defense = stats.defense
        for modifier in self.effect_modifiers:
            if modifier.remaining_rounds <= 0:
                continue
            if modifier.stat == AbilityStat.DAMAGE:
                damage += modifier.value
            elif modifier.stat == AbilityStat.HEALTH:
                health += modifier.value
            elif modifier.stat == AbilityStat.DEFENSE:
                defense += modifier.value
        self.damage = max(0, damage)
        self.defense = max(0, defense)
        self.max_health = max(1, health)
        self.current_health = min(self.current_health, self.max_health)
        self.alive = self.current_health > 0

    def ability_available(self) -> bool:
        """Return True when the card can use its ability this round."""

        return self.alive and self.ability_cooldown_remaining <= 0


@dataclass(slots=True)
class BattleSide:
    """One side of a battle with five cards."""

    player_id: int
    cards: dict[int, BattleCardState]
    active_card_id: int

    def alive_cards(self) -> list[BattleCardState]:
        """Return all surviving cards."""

        return [card for card in self.cards.values() if card.alive and card.current_health > 0]

    def active_card(self) -> BattleCardState:
        """Return the currently active card."""

        return self.cards[self.active_card_id]

    def ensure_active_alive(self) -> None:
        """Pick the first alive card when the active one is dead."""

        if self.active_card_id in self.cards:
            self.cards[self.active_card_id].alive = (
                self.cards[self.active_card_id].current_health > 0
            )
        if (
            self.active_card_id not in self.cards
            or not self.cards[self.active_card_id].alive
        ):
            alive = self.alive_cards()
            if alive:
                self.active_card_id = alive[0].player_card_id


@dataclass(slots=True)
class Battle:
    """Two-player battle aggregate."""

    id: int
    player_one_id: int
    player_two_id: int
    player_one_side: BattleSide
    player_two_side: BattleSide
    current_round: int = 1
    first_turn_player_id: int | None = None
    current_turn_player_id: int | None = None
    status: BattleStatus = BattleStatus.WAITING
    winner_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    pending_enemy_effects: list[tuple[int, StatModifier]] = field(default_factory=list)

    def side_for(self, player_id: int) -> BattleSide:
        """Return the side that belongs to a player."""

        if player_id == self.player_one_id:
            return self.player_one_side
        if player_id == self.player_two_id:
            return self.player_two_side
        raise ValueError("unknown player")

    def opponent_side_for(self, player_id: int) -> BattleSide:
        """Return the opposing side."""

        return (
            self.player_two_side
            if player_id == self.player_one_id
            else self.player_one_side
        )
