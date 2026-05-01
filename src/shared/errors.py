"""Domain exceptions used across the Yuqa package."""


class DomainError(Exception):
    """Base class for all domain-level failures."""


class ValidationError(DomainError):
    """Raised when an entity or value object is invalid."""


class NotEnoughResourcesError(DomainError):
    """Raised when a wallet cannot cover a spend operation."""


class EntityNotFoundError(DomainError):
    """Raised when a repository lookup returns nothing."""


class ForbiddenActionError(DomainError):
    """Raised when a rule or permission blocks an action."""


class BattleRuleViolationError(DomainError):
    """Raised when battle flow breaks a combat rule."""
