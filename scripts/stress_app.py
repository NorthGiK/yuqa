"""Run a local randomized stress simulation against Yuqa services.

The harness avoids Telegram network calls and drives the application through
the same service layer used by handlers. This keeps the run deterministic
enough for local development while still exercising persistence, cooldowns,
economy rules, collections, quests, ideas, and battle matchmaking.
"""

import argparse
import asyncio
import json
import resource
import statistics
import tempfile
import time
import tracemalloc
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from random import Random, randint
from typing import Any

from src.cards.domain.entities import Ability
from src.quests.domain.entities import QuestDefinition, QuestReward
from src.shared.enums import (
    BannerType,
    CardClass,
    IdeaStatus,
    ProfileBackgroundRarity,
    QuestActionType,
    QuestPeriod,
    Rarity,
    ResourceType,
    Universe,
)
from src.shared.errors import DomainError
from src.shared.value_objects.deck_slots import DeckSlots
from src.shared.value_objects.stat_block import StatBlock
from src.telegram.services import TelegramServices


type Operation = Callable[[TelegramServices, int, Random], Awaitable[None]]


@dataclass(slots=True)
class StressConfig:
    """Runtime knobs for one stress simulation."""

    players: int
    operations_per_player: int
    concurrency: int
    seed: int
    database_url: str | None


@dataclass(slots=True)
class OperationMetrics:
    """Mutable metrics collected by concurrent workers."""
    
    latencies_ms: list[float] = field(default_factory=list)
    successes: Counter[str] = field(default_factory=Counter)
    domain_rejections: Counter[str] = field(default_factory=Counter)
    errors: Counter[str] = field(default_factory=Counter)
    
    def record_success(self, operation: str, elapsed_ms: float) -> None:
        self.latencies_ms.append(elapsed_ms)
        self.successes[operation] += 1
    
    def record_domain_rejection(
        self,
        operation: str,
        error: DomainError,
        elapsed_ms: float,
    ) -> None:
        self.latencies_ms.append(elapsed_ms)
        self.domain_rejections[f"{operation}:{type(error).__name__}"] += 1
    
    def record_error(
        self,
        operation: str,
        error: Exception,
        elapsed_ms: float,
    ) -> None:
        self.latencies_ms.append(elapsed_ms)
        self.errors[f"{operation}:{type(error).__name__}"] += 1


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.expanduser().resolve().as_posix()}"


async def seed_catalog(services: TelegramServices) -> list[int]:
    """Create enough content for player, shop, banner, and battle flows."""
    
    template_ids: list[int] = []
    rarities = [
        Rarity.COMMON,
        Rarity.RARE,
        Rarity.EPIC,
        Rarity.MYTHIC,
        Rarity.LEGENDARY,
    ]
    for index, rarity in enumerate(rarities, start=1):
        template = await services.create_card_template(
            name=f"Stress Card {index}",
            universe=Universe.ORIGINAL,
            rarity=rarity,
            image_key=f"stress/card-{index}.png",
            card_class=CardClass.MELEE,
            base_stats=StatBlock(
                damage=10 + index,
                health=90 + index * 5,
                defense=4 + index,
            ),
            ascended_stats=StatBlock(
                damage=20 + index,
                health=140 + index * 5,
                defense=8 + index,
            ),
            ability=Ability(cost=1, cooldown=1),
        )
        template_ids.append(template.id)

    await services.set_standard_cards(template_ids)
    banner = await services.create_banner(
        "Stress Banner",
        BannerType.NORMAL,
        ResourceType.SILVER_TICKETS,
        start_at=None,
    )
    for template_id in template_ids:
        await services.add_banner_reward_card(
            banner.id,
            template_id,
            weight=10,
            guaranteed_for_10_pull=template_id == template_ids[-1],
        )
    await services.create_shop_item(
        sell_resource_type=ResourceType.CRYSTALS,
        buy_resource_type=ResourceType.COINS,
        price=10,
        quantity=1,
    )
    await services.create_profile_background(
        rarity=ProfileBackgroundRarity.EPIC,
        media_key="stress/profile-background.png",
        content_type="image/png",
        original_name="stress-profile-background.png",
    )
    return template_ids


