"""Player, profile, free reward, and deck flows for TelegramServices."""

import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, TypeVar

from yuqa.banners.domain.entities import BannerReward
from yuqa.cards.domain.entities import CardTemplate, PlayerCard
from yuqa.clans.domain.entities import Clan
from yuqa.players.domain.entities import (
    Player,
    PlayerTopEntry,
    ProfileBackgroundTemplate,
)
from yuqa.shared.enums import Rarity, ResourceType, RewardType
from yuqa.shared.errors import (
    EntityNotFoundError,
    ForbiddenActionError,
    ValidationError,
)
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.telegram.services.services_contracts import (
    FreeRewardSettings,
    FreeRewardsStatus,
    TelegramServiceContext,
)

_FREE_CARD_RARITIES = (
    Rarity.COMMON,
    Rarity.RARE,
    Rarity.EPIC,
    Rarity.MYTHIC,
    Rarity.LEGENDARY,
    Rarity.GODLY,
)
_FREE_RESOURCE_TYPES = (
    ResourceType.COINS,
    ResourceType.CRYSTALS,
    ResourceType.ORBS,
)
_FREE_REWARD_COOLDOWN = timedelta(hours=2)
_NICKNAME_RE = re.compile(r"^[\w]{3,24}$", re.UNICODE)
_MAX_TITLE_LENGTH = 60
_TOP_MODES = {"rating", "badenko_cards", "creator_points"}
_WeightedKey = TypeVar("_WeightedKey")


if TYPE_CHECKING:

    class _PlayerProfileServiceMixinBase(TelegramServiceContext):
        """Type-only base for mixin attribute and method completion."""

else:

    class _PlayerProfileServiceMixinBase:
        """Runtime base without protocol method stubs."""


