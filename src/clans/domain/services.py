"""Clan operations with all permission checks in one place."""

from dataclasses import dataclass

from src.clans.domain.entities import Clan
from src.clans.domain.texts import (
    RATING_LESS_THAN_MINIMUM,
    CANT_JOIN,
    LEADER_CANT_LEAVE_CLAN,
    ONLY_LEADER_CAN_MANAGE_BLACK_LIST,
)
from src.players.domain.entities import Player
from src.shared.enums import ResourceType
from src.shared.errors import ForbiddenActionError


@dataclass(slots=True)
class ClanService:
    """Create, join, leave, and manage a clan."""

    create_cost: int = 10_000
    min_creator_rating: int = 1000

    def create_clan(self, clan: Clan, owner: Player) -> None:
        """Create a clan and charge the owner."""

        if owner.rating <= self.min_creator_rating:
            raise ForbiddenActionError(RATING_LESS_THAN_MINIMUM)

        owner.wallet.spend(ResourceType.COINS, self.create_cost)
        owner.clan_id = clan.id
        clan.members.add(owner.telegram_id)

    def join_clan(self, clan: Clan, player: Player) -> None:
        """Add a player to the clan if all join rules pass."""

        if not clan.can_join(player.telegram_id, player.rating, player.clan_id):
            raise ForbiddenActionError(CANT_JOIN)

        clan.add_member(player.telegram_id)
        player.clan_id = clan.id

    def leave_clan(self, clan: Clan, player: Player) -> None:
        """Remove a player from the clan unless they are the leader."""

        if player.telegram_id == clan.owner_player_id:
            raise ForbiddenActionError(LEADER_CANT_LEAVE_CLAN)

        clan.remove_member(player.telegram_id)
        player.clan_id = None

    def delete_clan(self, clan: Clan, players: list[Player]) -> None:
        """Delete the clan and clear membership from all players."""

        for player in players:
            if player.clan_id == clan.id:
                player.clan_id = None

        clan.members.clear()
        clan.blacklist.clear()

    def add_to_blacklist(self, clan: Clan, leader: Player, player_id: int) -> None:
        """Add a player to the blacklist as the clan leader."""

        if leader.telegram_id != clan.owner_player_id:
            raise ForbiddenActionError(ONLY_LEADER_CAN_MANAGE_BLACK_LIST)

        clan.add_to_blacklist(player_id)

    def remove_from_blacklist(self, clan: Clan, leader: Player, player_id: int) -> None:
        """Remove a player from the blacklist as the clan leader."""

        if leader.telegram_id != clan.owner_player_id:
            raise ForbiddenActionError(ONLY_LEADER_CAN_MANAGE_BLACK_LIST)

        clan.remove_from_blacklist(player_id)
