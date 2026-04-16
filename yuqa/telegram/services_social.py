"""Ideas and clan flows for TelegramServices."""

from yuqa.clans.domain.entities import Clan
from yuqa.ideas.domain.entities import Idea
from yuqa.players.domain.entities import Player
from yuqa.shared.enums import IdeaStatus
from yuqa.shared.errors import EntityNotFoundError, ForbiddenActionError
from yuqa.telegram.services_support import _next_id


class SocialServiceMixin:
    """Idea moderation and clan management helpers."""

    async def propose_idea(
        self, telegram_id: int, title: str, description: str
    ) -> Idea:
        """Create a new player proposal that waits for admin review."""

        player = await self.get_or_create_player(telegram_id)
        idea = self.idea_service.create(
            _next_id(self.ideas.items),
            player.telegram_id,
            title,
            description,
        )
        await self.ideas.add(idea)
        return idea

    async def get_idea(self, idea_id: int) -> Idea:
        """Return one idea or raise when it is missing."""

        idea = await self.ideas.get_by_id(idea_id)
        if idea is None:
            raise EntityNotFoundError("idea not found")
        return idea

    async def list_ideas(
        self,
        status: IdeaStatus,
        *,
        page: int = 1,
        page_size: int = 10,
        player_id: int | None = None,
    ) -> tuple[list[Idea], bool, bool]:
        """Return one paginated idea slice for the requested status."""

        if page < 1:
            page = 1
        ideas = [
            idea
            for idea in await self.ideas.list_all()
            if idea.status == status
            and (player_id is None or idea.player_id == player_id)
        ]
        ideas = self._sort_ideas(ideas)
        start = (page - 1) * page_size
        end = start + page_size
        return ideas[start:end], page > 1, end < len(ideas)

    async def idea_author(self, idea: Idea) -> Player | None:
        """Resolve the player who proposed the idea."""

        return await self.get_player(idea.player_id)

    async def player_vote_for_idea(self, idea_id: int, telegram_id: int) -> int | None:
        """Return the player's recorded vote for an idea."""

        idea = await self.get_idea(idea_id)
        return idea.vote_of(telegram_id)

    async def vote_for_idea(
        self, telegram_id: int, idea_id: int, direction: int
    ) -> Idea:
        """Cast one upvote or downvote for a published idea."""

        await self.get_or_create_player(telegram_id)
        idea = await self.get_idea(idea_id)
        self.idea_service.vote(idea, telegram_id, direction)
        await self.ideas.save(idea)
        return idea

    async def publish_idea(self, idea_id: int) -> Idea:
        """Accept a pending idea onto the public ideas page."""

        idea = await self.get_idea(idea_id)
        self.idea_service.publish(idea)
        await self.ideas.save(idea)
        return idea

    async def collect_idea(self, idea_id: int) -> Idea:
        """Accept a public idea into the author's collection."""

        idea = await self.get_idea(idea_id)
        self.idea_service.collect(idea)
        await self.ideas.save(idea)
        return idea

    async def reject_idea(self, idea_id: int) -> Idea:
        """Archive an idea away from the public ideas page."""

        idea = await self.get_idea(idea_id)
        self.idea_service.reject(idea)
        await self.ideas.save(idea)
        return idea

    async def create_clan(self, telegram_id: int, name: str, icon: str) -> Clan:
        """Create a clan for the player who started the flow."""

        owner = await self.get_or_create_player(telegram_id)
        if owner.clan_id is not None:
            raise ForbiddenActionError("player is already in a clan")
        clan = Clan(
            id=await self._next_clan_id(),
            owner_player_id=owner.telegram_id,
            name=name,
            icon=icon,
        )
        self.clan_service.create_clan(clan, owner)
        await self.clans.add(clan)
        await self.players.save(owner)
        return clan

    async def join_clan(self, telegram_id: int, clan_id: int) -> Clan:
        """Join an existing clan."""

        player = await self.get_or_create_player(telegram_id)
        clan = await self.clans.get_by_id(clan_id)
        if clan is None:
            raise EntityNotFoundError("clan not found")
        self.clan_service.join_clan(clan, player)
        await self.clans.save(clan)
        await self.players.save(player)
        return clan

    async def leave_clan(self, telegram_id: int) -> None:
        """Leave the current clan."""

        player = await self.get_or_create_player(telegram_id)
        clan = await self.player_clan(player)
        if clan is None:
            raise EntityNotFoundError("clan not found")
        self.clan_service.leave_clan(clan, player)
        await self.clans.save(clan)
        await self.players.save(player)

    @staticmethod
    def _sort_ideas(ideas: list[Idea]) -> list[Idea]:
        """Sort ideas by community support first."""

        return sorted(
            ideas,
            key=lambda idea: (idea.upvotes, -idea.downvotes, idea.id),
            reverse=True,
        )

    async def _next_clan_id(self) -> int:
        return _next_id(self.clans.items)


__all__ = ["SocialServiceMixin"]
