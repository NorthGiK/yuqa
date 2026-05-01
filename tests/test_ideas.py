"""Direct tests for the ideas domain service."""

import pytest

from src.ideas.domain.entities import Idea
from src.ideas.domain.services import IdeaService
from src.shared.enums import IdeaStatus
from src.shared.errors import ForbiddenActionError, ValidationError


def test_create_idea_trims_fields_and_starts_pending() -> None:
    """New ideas should be normalized and start in review."""

    service = IdeaService()

    idea = service.create(1, 42, "  Новая механика  ", "  Достаточно длинное описание  ")

    assert idea.id == 1
    assert idea.player_id == 42
    assert idea.title == "Новая механика"
    assert idea.description == "Достаточно длинное описание"
    assert idea.status == IdeaStatus.PENDING


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("no", "Достаточно длинное описание"),
        ("Хороший заголовок", "коротко"),
    ],
)
def test_create_idea_validates_title_and_description(
    title: str, description: str
) -> None:
    """Ideas should reject short titles and descriptions."""

    service = IdeaService()

    with pytest.raises(ValidationError):
        service.create(1, 42, title, description)


def test_publish_collect_and_reject_follow_lifecycle_rules() -> None:
    """Ideas should move only through valid lifecycle transitions."""

    service = IdeaService()
    idea = service.create(1, 42, "Идея", "Достаточно длинное описание")

    published = service.publish(idea)
    assert published.status == IdeaStatus.PUBLISHED

    collected = service.collect(idea)
    assert collected.status == IdeaStatus.COLLECTED

    with pytest.raises(ForbiddenActionError):
        service.reject(idea)


def test_reject_can_archive_pending_or_published_idea() -> None:
    """Pending and published ideas may be rejected, but only once."""

    service = IdeaService()
    pending = service.create(1, 42, "Идея", "Достаточно длинное описание")
    published = service.create(2, 42, "Идея 2", "Еще одно длинное описание")
    service.publish(published)

    assert service.reject(pending).status == IdeaStatus.REJECTED
    assert service.reject(published).status == IdeaStatus.REJECTED

    with pytest.raises(ForbiddenActionError):
        service.reject(published)


def test_vote_requires_published_state_valid_direction_and_single_vote() -> None:
    """Voting should only work on public ideas and only once per player."""

    service = IdeaService()
    idea = service.create(1, 42, "Идея", "Достаточно длинное описание")

    with pytest.raises(ForbiddenActionError):
        service.vote(idea, 100, 1)

    service.publish(idea)
    service.vote(idea, 100, 1)
    service.vote(idea, 101, -1)

    assert idea.upvotes == 1
    assert idea.downvotes == 1
    assert idea.vote_of(100) == 1
    assert idea.vote_of(101) == -1

    with pytest.raises(ValidationError):
        service.vote(idea, 102, 0)
    with pytest.raises(ForbiddenActionError):
        service.vote(idea, 100, -1)


def test_idea_entity_counts_votes_from_vote_map() -> None:
    """Vote counters should derive from the stored vote map."""

    idea = Idea(
        id=1,
        player_id=42,
        title="Идея",
        description="Достаточно длинное описание",
        votes={1: 1, 2: 1, 3: -1},
    )

    assert idea.upvotes == 2
    assert idea.downvotes == 1
    assert idea.vote_of(3) == -1
    assert idea.vote_of(99) is None
