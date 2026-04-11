"""Domain rules for player-created mechanic ideas."""

from yuqa.ideas.domain.entities import Idea
from yuqa.shared.enums import IdeaStatus
from yuqa.shared.errors import ForbiddenActionError, ValidationError

_MIN_TITLE_LENGTH = 3
_MAX_TITLE_LENGTH = 80
_MIN_DESCRIPTION_LENGTH = 10
_MAX_DESCRIPTION_LENGTH = 1500


class IdeaService:
    """Validate and transition idea lifecycle state."""

    def create(
        self,
        idea_id: int,
        player_id: int,
        title: str,
        description: str,
    ) -> Idea:
        """Build a validated player proposal."""

        normalized_title = self._normalize_title(title)
        normalized_description = self._normalize_description(description)
        return Idea(
            id=idea_id,
            player_id=player_id,
            title=normalized_title,
            description=normalized_description,
        )

    def publish(self, idea: Idea) -> Idea:
        """Move a pending idea to the public voting page."""

        if idea.status != IdeaStatus.PENDING:
            raise ForbiddenActionError("idea is not waiting for review")
        idea.status = IdeaStatus.PUBLISHED
        return idea

    def collect(self, idea: Idea) -> Idea:
        """Move a published idea to the author's collection."""

        if idea.status != IdeaStatus.PUBLISHED:
            raise ForbiddenActionError("idea is not on the public ideas page")
        idea.status = IdeaStatus.COLLECTED
        return idea

    def reject(self, idea: Idea) -> Idea:
        """Archive an idea outside the public ideas page."""

        if idea.status in {IdeaStatus.COLLECTED, IdeaStatus.REJECTED}:
            raise ForbiddenActionError("idea can no longer be rejected")
        idea.status = IdeaStatus.REJECTED
        return idea

    def vote(self, idea: Idea, player_id: int, direction: int) -> Idea:
        """Record one player's single upvote or downvote."""

        if idea.status != IdeaStatus.PUBLISHED:
            raise ForbiddenActionError("idea is not open for voting")
        if direction not in {1, -1}:
            raise ValidationError("vote direction must be 1 or -1")
        if player_id in idea.votes:
            raise ForbiddenActionError("you can vote only once")
        idea.votes[player_id] = direction
        return idea

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Return a trimmed, validated idea title."""

        value = (title or "").strip()
        if len(value) < _MIN_TITLE_LENGTH:
            raise ValidationError(
                f"title must be at least {_MIN_TITLE_LENGTH} characters"
            )
        if len(value) > _MAX_TITLE_LENGTH:
            raise ValidationError(f"title must be <= {_MAX_TITLE_LENGTH} characters")
        return value

    @staticmethod
    def _normalize_description(description: str) -> str:
        """Return a trimmed, validated idea description."""

        value = (description or "").strip()
        if len(value) < _MIN_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"description must be at least {_MIN_DESCRIPTION_LENGTH} characters"
            )
        if len(value) > _MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"description must be <= {_MAX_DESCRIPTION_LENGTH} characters"
            )
        return value
