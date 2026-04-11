"""Typed identifiers used in the domain."""

from typing import NewType

PlayerId = NewType("PlayerId", int)
CardTemplateId = NewType("CardTemplateId", int)
PlayerCardId = NewType("PlayerCardId", int)
ClanId = NewType("ClanId", int)
BattleId = NewType("BattleId", int)
BannerId = NewType("BannerId", int)
QuestId = NewType("QuestId", int)
SeasonId = NewType("SeasonId", int)
ShopItemId = NewType("ShopItemId", int)