async def seed_players(
    services: TelegramServices,
    player_ids: list[int],
) -> None:
    """Create players with enough resources and starter decks for random flows."""

    for index, player_id in enumerate(player_ids):
        player = await services.get_or_create_player(player_id)
        player.wallet.add(ResourceType.COINS, 1_000_000)
        player.wallet.add(ResourceType.CRYSTALS, 10_000)
        player.wallet.add(ResourceType.ORBS, 1_000)
        player.wallet.add(ResourceType.SILVER_TICKETS, 10_000)
        player.wallet.add(ResourceType.GOLD_TICKETS, 1_000)
        player.rating = 1_000 + index % 50
        player.is_premium = index % 3 == 0
        cards = await services.list_player_cards(player_id)
        if len(cards) >= 5:
            player.battle_deck = DeckSlots(tuple(card.id for card in cards[:5]))
        await services.players.save(player)


async def op_profile(services: TelegramServices, player_id: int, rng: Random) -> None:
    await services.get_or_create_player(player_id)
    await services.free_rewards_status(player_id)
    await services.list_player_cards(player_id)
    await services.list_top_players(
        rng.choice(["rating", "badenko_cards", "creator_points"])
    )
    await services.admin_counts()


async def op_economy(services: TelegramServices, player_id: int, rng: Random) -> None:
    choice = rng.randrange(4)
    if choice == 0:
        await services.claim_free_resources(player_id)
    elif choice == 1:
        await services.claim_free_card(player_id)
    elif choice == 2:
        item_id = rng.choice(list(services.shop.items))
        await services.purchase_shop_item(player_id, item_id)
    else:
        banner_id = rng.choice(list(services.banners.items))
        await services.pull_banner(player_id, banner_id, rng.choice([1, 10]))


async def op_collection(
    services: TelegramServices, player_id: int, rng: Random
) -> None:
    template_id = rng.choice(list(services.card_templates.items))
    if rng.random() < 0.55:
        await services.grant_card_to_player(player_id, template_id)
        return
    cards = await services.list_player_cards(player_id)
    if not cards:
        return
    card = rng.choice(cards)
    if rng.random() < 0.8:
        await services.level_up_card(player_id, card.id)
    else:
        await services.ascend_card(player_id, card.id)


async def op_social(services: TelegramServices, player_id: int, rng: Random) -> None:
    if rng.random() < 0.65:
        await services.propose_idea(
            player_id,
            f"Stress idea {player_id}-{rng.randrange(1_000_000)}",
            "Generated during local stress simulation.",
        )
        return
    await services.list_ideas(IdeaStatus.PENDING, page=rng.randint(1, 5))


async def op_quest(services: TelegramServices, player_id: int, rng: Random) -> None:
    action_type = rng.choice(list(QuestActionType))
    quest = QuestDefinition(
        id=10_000 + list(QuestActionType).index(action_type),
        period=QuestPeriod.DAILY,
        action_type=action_type,
        reward=QuestReward(coins=5, battle_pass_points=1),
        cooldown=timedelta(seconds=30),
    )
    await services.complete_action_quest(quest, player_id)


async def op_battle(services: TelegramServices, player_id: int, rng: Random) -> None:
    battle = await services.get_active_battle(player_id)
    if battle is None:
        if rng.random() < 0.8:
            await services.search_battle(player_id)
        else:
            await services.cancel_battle_search(player_id)
        return
    if rng.random() < 0.7:
        await services.record_battle_action(
            player_id,
            rng.choice(["attack", "block", "bonus", "ability"]),
        )
    else:
        services.battle_round_summary(battle, player_id)


OPERATIONS: dict[str, Operation] = {
    "profile": op_profile,
    "economy": op_economy,
    "collection": op_collection,
    "social": op_social,
    "quest": op_quest,
    "battle": op_battle,
}


async def run_player(
    services: TelegramServices,
    player_id: int,
    config: StressConfig,
    metrics: OperationMetrics,
    limiter: asyncio.Semaphore,
) -> None:
    rng = Random(config.seed + player_id)
    operation_names = list(OPERATIONS)
    for _ in range(config.operations_per_player):
        operation_name = rng.choice(operation_names)
        operation = OPERATIONS[operation_name]
        started = time.perf_counter()
        async with limiter:
            try:
                await operation(services, player_id, rng)
            except DomainError as error:
                elapsed_ms = (time.perf_counter() - started) * 1000
                metrics.record_domain_rejection(operation_name, error, elapsed_ms)
            except Exception as error:  # noqa: BLE001
                elapsed_ms = (time.perf_counter() - started) * 1000
                metrics.record_error(operation_name, error, elapsed_ms)
            else:
                elapsed_ms = (time.perf_counter() - started) * 1000
                metrics.record_success(operation_name, elapsed_ms)


