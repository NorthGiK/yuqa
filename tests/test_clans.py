"""Tests for clan rules."""

import pytest

from yuqa.clans.domain.entities import Clan
from yuqa.clans.domain.services import ClanService
from yuqa.players.domain.entities import Player
from yuqa.shared.errors import ForbiddenActionError
from yuqa.shared.value_objects.resource_wallet import ResourceWallet


def test_clan_lifecycle():
    leader = Player(telegram_id=1, rating=1500, wallet=ResourceWallet(coins=20_000))
    member = Player(telegram_id=2, rating=1200)
    clan = Clan(id=10, owner_player_id=leader.telegram_id, name="Alpha", icon="icon.png", min_entry_rating=1000)
    service = ClanService()
    service.create_clan(clan, leader)
    service.join_clan(clan, member)
    assert leader.clan_id == clan.id and member.clan_id == clan.id and leader.wallet.coins == 10_000
    with pytest.raises(ForbiddenActionError):
        service.leave_clan(clan, leader)
    service.leave_clan(clan, member)
    assert member.clan_id is None


def test_blacklist_management():
    leader = Player(telegram_id=1, rating=1500)
    clan = Clan(id=10, owner_player_id=leader.telegram_id, name="Alpha", icon="icon.png")
    service = ClanService()
    service.add_to_blacklist(clan, leader, 99)
    assert 99 in clan.blacklist