class PlayerProfileServiceMixin(_PlayerProfileServiceMixinBase):
    """Player lookup, profile, free reward, and deck editing helpers."""

    async def get_or_create_player(self, telegram_id: int) -> Player:
        """Return an existing player or create a fresh one."""

        player = await self.players.get_by_telegram_id(telegram_id)
        if player is None:
            player = Player(telegram_id=telegram_id)
            await self.players.add(player)
            await self._grant_standard_cards(player)
            await self.players.save(player)
        return player

    async def get_player(self, telegram_id: int) -> Player | None:
        """Return a player without creating one."""

        return await self.players.get_by_id(telegram_id)

    async def player_clan(self, player: Player) -> Clan | None:
        """Return the clan that belongs to the player."""

        return (
            None
            if player.clan_id is None
            else await self.clans.get_by_id(player.clan_id)
        )

    async def clan_members(self, clan: Clan | None) -> list[Player]:
        """Return resolved clan members ordered by telegram id."""

        if clan is None:
            return []
        members: list[Player] = []
        for member_id in sorted(clan.members):
            player = await self.players.get_by_id(member_id)
            if player is not None:
                members.append(player)
        return members

    async def list_player_cards(self, telegram_id: int) -> list[PlayerCard]:
        """Return every card owned by a player."""

        return await self.player_cards.list_by_owner(telegram_id)

    async def get_profile_background(
        self, background_id: int
    ) -> ProfileBackgroundTemplate | None:
        """Return a profile background template by id."""

        return await self.profile_backgrounds.get_by_id(background_id)

    async def list_profile_backgrounds(self) -> list[ProfileBackgroundTemplate]:
        """Return every stored profile background template."""

        return list(await self.profile_backgrounds.list_all())

    async def list_player_profile_backgrounds(
        self, telegram_id: int
    ) -> list[ProfileBackgroundTemplate]:
        """Return the profile backgrounds owned by a player."""

        player = await self.get_or_create_player(telegram_id)
        items: list[ProfileBackgroundTemplate] = []
        for background_id in player.owned_profile_background_ids:
            background = await self.profile_backgrounds.get_by_id(background_id)
            if background is not None:
                items.append(background)
        return items

    async def selected_profile_background_for_player(
        self, player: Player
    ) -> ProfileBackgroundTemplate | None:
        """Resolve the active profile background for a player."""

        if player.selected_profile_background_id is None:
            return None
        return await self.profile_backgrounds.get_by_id(
            player.selected_profile_background_id
        )

    async def free_rewards_status(self, telegram_id: int) -> FreeRewardsStatus:
        """Return cooldown and configuration data for the free rewards screen."""

        player = await self.get_or_create_player(telegram_id)
        now = datetime.now(timezone.utc)
        card_ready_at = self._next_free_reward_time(player.last_free_card_claim_at)
        resource_ready_at = self._next_free_reward_time(
            player.last_free_resources_claim_at
        )
        return {
            "card_ready_at": card_ready_at,
            "resource_ready_at": resource_ready_at,
            "card_ready": card_ready_at <= now,
            "resource_ready": resource_ready_at <= now,
            "settings": self.free_reward_settings(),
        }

    def free_reward_settings(self) -> FreeRewardSettings:
        """Return the current free reward settings in a text-friendly shape."""

        return {
            "card_weights": {
                rarity.value: self.free_card_weights.get(rarity, 0)
                for rarity in _FREE_CARD_RARITIES
            },
            "resource_weights": {
                resource.value: self.free_resource_weights.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
            "resource_values": {
                resource.value: self.free_resource_values.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
            "cooldown_seconds": {"value": int(_FREE_REWARD_COOLDOWN.total_seconds())},
        }

    async def claim_free_card(
        self, telegram_id: int
    ) -> tuple[PlayerCard, CardTemplate]:
        """Grant one free random card if the cooldown is ready."""

        player = await self.get_or_create_player(telegram_id)
        self._ensure_free_reward_ready(player.last_free_card_claim_at)
        templates = await self.card_templates.list_active()
        templates_by_rarity = {
            rarity: [template for template in templates if template.rarity == rarity]
            for rarity in _FREE_CARD_RARITIES
        }
        available_weights = {
            rarity: self.free_card_weights[rarity]
            for rarity, items in templates_by_rarity.items()
            if items and self.free_card_weights.get(rarity, 0) > 0
        }
        if not available_weights:
            raise ValidationError("нет доступных карт для бесплатной награды")
        chosen_rarity = self._pick_weighted(available_weights)
        template = self.rng.choice(templates_by_rarity[chosen_rarity])
        card = await self._grant_template_to_player(player, template)
        player.last_free_card_claim_at = datetime.now(timezone.utc)
        await self.players.save(player)
        return card, template

    async def claim_free_resources(self, telegram_id: int) -> tuple[ResourceType, int]:
        """Grant one free random resource if the cooldown is ready."""

        player = await self.get_or_create_player(telegram_id)
        self._ensure_free_reward_ready(player.last_free_resources_claim_at)
        weights = {
            resource: self.free_resource_weights[resource]
            for resource in _FREE_RESOURCE_TYPES
            if self.free_resource_weights.get(resource, 0) > 0
        }
        if not weights:
            raise ValidationError("нет доступных ресурсов для бесплатной награды")
        resource = self._pick_weighted(weights)
        amount = self.free_resource_values.get(resource, 0)
        if amount <= 0:
            raise ValidationError(f"value for {resource.value} must be > 0")
        player.wallet.add(resource, amount)
        player.last_free_resources_claim_at = datetime.now(timezone.utc)
        await self.players.save(player)
        return resource, amount

    async def set_player_nickname(
        self, telegram_id: int, nickname: str | None
    ) -> Player:
        """Set or clear the player's unique nickname."""

        player = await self.get_or_create_player(telegram_id)
        nickname = self._normalize_nickname(nickname)
        if nickname is not None:
            other = await self.players.get_by_nickname(nickname)
            if other is not None and other.telegram_id != player.telegram_id:
                raise ValidationError("nickname is already taken")
        player.nickname = nickname
        await self.players.save(player)
        return player

    async def set_player_title(self, telegram_id: int, title: str | None) -> Player:
        """Set or clear the player's title."""

        player = await self.get_or_create_player(telegram_id)
        player.title = self._normalize_title(title)
        await self.players.save(player)
        return player

    async def add_creator_points(self, telegram_id: int, amount: int) -> Player:
        """Increase creator points for a player by id."""

        if amount <= 0:
            raise ValidationError("creator points amount must be > 0")
        player = await self.get_or_create_player(telegram_id)
        player.creator_points += amount
        await self.players.save(player)
        return player

    async def set_player_premium(self, telegram_id: int, is_premium: bool) -> Player:
        """Set premium status for an existing player."""

        player = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")
        player.is_premium = is_premium
        await self.players.save(player)
        return player

    async def toggle_player_premium(self, telegram_id: int) -> Player:
        """Toggle premium status for an existing player."""

        player = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")
        player.is_premium = not player.is_premium
        await self.players.save(player)
        return player

    async def delete_player(self, telegram_id: int) -> Player:
        """Delete a player and clean up related runtime state."""

        player: Player | None = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")

        clan: Clan | None = await self.player_clan(player)
        if clan is not None:
            clan.remove_member(telegram_id)
            if clan.owner_player_id == telegram_id:
                for member_id in list(clan.members):
                    if member_id == telegram_id:
                        continue
                    member: Player | None = await self.players.get_by_id(member_id)
                    if member is not None:
                        member.clan_id = None
                        await self.players.save(member)
                await self.clans.delete(clan.id)
            else:
                await self.clans.save(clan)

        for card_id, player_card in list(self.player_cards.items.items()):
            if player_card.owner_player_id == telegram_id:
                await self.player_cards.delete(card_id)

        for battle_pass_key in list(self.battle_pass_progress.items):
            if battle_pass_key[0] == telegram_id:
                await self.battle_pass_progress.delete(battle_pass_key)
        for battle_pass_key in list(self.premium_battle_pass_progress.items):
            if battle_pass_key[0] == telegram_id:
                await self.premium_battle_pass_progress.delete(battle_pass_key)

        for battle_id, battle in list(self.battles.items.items()):
            if telegram_id in {battle.player_one_id, battle.player_two_id}:
                await self.battles.delete(battle_id)
                self._clear_battle_round_drafts(battle_id)

        self.search_queue.pop(telegram_id, None)
        self.deck_drafts.pop(telegram_id, None)
        self.action_events[:] = [
            event for event in self.action_events if event[0] != telegram_id
        ]

        await self.players.delete(telegram_id)
        self._persist_runtime_state()
        return player

    async def select_profile_background(
        self, telegram_id: int, background_id: int | None
    ) -> Player:
        """Choose one owned profile background or clear the selection."""

        player = await self.get_or_create_player(telegram_id)
        if background_id is not None:
            background = await self.profile_backgrounds.get_by_id(background_id)
            if background is None:
                raise EntityNotFoundError("profile background not found")
        try:
            player.select_profile_background(background_id)
        except ValueError as error:
            raise ForbiddenActionError(
                "profile background is not in your collection"
            ) from error
        await self.players.save(player)
        return player

    async def list_top_players(
        self, mode: str, limit: int = 10
    ) -> list[PlayerTopEntry]:
        """Return a leaderboard sorted by the requested metric."""

        if mode not in _TOP_MODES:
            raise ValidationError("unknown top mode")
        players = await self.players.list_all()
        values: dict[int, int] = {}
        for player in players:
            if mode == "rating":
                values[player.telegram_id] = player.rating
            elif mode == "creator_points":
                values[player.telegram_id] = player.creator_points
            else:
                values[player.telegram_id] = await self._badenko_card_count(
                    player.telegram_id
                )
        ranked = sorted(
            players,
            key=lambda player: (
                values[player.telegram_id],
                player.rating,
                -player.telegram_id,
            ),
            reverse=True,
        )[:limit]
        return [
            PlayerTopEntry(rank=index, player=player, value=values[player.telegram_id])
            for index, player in enumerate(ranked, start=1)
        ]

    async def set_free_card_weights(
        self, weights: dict[Rarity, int]
    ) -> FreeRewardSettings:
        """Persist card-rarity weights for the free reward."""

        self._validate_weight_map(weights, "card weights")
        self.free_card_weights = {
            rarity: weights.get(rarity, 0) for rarity in _FREE_CARD_RARITIES
        }
        self._save_free_reward_settings()
        return self.free_reward_settings()

    async def set_free_resource_weights(
        self, weights: dict[ResourceType, int]
    ) -> FreeRewardSettings:
        """Persist resource-type weights for the free reward."""

        self._validate_weight_map(weights, "resource weights")
        self.free_resource_weights = {
            resource: weights.get(resource, 0) for resource in _FREE_RESOURCE_TYPES
        }
        self._save_free_reward_settings()
        return self.free_reward_settings()

    async def set_free_resource_values(
        self, values: dict[ResourceType, int]
    ) -> FreeRewardSettings:
        """Persist resource values for the free reward."""

        if any(value <= 0 for value in values.values()):
            raise ValidationError("resource values must be > 0")
        self.free_resource_values = {
            resource: values.get(resource, 0) for resource in _FREE_RESOURCE_TYPES
        }
        self._save_free_reward_settings()
        return self.free_reward_settings()

    async def deck_draft(self, telegram_id: int) -> list[int]:
        """Return or initialize the editable deck draft for a player."""

        player = await self.get_or_create_player(telegram_id)
        draft = self.deck_drafts.get(
            telegram_id,
            list(player.battle_deck.card_ids) if player.battle_deck else [],
        )
        owned = {card.id for card in await self.list_player_cards(telegram_id)}
        draft = [card_id for card_id in draft if card_id in owned]
        draft = self._unique_card_ids(draft)
        self.deck_drafts[telegram_id] = draft
        self._persist_runtime_state()
        return list(draft)

    async def toggle_deck_draft_card(self, telegram_id: int, card_id: int) -> list[int]:
        """Toggle one owned card in the editable deck draft."""

        await self.get_card(card_id, telegram_id)
        draft = await self.deck_draft(telegram_id)
        if card_id in draft:
            draft.remove(card_id)
        else:
            if len(draft) >= 5:
                raise ValidationError("в колоде можно выбрать не больше 5 карт")
            draft.append(card_id)
        self.deck_drafts[telegram_id] = draft
        self._persist_runtime_state()
        return list(draft)

    async def clear_deck_draft(self, telegram_id: int) -> list[int]:
        """Clear the editable deck draft."""

        await self.get_or_create_player(telegram_id)
        self.deck_drafts[telegram_id] = []
        self._persist_runtime_state()
        return []

    async def save_deck_draft(self, telegram_id: int) -> DeckSlots:
        """Persist the current draft as the player's battle deck."""

        player = await self.get_or_create_player(telegram_id)
        draft = await self.deck_draft(telegram_id)
        self._ensure_valid_battle_deck_ids(draft)
        player.battle_deck = DeckSlots(tuple(draft))
        await self.players.save(player)
        return player.battle_deck

    def _load_free_reward_settings(self) -> None:
        """Load persisted free reward settings when available."""

        if self.catalog is None:
            return
        data = self.catalog.free_rewards or {}
        self.free_card_weights = {
            rarity: int(
                data.get("card_weights", {}).get(
                    rarity.value, self.free_card_weights[rarity]
                )
            )
            for rarity in _FREE_CARD_RARITIES
        }
        self.free_resource_weights = {
            resource: int(
                data.get("resource_weights", {}).get(
                    resource.value, self.free_resource_weights[resource]
                )
            )
            for resource in _FREE_RESOURCE_TYPES
        }
        self.free_resource_values = {
            resource: int(
                data.get("resource_values", {}).get(
                    resource.value, self.free_resource_values[resource]
                )
            )
            for resource in _FREE_RESOURCE_TYPES
        }

    def _save_free_reward_settings(self) -> None:
        """Persist free reward settings when a local catalog is active."""

        if self.catalog is None:
            return
        self.catalog.free_rewards = {
            "card_weights": {
                rarity.value: self.free_card_weights.get(rarity, 0)
                for rarity in _FREE_CARD_RARITIES
            },
            "resource_weights": {
                resource.value: self.free_resource_weights.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
            "resource_values": {
                resource.value: self.free_resource_values.get(resource, 0)
                for resource in _FREE_RESOURCE_TYPES
            },
        }
        self.catalog.save()

    @staticmethod
    def _normalize_nickname(nickname: str | None) -> str | None:
        """Validate and normalize a unique nickname."""

        if nickname is None:
            return None
        value = nickname.strip()
        if value.lower() in {"", "-", "none", "нет", "null"}:
            return None
        if not _NICKNAME_RE.fullmatch(value):
            raise ValidationError("nickname must be 3-24 chars: letters, digits or _")
        return value

    @staticmethod
    def _normalize_title(title: str | None) -> str | None:
        """Validate and normalize a profile title."""

        if title is None:
            return None
        value = title.strip()
        if value.lower() in {"", "-", "none", "нет", "null"}:
            return None
        if len(value) > _MAX_TITLE_LENGTH:
            raise ValidationError(f"title must be <= {_MAX_TITLE_LENGTH} chars")
        return value

    @staticmethod
    def _validate_weight_map(weights: Mapping[object, int], label: str) -> None:
        """Make sure a weighted config has at least one positive entry."""

        if any(value < 0 for value in weights.values()):
            raise ValidationError(f"{label} must be >= 0")
        if sum(weights.values()) <= 0:
            raise ValidationError(f"{label} must have a positive total weight")

    def _pick_weighted(self, weights: Mapping[_WeightedKey, int]) -> _WeightedKey:
        """Pick one key from a weighted mapping."""

        total = sum(weights.values())
        if total <= 0:
            raise ValidationError("weights must have a positive total weight")
        pick = self.rng.randint(1, total)
        upto = 0
        for key, weight in weights.items():
            upto += weight
            if pick <= upto:
                return key
        return next(iter(weights))

    @staticmethod
    def _next_free_reward_time(last_claim_at: datetime | None) -> datetime:
        """Return the next moment when a reward becomes available."""

        if last_claim_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        moment = (
            last_claim_at
            if last_claim_at.tzinfo
            else last_claim_at.replace(tzinfo=timezone.utc)
        )
        return moment + _FREE_REWARD_COOLDOWN

    def _ensure_free_reward_ready(self, last_claim_at: datetime | None) -> None:
        """Raise when the reward is still on cooldown."""

        now = datetime.now(timezone.utc)
        ready_at = self._next_free_reward_time(last_claim_at)
        if ready_at > now:
            raise ValidationError("бесплатная награда еще не готова")

    @staticmethod
    def _unique_card_ids(card_ids: list[int]) -> list[int]:
        """Return card ids without duplicates, preserving order."""

        unique: list[int] = []
        seen: set[int] = set()
        for card_id in card_ids:
            if card_id in seen:
                continue
            unique.append(card_id)
            seen.add(card_id)
        return unique

    @staticmethod
    def _ensure_valid_battle_deck_ids(card_ids: list[int] | tuple[int, ...]) -> None:
        """Validate the battle deck size and uniqueness rules."""

        if len(card_ids) != 5 or len(set(card_ids)) != 5:
            raise ValidationError("для боя нужна колода из 5 разных карт")

    async def _grant_profile_background_to_player(
        self, player: Player, background: ProfileBackgroundTemplate
    ) -> bool:
        """Grant a profile background to a player."""

        granted = player.grant_profile_background(background.id)
        await self.players.save(player)
        return granted

    async def _badenko_card_count(self, telegram_id: int) -> int:
        """Return the number of Badenko cards in the player's collection."""

        count = 0
        for card in await self.player_cards.list_by_owner(telegram_id):
            template = await self.get_template(card.template_id)
            if template is not None and template.rarity == Rarity.BADENKO:
                count += 1
        return count

    async def _apply_banner_reward(self, player: Player, reward: BannerReward) -> str:
        """Apply one banner reward to the player and return a readable summary."""

        if (
            reward.reward_type == RewardType.RESOURCE
            and reward.resource_type is not None
        ):
            player.wallet.add(reward.resource_type, reward.quantity)
            return f"<code>{reward.quantity}</code> {reward.resource_type.value}"
        if (
            reward.reward_type == RewardType.CARD
            and reward.card_template_id is not None
        ):
            template = await self.get_template(reward.card_template_id)
            if template is None:
                raise EntityNotFoundError("card template not found")
            card = await self._grant_template_to_player(player, template)
            return (
                f"карта <b>{template.name}</b> · <code>{template.rarity.value}</code>"
                f" · card_id <code>{card.id}</code>"
            )
        if (
            reward.reward_type == RewardType.PROFILE_BACKGROUND
            and reward.profile_background_id is not None
        ):
            background = await self.get_profile_background(reward.profile_background_id)
            if background is None:
                raise EntityNotFoundError("profile background not found")
            granted = await self._grant_profile_background_to_player(player, background)
            status = "новый" if granted else "уже был"
            return (
                f"фон профиля <code>#{background.id}</code> · "
                f"<code>{background.rarity.value}</code> · {status}"
            )
        raise ValidationError("unsupported banner reward")


__all__ = ["PlayerProfileServiceMixin"]