def latency_summary(latencies_ms: list[float]) -> dict[str, float]:
    """Return compact latency percentiles for JSON output."""

    if not latencies_ms:
        return {}
    values = sorted(latencies_ms)
    last_index = len(values) - 1

    def percentile(percent: float) -> float:
        index = min(last_index, round(last_index * percent))
        return round(values[index], 3)

    return {
        "min_ms": round(values[0], 3),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": percentile(0.50),
        "p90_ms": percentile(0.90),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
        "max_ms": round(values[-1], 3),
    }


def usage_snapshot(start_usage: resource.struct_rusage) -> dict[str, float]:
    """Return process resource counters since the stress phase began."""

    end_usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "user_cpu_seconds": round(end_usage.ru_utime - start_usage.ru_utime, 3),
        "system_cpu_seconds": round(end_usage.ru_stime - start_usage.ru_stime, 3),
        "max_rss_mb": round(end_usage.ru_maxrss / 1024, 3),
        "minor_page_faults": float(end_usage.ru_minflt - start_usage.ru_minflt),
        "major_page_faults": float(end_usage.ru_majflt - start_usage.ru_majflt),
    }


async def run_stress(config: StressConfig) -> dict[str, Any]:
    """Run one complete stress simulation and return JSON-serializable metrics."""
    
    player_ids = [1_000_000 + i for i in range(config.players)]
    temporary_dir: tempfile.TemporaryDirectory[str] | None = None
    database_url = config.database_url
    if database_url is None:
        temporary_dir = tempfile.TemporaryDirectory(prefix="yuqa-stress-")
        database_url = _sqlite_url(Path(temporary_dir.name) / "yuqa.db")
    
    services = TelegramServices(database_url=database_url)
    try:
        await seed_catalog(services)
        await seed_players(services, player_ids)
        
        metrics = OperationMetrics()
        limiter = asyncio.Semaphore(config.concurrency)
        tracemalloc.start()
        start_usage = resource.getrusage(resource.RUSAGE_SELF)
        started = time.perf_counter()
        
        await asyncio.gather(
            *(
                run_player(services, player_id, config, metrics, limiter)
                for player_id in player_ids
            )
        )

        elapsed_seconds = time.perf_counter() - started
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        await services.flush()

        total_attempts = config.players * config.operations_per_player
        completed = sum(metrics.successes.values())
        rejected = sum(metrics.domain_rejections.values())
        failed = sum(metrics.errors.values())
        report = {
            "config": {
                "players": config.players,
                "operations_per_player": config.operations_per_player,
                "concurrency": config.concurrency,
                "seed": config.seed,
                "database_url": database_url,
            },
            "totals": {
                "attempted": total_attempts,
                "succeeded": completed,
                "domain_rejected": rejected,
                "failed": failed,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "throughput_ops_per_second": round(total_attempts / elapsed_seconds, 2)
                if elapsed_seconds
                else 0,
            },
            "latency": latency_summary(metrics.latencies_ms),
            "operation_successes": dict(metrics.successes),
            "domain_rejections": dict(metrics.domain_rejections),
            "errors": dict(metrics.errors),
            "resources": {
                **usage_snapshot(start_usage),
                "tracemalloc_current_mb": round(current_bytes / 1024 / 1024, 3),
                "tracemalloc_peak_mb": round(peak_bytes / 1024 / 1024, 3),
            },
            "state_counts": {
                "players": len(services.players.items),
                "player_cards": len(services.player_cards.items),
                "ideas": len(services.ideas.items),
                "battles": len(services.battles.items),
                "quest_progress": len(services.quests.progress_items),
                "battle_queue": len(services.search_queue),
            },
        }
        return report
    
    finally:
        await services.shutdown()
        if temporary_dir is not None:
            temporary_dir.cleanup()


def parse_args() -> StressConfig:
    parser = argparse.ArgumentParser(
        description="Stress Yuqa services with concurrent randomized player actions.",
    )
    parser.add_argument("--players", type=int, default=100)
    parser.add_argument("--operations-per-player", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--seed", type=int, default=randint(1, 2**32))
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional SQLAlchemy URL. Defaults to a temporary SQLite database.",
    )
    args = parser.parse_args()
    
    def _less_than_zero(arg: str):
        parser.error(f"{arg} must be > 0")
    
    if args.players <= 0:
        _less_than_zero("--players")
    if args.operations_per_player <= 0:
        _less_than_zero("--operations-per-player")
    if args.concurrency <= 0:
        _less_than_zero("--concurrency")
    
    return StressConfig(
        players=args.players,
        operations_per_player=args.operations_per_player,
        concurrency=args.concurrency,
        seed=args.seed,
        database_url=args.database_url,
    )


async def main() -> None:
    report = await run_stress(parse_args())
    print("\r", json.dumps(report, indent="\t", ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
