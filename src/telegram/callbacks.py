"""Typed callback payloads for inline keyboards."""

from src.telegram.compat import CallbackData


class MenuCallback(CallbackData, prefix="menu"):
    """Main menu navigation callback."""

    section: str


class ProfileCallback(CallbackData, prefix="profile"):
    """Profile and background actions callback."""

    action: str
    player_id: int = 0
    background_id: int = 0


class CardCallback(CallbackData, prefix="card"):
    """Card list and card action callback."""

    action: str
    card_id: int = 0
    page: int = 1
    scope: str = "collection"


class GalleryCallback(CallbackData, prefix="gallery"):
    """Gallery-only card previews."""

    card_id: int = 0
    page: int = 1


class ShopCallback(CallbackData, prefix="shop"):
    """Shop browsing and purchase callback."""

    action: str
    item_id: int


class BannerCallback(CallbackData, prefix="banner"):
    """Banner browsing and pull callback."""

    action: str
    banner_id: int
    count: int = 1


class BattleQueueCallback(CallbackData, prefix="battleq"):
    """Battle matchmaking callbacks."""

    action: str


class BattleCallback(CallbackData, prefix="battle"):
    """Battle round and action callbacks."""

    action: str
    card_id: int = 0


class BattlePassCallback(CallbackData, prefix="bp"):
    """Battle pass player actions."""

    action: str


class PremiumBattlePassCallback(CallbackData, prefix="pbp"):
    """Premium battle pass player actions."""

    action: str


class DeckCallback(CallbackData, prefix="deck"):
    """Deck constructor callbacks."""

    action: str
    card_id: int = 0


class FreeRewardCallback(CallbackData, prefix="free"):
    """Free reward callbacks."""

    action: str


class ClanCallback(CallbackData, prefix="clan"):
    """Clan actions callback."""

    action: str


class TopCallback(CallbackData, prefix="top"):
    """Users-top mode switch callback."""

    mode: str


class IdeaCallback(CallbackData, prefix="idea"):
    """Idea browsing, voting, and moderation callback."""

    action: str
    idea_id: int = 0
    page: int = 1
    scope: str = "published"


class AdminCallback(CallbackData, prefix="admin"):
    """Admin dashboard callback."""

    action: str
    value: str = ""
    item_id: int = 0
    card_id: int = 0
    banner_id: int = 0
    season_id: int = 0
