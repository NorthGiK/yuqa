"""Catalog and admin content flows for TelegramServices."""

from yuqa.banners.domain.entities import Banner, BannerReward
from yuqa.cards.domain.entities import Ability, CardTemplate, PlayerCard
from yuqa.players.domain.entities import Player, ProfileBackgroundTemplate
from yuqa.shared.enums import (
    BannerType,
    CardClass,
    CardForm,
    ProfileBackgroundRarity,
    Rarity,
    ResourceType,
    RewardType,
    Universe,
)
from yuqa.shared.errors import (
    EntityNotFoundError,
    ForbiddenActionError,
)
from yuqa.shared.value_objects.date_range import DateRange
from yuqa.shared.value_objects.deck_slots import DeckSlots
from yuqa.shared.value_objects.image_ref import ImageRef
from yuqa.shared.value_objects.stat_block import StatBlock
from yuqa.shop.domain.entities import ShopItem
from yuqa.telegram.services_support import _next_id


class ContentAdminServiceMixin:
    """Catalog, card, banner, shop, and admin content helpers."""

    async def list_active_shop_items(self) -> list[ShopItem]:
        """Return the visible shop catalog."""

        return await self.shop.list_active()

    async def list_available_banners(self) -> list[Banner]:
        """Return the banners that are currently available."""

        return await self.banners.list_available()

    async def list_card_templates(self) -> list[CardTemplate]:
        """Return every stored card template."""

        return list(self.card_templates.items.values())

    async def list_universes(self) -> list[str]:
        """Return the current universe catalog."""

        if self.catalog is None:
            return list(self._universes)
        return list(self.catalog.universes)

    async def list_standard_cards(self) -> list[int]:
        """Return the starter card template ids."""

        return list(self._read_standard_cards())

    async def create_profile_background(
        self,
        rarity: ProfileBackgroundRarity,
        media_key: str,
        *,
        content_type: str = "image/png",
        original_name: str | None = None,
    ) -> ProfileBackgroundTemplate:
        """Create and persist a new profile background template."""

        background = ProfileBackgroundTemplate(
            id=_next_id(self.profile_backgrounds.items),
            rarity=rarity,
            media=ImageRef(
                media_key,
                content_type=content_type,
                original_name=original_name,
            ),
        )
        await self.profile_backgrounds.add(background)
        return background

    async def get_card(self, card_id: int, player_id: int) -> PlayerCard:
        """Return an owned card or raise an error."""

        card = await self.player_cards.get_by_id(card_id)
        if card is None or card.owner_player_id != player_id:
            raise EntityNotFoundError("card not found")
        return card

    async def level_up_card(self, telegram_id: int, card_id: int) -> PlayerCard:
        """Level up one owned card and persist the wallet change."""

        player = await self.get_or_create_player(telegram_id)
        card = await self.get_card(card_id, telegram_id)
        self.card_progression.level_up(card, player.wallet)
        await self.player_cards.save(card)
        await self.players.save(player)
        return card

    async def ascend_card(self, telegram_id: int, card_id: int) -> PlayerCard:
        """Ascend one owned card and persist the wallet change."""

        player = await self.get_or_create_player(telegram_id)
        card = await self.get_card(card_id, telegram_id)
        self.card_progression.ascend(card, player.wallet)
        await self.player_cards.save(card)
        await self.players.save(player)
        return card

    async def toggle_card_form(self, telegram_id: int, card_id: int) -> PlayerCard:
        """Toggle the visible form of an ascended card."""

        card = await self.get_card(card_id, telegram_id)
        self.card_progression.toggle_form(card)
        await self.player_cards.save(card)
        return card

    async def get_template(self, template_id: int) -> CardTemplate | None:
        """Return a card template by id."""

        return await self.card_templates.get_by_id(template_id)

    async def add_universe(self, value: str) -> list[str]:
        """Append a new universe name if it does not exist yet."""

        value = self._normalize_universe(value)
        universes = await self.list_universes()
        if value not in universes:
            universes.append(value)
            self._set_universes(universes)
        return universes

    async def remove_universe(self, value: str) -> list[str]:
        """Remove a universe name from the catalog."""

        value = self._normalize_universe(value)
        universes = [item for item in await self.list_universes() if item != value]
        self._set_universes(universes)
        return universes

    async def create_card_template(
        self,
        name: str,
        universe: Universe | str,
        rarity: Rarity,
        image_key: str,
        card_class: CardClass,
        base_stats: StatBlock,
        ascended_stats: StatBlock,
        ability: Ability,
        ascended_ability: Ability | None = None,
        is_available: bool = True,
    ) -> CardTemplate:
        """Create and persist a new card template."""

        await self.add_universe(getattr(universe, "value", universe))
        template = CardTemplate(
            id=_next_id(self.card_templates.items),
            name=name,
            universe=getattr(universe, "value", universe),
            rarity=rarity,
            image=ImageRef(image_key),
            card_class=card_class,
            base_stats=base_stats,
            ascended_stats=ascended_stats,
            ability=ability,
            ascended_ability=ascended_ability,
            is_available=is_available,
        )
        await self.card_templates.add(template)
        return template

    async def delete_profile_background(self, background_id: int) -> None:
        """Delete a profile background and remove it from players and banners."""

        if await self.get_profile_background(background_id) is None:
            raise EntityNotFoundError("profile background not found")
        await self.profile_backgrounds.delete(background_id)
        for banner in list(self.banners.items.values()):
            banner.pools = [
                item
                for item in banner.pools
                if item.profile_background_id != background_id
            ]
            await self.banners.save(banner)
        for player in self.players.items.values():
            player.owned_profile_background_ids = [
                item
                for item in player.owned_profile_background_ids
                if item != background_id
            ]
            if player.selected_profile_background_id == background_id:
                player.selected_profile_background_id = None
            await self.players.save(player)

    async def delete_card_template(self, template_id: int) -> None:
        """Delete a card template and every dependent reference."""

        if await self.get_template(template_id) is None:
            raise EntityNotFoundError("card template not found")
        await self.card_templates.delete(template_id)
        removed_card_ids: set[int] = set()
        for card_id, card in list(self.player_cards.items.items()):
            if card.template_id == template_id:
                removed_card_ids.add(card_id)
                await self.player_cards.delete(card_id)
        for banner in list(self.banners.items.values()):
            banner.pools = [
                item for item in banner.pools if item.card_template_id != template_id
            ]
            await self.banners.save(banner)
        await self.set_standard_cards(
            [item for item in await self.list_standard_cards() if item != template_id]
        )
        self._remove_card_ids_from_deck_drafts(removed_card_ids)
        for player in self.players.items.values():
            player.collection_count = len(
                await self.player_cards.list_by_owner(player.telegram_id)
            )
            self._remove_card_ids_from_player_deck(player, removed_card_ids)
            await self.players.save(player)
        self._persist_runtime_state()

    async def create_banner(
        self,
        name: str,
        banner_type: BannerType,
        cost_resource: ResourceType,
        start_at,
        end_at=None,
        is_active: bool = True,
    ) -> Banner:
        """Create and persist a new banner."""

        banner = Banner(
            id=_next_id(self.banners.items),
            name=name,
            banner_type=banner_type,
            cost_resource=cost_resource,
            date_range=DateRange(start_at, end_at),
            is_active=is_active,
        )
        await self.banners.add(banner)
        return banner

    async def delete_banner(self, banner_id: int) -> None:
        """Delete a banner while it is still manageable or currently active."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit() and not banner.is_available():
            raise ForbiddenActionError("banner already started")
        await self.banners.delete(banner_id)

    async def add_banner_reward_card(
        self,
        banner_id: int,
        template_id: int,
        weight: int,
        guaranteed_for_10_pull: bool,
    ) -> Banner:
        """Add a card reward to a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        template = await self.get_template(template_id)
        if template is None:
            raise EntityNotFoundError("card template not found")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.CARD
                and reward.card_template_id == template_id
            )
        ]
        banner.pools.append(
            BannerReward(
                RewardType.CARD,
                card_template_id=template.id,
                quantity=1,
                rarity=template.rarity,
                weight=weight,
                guaranteed_for_10_pull=guaranteed_for_10_pull,
            )
        )
        await self.banners.save(banner)
        return banner

    async def add_banner_reward_profile_background(
        self,
        banner_id: int,
        background_id: int,
        weight: int,
        guaranteed_for_10_pull: bool,
    ) -> Banner:
        """Add a profile-background reward to a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        background = await self.get_profile_background(background_id)
        if background is None:
            raise EntityNotFoundError("profile background not found")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.PROFILE_BACKGROUND
                and reward.profile_background_id == background_id
            )
        ]
        banner.pools.append(
            BannerReward(
                RewardType.PROFILE_BACKGROUND,
                profile_background_id=background.id,
                quantity=1,
                profile_background_rarity=background.rarity,
                weight=weight,
                guaranteed_for_10_pull=guaranteed_for_10_pull,
            )
        )
        await self.banners.save(banner)
        return banner

    async def remove_banner_reward_card(
        self, banner_id: int, template_id: int
    ) -> Banner:
        """Remove a card reward from a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.CARD
                and reward.card_template_id == template_id
            )
        ]
        await self.banners.save(banner)
        return banner

    async def remove_banner_reward_profile_background(
        self, banner_id: int, background_id: int
    ) -> Banner:
        """Remove a profile-background reward from a banner before it starts."""

        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        if not banner.can_edit():
            raise ForbiddenActionError("banner already started")
        banner.pools = [
            reward
            for reward in banner.pools
            if not (
                reward.reward_type == RewardType.PROFILE_BACKGROUND
                and reward.profile_background_id == background_id
            )
        ]
        await self.banners.save(banner)
        return banner

    async def create_shop_item(
        self,
        sell_resource_type: ResourceType,
        buy_resource_type: ResourceType,
        price: int,
        quantity: int,
        is_active: bool = True,
    ) -> ShopItem:
        """Create and persist a new shop item."""

        item = ShopItem(
            id=_next_id(self.shop.items),
            sell_resource_type=sell_resource_type,
            buy_resource_type=buy_resource_type,
            price=price,
            quantity=quantity,
            is_active=is_active,
        )
        await self.shop.add(item)
        return item

    async def remove_shop_item(self, item_id: int) -> None:
        """Remove an existing shop item from the catalog."""

        if await self.shop.get_by_id(item_id) is None:
            raise EntityNotFoundError("shop item not found")
        await self.shop.delete(item_id)

    async def set_standard_cards(self, template_ids: list[int]) -> list[int]:
        """Persist the full list of standard cards."""

        await self._validate_standard_cards(template_ids)
        ids = list(dict.fromkeys(template_ids))
        if self.catalog is None:
            self._write_standard_cards(ids)
        else:
            self.catalog.standard_cards = ids
            self.catalog.save()
        return ids

    async def add_standard_card(self, template_id: int) -> list[int]:
        """Append one card to the standard list."""

        current = await self.list_standard_cards()
        current.append(template_id)
        return await self.set_standard_cards(current)

    async def remove_standard_card(self, template_id: int) -> list[int]:
        """Remove one card from the standard list."""

        return await self.set_standard_cards(
            [item for item in await self.list_standard_cards() if item != template_id]
        )

    async def purchase_shop_item(self, telegram_id: int, item_id: int) -> ShopItem:
        """Buy one shop item for the player."""

        player = await self.get_or_create_player(telegram_id)
        item = await self.shop.get_by_id(item_id)
        if item is None:
            raise EntityNotFoundError("shop item not found")
        self.shop_service.purchase(player, item)
        await self.players.save(player)
        return item

    async def pull_banner(
        self, telegram_id: int, banner_id: int, count: int
    ) -> list[str]:
        """Roll rewards from a banner."""

        player = await self.get_or_create_player(telegram_id)
        banner = await self.banners.get_by_id(banner_id)
        if banner is None:
            raise EntityNotFoundError("banner not found")
        rewards = self.banner_service.pull(player, banner, count=count)
        descriptions = [
            await self._apply_banner_reward(player, reward) for reward in rewards
        ]
        await self.players.save(player)
        return descriptions

    async def grant_card_to_player(
        self, telegram_id: int, template_id: int
    ) -> PlayerCard:
        """Grant one card template to a player by Telegram id."""

        player = await self.get_or_create_player(telegram_id)
        template = await self.get_template(template_id)
        if template is None:
            raise EntityNotFoundError("card template not found")
        card = await self._grant_template_to_player(player, template)
        await self.players.save(player)
        return card

    async def remove_card_from_player(
        self, telegram_id: int, template_id: int
    ) -> PlayerCard:
        """Remove one owned copy of a template from a player by Telegram id."""

        player = await self.get_player(telegram_id)
        if player is None:
            raise EntityNotFoundError("player not found")
        template = await self.get_template(template_id)
        if template is None:
            raise EntityNotFoundError("card template not found")
        owned_cards = await self.player_cards.list_by_owner(player.telegram_id)
        for card in owned_cards:
            if card.template_id != template_id:
                continue
            if card.copies_owned > 1:
                card.copies_owned -= 1
                await self.player_cards.save(card)
                return card
            await self.player_cards.delete(card.id)
            player.collection_count = len(
                await self.player_cards.list_by_owner(player.telegram_id)
            )
            self._remove_card_ids_from_player_deck(player, {card.id})
            self._remove_card_ids_from_deck_drafts({card.id})
            await self.players.save(player)
            self._persist_runtime_state()
            return card
        raise EntityNotFoundError("player card not found")

    async def _grant_template_to_player(
        self, player: Player, template: CardTemplate
    ) -> PlayerCard:
        """Grant a template as a new card or as an extra copy."""

        owned_cards = await self.player_cards.list_by_owner(player.telegram_id)
        for card in owned_cards:
            if card.template_id == template.id:
                card.copies_owned += 1
                await self.player_cards.save(card)
                return card
        card = PlayerCard(
            id=_next_id(self.player_cards.items),
            owner_player_id=player.telegram_id,
            template_id=template.id,
            level=1,
            copies_owned=1,
            current_form=CardForm.BASE,
        )
        await self.player_cards.add(card)
        player.collection_count = len(
            await self.player_cards.list_by_owner(player.telegram_id)
        )
        return card

    def _set_universes(self, values: list[str]) -> None:
        """Persist the universe list."""

        values = list(dict.fromkeys(values))
        if self.catalog is None:
            self._universes = values
        else:
            self.catalog.universes = values
            self.catalog.save()

    def _normalize_universe(self, value: str) -> str:
        """Normalize a free-form universe name."""

        return "_".join(
            part for part in value.strip().lower().replace("-", " ").split()
        )

    def _read_standard_cards(self) -> list[int]:
        """Read the starter card list."""

        return list(
            getattr(self, "_standard_cards", [])
            if self.catalog is None
            else self.catalog.standard_cards
        )

    def _write_standard_cards(self, values: list[int]) -> None:
        """Persist the starter card list."""

        if self.catalog is None:
            self._standard_cards = list(values)
            return
        self.catalog.standard_cards = list(values)
        self.catalog.save()

    async def _validate_standard_cards(self, template_ids: list[int]) -> None:
        """Make sure the standard list only contains existing templates."""

        for template_id in template_ids:
            if await self.get_template(template_id) is None:
                raise EntityNotFoundError(f"card template {template_id} not found")

    async def _grant_standard_cards(self, player: Player) -> None:
        """Give the default starter cards to a newly created player."""

        template_ids = await self.list_standard_cards()
        if not template_ids:
            return
        for template_id in template_ids:
            if await self.get_template(template_id) is None:
                continue
            await self.player_cards.add(
                PlayerCard(
                    id=_next_id(self.player_cards.items),
                    owner_player_id=player.telegram_id,
                    template_id=template_id,
                    copies_owned=1,
                    level=1,
                    current_form=CardForm.BASE,
                )
            )
        player.collection_count = len(
            await self.player_cards.list_by_owner(player.telegram_id)
        )

    @staticmethod
    def _remove_card_ids_from_player_deck(
        player: Player, removed_card_ids: set[int]
    ) -> None:
        """Drop removed card ids from one player's saved battle deck."""

        if player.battle_deck is None or not removed_card_ids:
            return
        filtered = [
            card_id
            for card_id in player.battle_deck.card_ids
            if card_id not in removed_card_ids
        ]
        if len(filtered) == 5 and len(set(filtered)) == 5:
            player.battle_deck = DeckSlots(tuple(filtered))
        else:
            player.battle_deck = None

    def _remove_card_ids_from_deck_drafts(self, removed_card_ids: set[int]) -> None:
        """Drop removed card ids from every in-progress deck draft."""

        if not removed_card_ids:
            return
        for player_id, draft in list(self.deck_drafts.items()):
            filtered = [card_id for card_id in draft if card_id not in removed_card_ids]
            self.deck_drafts[player_id] = self._unique_card_ids(filtered)


__all__ = ["ContentAdminServiceMixin"]
