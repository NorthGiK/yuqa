"""Enumerations shared by the Yuqa domain."""

from enum import Enum


class Universe(str, Enum):
    """Anime universe of a card."""
    
    UNKNOWN = "unknown"
    ORIGINAL = "original"
    NARUTO = "naruto"
    ONE_PIECE = "one_piece"
    BLEACH = "bleach"
    JJK = "jjk"
    OTHER = "other"


class Rarity(str, Enum):
    """Card rarity."""
    
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    MYTHIC = "mythic"
    LEGENDARY = "legendary"
    GODLY = "godly"
    BADENKO = "badenko"


class CardClass(str, Enum):
    """Battle role of a card."""
    
    MELEE = "melee"
    TANK = "tank"
    RANGER = "ranger"
    SUPPORT = "support"


class AbilityTarget(str, Enum):
    """Target group for an ability effect."""
    
    SELF = "self"
    TEAMMATES_DECK = "teammates_deck"
    OPPONENTS_DECK = "opponents_deck"


class AbilityStat(str, Enum):
    """Stat affected by an ability effect."""
    
    DAMAGE = "damage"
    HEALTH = "health"
    DEFENSE = "defense"


class CardForm(str, Enum):
    """Visual and stat form of a card."""
    
    BASE = "base"
    ASCENDED = "ascended"


class BannerType(str, Enum):
    """Banner category."""
    
    NORMAL = "normal"
    EVENT = "event"


class ProfileBackgroundRarity(str, Enum):
    """Profile-background rarity."""
    
    EPIC = "epic"
    LEGENDARY = "legendary"
    LIMITED = "limited"


class ResourceType(str, Enum):
    """Wallet resource types."""
    
    COINS = "coins"
    CRYSTALS = "crystals"
    ORBS = "orbs"
    SILVER_TICKETS = "silver_tickets"
    GOLD_TICKETS = "gold_tickets"


class QuestPeriod(str, Enum):
    """Quest refresh period."""
    
    DAILY = "daily"
    WEEKLY = "weekly"


class QuestActionType(str, Enum):
    """Quest completion trigger."""
    
    BATTLE_WIN = "battle_win"
    SHOP_PURCHASE = "shop_purchase"
    CARD_ASCEND = "card_ascend"
    CARD_LEVEL_UP = "card_level_up"


class ClanRole(str, Enum):
    """Clan membership role."""
    
    LEADER = "leader"
    MEMBER = "member"


class BattleActionType(str, Enum):
    """Action types in combat."""
    
    ATTACK = "attack"
    BLOCK = "block"
    BONUS = "bonus"
    USE_ABILITY = "use_ability"
    SWITCH_CARD = "switch_card"


class BattleStatus(str, Enum):
    """Battle lifecycle status."""
    
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"


class RewardType(str, Enum):
    """Banner reward kind."""
    
    RESOURCE = "resource"
    CARD = "card"
    PROFILE_BACKGROUND = "profile_background"


class IdeaStatus(str, Enum):
    """Lifecycle status for user-submitted game ideas."""
    
    PENDING = "pending"
    PUBLISHED = "published"
    COLLECTED = "collected"
    REJECTED = "rejected"
