"""Battle pass operations for TelegramServices."""

from datetime import datetime, timezone

from yuqa.battle_pass.domain.entities import (
    BattlePassLevel,
    BattlePassProgress,
    BattlePassSeason,
)
from yuqa.quests.domain.entities import QuestReward
from yuqa.shared.enums import ResourceType
from yuqa.shared.errors import (
    EntityNotFoundError,
    ForbiddenActionError,
    ValidationError,
)
from yuqa.telegram.services_support import _next_id


class BattlePassServiceMixin:
    """Season, level, and progress helpers for battle pass flows."""

    async def active_battle_pass(self) -> BattlePassSeason | None:
        """Return the currently active battle pass season."""

        return await self._active_season(self.battle_pass_seasons)

    async def list_battle_pass_seasons(self) -> list[BattlePassSeason]:
        """Return every stored battle pass season sorted by dates."""

        return self._list_seasons(self.battle_pass_seasons)

    async def create_battle_pass_season(
        self,
        name: str,
        start_at: datetime,
        end_at: datetime,
    ) -> BattlePassSeason:
        """Create a new battle pass season with explicit dates."""

        return await self._create_season(
            self.battle_pass_seasons,
            name=name,
            start_at=start_at,
            end_at=end_at,
        )

    async def delete_battle_pass_season(self, season_id: int) -> None:
        """Delete an ended battle pass season."""

        await self._delete_finished_season(self.battle_pass_seasons, season_id)

    async def active_premium_battle_pass(self) -> BattlePassSeason | None:
        """Return the currently active premium battle pass season."""

        return await self._active_season(self.premium_battle_pass_seasons)

    async def list_premium_battle_pass_seasons(self) -> list[BattlePassSeason]:
        """Return every stored premium battle pass season sorted by dates."""

        return self._list_seasons(self.premium_battle_pass_seasons)

    async def create_premium_battle_pass_season(
        self,
        name: str,
        start_at: datetime,
        end_at: datetime,
    ) -> BattlePassSeason:
        """Create a new premium battle pass season with explicit dates."""

        return await self._create_season(
            self.premium_battle_pass_seasons,
            name=name,
            start_at=start_at,
            end_at=end_at,
        )

    async def delete_premium_battle_pass_season(self, season_id: int) -> None:
        """Delete an ended premium battle pass season."""

        await self._delete_finished_season(self.premium_battle_pass_seasons, season_id)

    async def list_battle_pass_levels(self) -> list[BattlePassLevel]:
        """Return levels from the active battle pass season."""

        season = await self.active_battle_pass()
        return [] if season is None else list(season.levels)

    async def list_premium_battle_pass_levels(self) -> list[BattlePassLevel]:
        """Return levels from the active premium battle pass season."""

        season = await self.active_premium_battle_pass()
        return [] if season is None else list(season.levels)

    async def add_battle_pass_level(
        self,
        level_number: int,
        required_points: int,
        reward: QuestReward,
    ) -> BattlePassSeason:
        """Add or replace a battle pass level in the active season."""

        return await self._add_level_to_active_season(
            self.active_battle_pass,
            self.battle_pass_seasons,
            level_number=level_number,
            required_points=required_points,
            reward=reward,
        )

    async def add_premium_battle_pass_level(
        self,
        level_number: int,
        required_points: int,
        reward: QuestReward,
    ) -> BattlePassSeason:
        """Add or replace a level in the active premium battle pass season."""

        return await self._add_level_to_active_season(
            self.active_premium_battle_pass,
            self.premium_battle_pass_seasons,
            level_number=level_number,
            required_points=required_points,
            reward=reward,
        )

    async def active_battle_pass_progress(self, player_id: int) -> BattlePassProgress:
        """Return the active season progress for a player."""

        return await self._active_progress_for(
            self.battle_pass_progress,
            self.active_battle_pass,
            player_id,
        )

    async def active_premium_battle_pass_progress(
        self, player_id: int
    ) -> BattlePassProgress:
        """Return the active premium season progress for a player."""

        return await self._active_progress_for(
            self.premium_battle_pass_progress,
            self.active_premium_battle_pass,
            player_id,
        )

    async def buy_battle_pass_level(
        self, telegram_id: int
    ) -> tuple[BattlePassProgress, int]:
        """Buy the next unclaimed battle pass level for 250 coins."""

        return await self._buy_next_level(
            telegram_id=telegram_id,
            season_getter=self.active_battle_pass,
            progress_getter=self.active_battle_pass_progress,
            progress_repository=self.battle_pass_progress,
        )

    async def buy_premium_battle_pass_level(
        self, telegram_id: int
    ) -> tuple[BattlePassProgress, int]:
        """Buy the next unclaimed premium battle pass level for 250 coins."""

        return await self._buy_next_level(
            telegram_id=telegram_id,
            season_getter=self.active_premium_battle_pass,
            progress_getter=self.active_premium_battle_pass_progress,
            progress_repository=self.premium_battle_pass_progress,
            require_premium=True,
        )

    async def _active_season(self, repository) -> BattlePassSeason | None:
        """Return the latest active season from a repository."""

        now = datetime.now(timezone.utc)
        seasons = [
            season
            for season in await repository.list_active()
            if season.is_active and season.start_at <= now <= season.end_at
        ]
        if not seasons:
            return None
        return sorted(seasons, key=lambda season: (season.start_at, season.id))[-1]

    def _list_seasons(self, repository) -> list[BattlePassSeason]:
        """Return seasons from a repository sorted by most recent first."""

        seasons: list[BattlePassSeason] = list(
            getattr(repository, "items", {}).values()
        )
        return sorted(
            seasons, key=lambda season: (season.start_at, season.id), reverse=True
        )

    async def _create_season(
        self,
        repository,
        *,
        name: str,
        start_at: datetime,
        end_at: datetime,
    ) -> BattlePassSeason:
        """Create one season after validating name and date overlap."""

        if not name.strip():
            raise ValidationError("battle pass name must not be empty")
        if start_at >= end_at:
            raise ValidationError("start_at must be before end_at")
        seasons = self._list_seasons(repository)
        for season in seasons:
            if start_at <= season.end_at and end_at >= season.start_at:
                raise ForbiddenActionError(
                    "battle pass dates overlap with an existing season"
                )
        season = BattlePassSeason(
            id=_next_id(getattr(repository, "items", {})),
            name=name.strip(),
            start_at=start_at,
            end_at=end_at,
            levels=[],
            is_active=True,
        )
        await repository.save(season)
        return season

    async def _delete_finished_season(self, repository, season_id: int) -> None:
        """Delete one finished season from the selected repository."""

        season = await repository.get_by_id(season_id)
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        if season.end_at > datetime.now(timezone.utc):
            raise ForbiddenActionError("battle pass is not finished yet")
        await repository.delete(season_id)

    async def _add_level_to_active_season(
        self,
        season_getter,
        repository,
        *,
        level_number: int,
        required_points: int,
        reward: QuestReward,
    ) -> BattlePassSeason:
        """Add or replace one level in the active season."""

        season = await season_getter()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        now = datetime.now(timezone.utc)
        if not (season.start_at <= now <= season.end_at):
            raise ForbiddenActionError("battle pass season is not active")
        season.levels = [
            level for level in season.levels if level.level_number != level_number
        ]
        season.levels.append(BattlePassLevel(level_number, required_points, reward))
        season.levels.sort(key=lambda level: level.level_number)
        await repository.save(season)
        return season

    async def _active_progress_for(
        self,
        repository,
        season_getter,
        player_id: int,
    ) -> BattlePassProgress:
        """Return progress for the active season, creating it when missing."""

        season = await season_getter()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        progress = await repository.get_for_player(player_id, season.id)
        if progress is None:
            progress = BattlePassProgress(player_id=player_id, season_id=season.id)
            await repository.save(progress)
        return progress

    async def _buy_next_level(
        self,
        *,
        telegram_id: int,
        season_getter,
        progress_getter,
        progress_repository,
        require_premium: bool = False,
    ) -> tuple[BattlePassProgress, int]:
        """Buy and claim the next available level from one battle pass track."""

        season = await season_getter()
        if season is None:
            raise EntityNotFoundError("battle pass season not found")
        player = await self.get_or_create_player(telegram_id)
        if require_premium and not player.is_premium:
            raise ForbiddenActionError(
                "premium battle pass is available only for premium players"
            )
        progress = await progress_getter(telegram_id)
        next_level = next(
            (
                level
                for level in season.levels
                if level.level_number not in progress.claimed_levels
            ),
            None,
        )
        if next_level is None:
            raise ValidationError("battle pass is already fully claimed")
        player.wallet.spend(ResourceType.COINS, 250)
        progress.points = max(progress.points, next_level.required_points)
        progress.claimed_levels.add(next_level.level_number)
        self._apply_battle_pass_reward(player, next_level.reward)
        await self.players.save(player)
        await progress_repository.save(progress)
        return progress, next_level.level_number

    @staticmethod
    def _apply_battle_pass_reward(player, reward: QuestReward) -> None:
        """Apply a claimed battle pass reward directly to the player."""

        if reward.coins:
            player.wallet.add(ResourceType.COINS, reward.coins)
        if reward.crystals:
            player.wallet.add(ResourceType.CRYSTALS, reward.crystals)
        if reward.orbs:
            player.wallet.add(ResourceType.ORBS, reward.orbs)
        if reward.battle_pass_points:
            player.battle_pass_progress.append(reward.battle_pass_points)


__all__ = ["BattlePassServiceMixin"]
