"""Battle pass reward claiming."""

from dataclasses import dataclass

from yuqa.battle_pass.domain.entities import BattlePassProgress, BattlePassSeason


@dataclass(slots=True)
class BattlePassService:
    """Track points and claim all unlocked rewards."""

    def add_points(self, progress: BattlePassProgress, points: int) -> None:
        """Increase progress points."""

        progress.points += max(0, points)

    def claim_available_rewards(
        self, progress: BattlePassProgress, season: BattlePassSeason
    ) -> list[int]:
        """Claim every unlocked and unclaimed level."""

        claimed: list[int] = []
        for level in season.levels:
            if (
                level.level_number not in progress.claimed_levels
                and progress.points >= level.required_points
            ):
                progress.claimed_levels.add(level.level_number)
                claimed.append(level.level_number)
        return claimed
