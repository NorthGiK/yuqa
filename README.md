# Yuqa

Telegram game bot with persistent runtime storage, Alembic migrations, and
container deployment support.

English | [Русский](README.ru.md)

## For Players

Yuqa is a Telegram game, not a separate desktop or mobile app.

You play it inside Telegram by opening the bot and using commands, buttons, and
menus. The game includes profile progression, cards, battles, quests, clans,
the shop, banners, and battle pass systems. Your progress is stored
persistently, so your account does not reset when the service restarts.

If you are only playing, you do not need the development notes below. The
important part is that Yuqa keeps your game state, inventory, and rewards in
storage between sessions.

## Local development

```bash
make sync
cp .env.example .env
make agent-summary
make db-upgrade
make run
```

By default the bot stores state in SQLite at `data/yuqa/yuqa.db`. Override it
with `DATABASE_URL` to use PostgreSQL or another SQLAlchemy-supported database.

Runtime logging is controlled by:

- `YUQA_LOG_LEVEL`: standard Python log level, default `INFO`
- `YUQA_LOG_FORMAT`: `plain` for local runs or `json` for containers

## Package layout

The Telegram layer is split into package directories rather than one large flat
module set:

- `src/telegram/router/` for handler registration, wizard steps, and reusable views
- `src/telegram/services/` for storage selection, typed mixin contracts, and
  orchestration mixins
- `src/telegram/texts/` for copy and text-formatting helpers
- `src/telegram/ui/` for keyboards and inline markup

Import from the stable package roots:

- `src.telegram.router`
- `src.telegram.services`
- `src.telegram.texts`
- `src.telegram.ui`

Edit the implementation modules inside those directories when behavior changes.

## Typing conventions

- Repository adapters should expose concrete return types for their async
  methods, even when they share a small generic base class.
- Telegram service mixins use protocol contracts from
  `src/telegram/services/contracts.py`; update those contracts when a mixin
  starts depending on a new repository or service attribute.
- Add comments only around non-obvious runtime decisions, such as persistence
  pragmas or bootstrap side effects. Prefer type hints and clear names for
  ordinary control flow.

## Quest action completion

Routers can complete cooldown-based action quests through one service call:

```python
await services.complete_action_quest(
    quest=QuestDefinition(
        id=101,
        period=QuestPeriod.DAILY,
        action_type=QuestActionType.CARD_LEVEL_UP,
        reward=QuestReward(coins=25),
        cooldown=timedelta(hours=2),
    ),
    player_id=telegram_id,
)
```

The helper checks the player's quest cooldown, applies the supplied reward only
when the quest is ready, and persists the next cooldown timestamp.

For handler code that should trigger the quest automatically, import
`quest_init` from `src.telegram.decorators`. It resolves the Telegram player
id from the incoming message or callback and delegates to the same persistent
quest service path.

## Transactional writes

Write-heavy service flows run inside a guarded transaction wrapper so related
state changes commit together and roll back together on failure. This keeps
quest rewards, battle updates, purchases, deck changes, and admin content
changes consistent when several players act at the same time.

## Observability

Startup logs include sanitized runtime settings, migration start/finish timing,
service initialization timing, Telegram polling lifecycle, and graceful shutdown
events. Database passwords are hidden before URLs are written to logs.

The deployment healthcheck can be run directly:

```bash
python -m src.infrastructure.sqlalchemy.healthcheck
```

It prints one JSON object and exits non-zero when the database is unreachable,
required runtime tables are missing, or the database revision is not at the
current Alembic head.

## AI-agent workflow

The repository includes an agent-focused inspection script and guide:

```bash
make agent-summary
make agent-check
```

- `make agent-summary` prints a compact JSON map of entrypoints, features,
  storage modes, stable package surfaces, and hotspot files.
- `make agent-check` validates a few layer boundaries so domain modules do not
  quietly depend on Telegram or persistence adapters.
- `docs/ai-agents.md` provides the shortest path to the correct modules for
  runtime, transport, domain, and persistence work in the current package
  layout.

## Stress testing

Run a local randomized service-level stress simulation with:

```bash
make stress
make stress STRESS_ARGS="--players 100 --operations-per-player 200 --concurrency 50"
```

The harness in `scripts/stress_app.py` creates a temporary SQLite database,
seeds catalog content, simulates many concurrent players across profile,
economy, collection, quest, idea, and battle flows, and prints JSON metrics for
latency, throughput, expected domain-rule rejections, failures, CPU time, and
memory. Pass `--database-url` when you want to measure a specific database.

## Persistence model

- ORM tables are split across `src/infrastructure/sqlalchemy/models/` instead
  of living in one flat module.
- SQLAlchemy repositories use per-aggregate relational tables instead of a
  single application-state JSON document. The relational migration copies old
  `state_documents` data into the new tables and then drops the legacy table.
- Static catalog data from `data/yuqa/catalog.json` is imported into the
  database on the first boot.
- Runtime state such as players, cards, clans, finished battle results, and
  deck drafts is persisted so restarts do not reset player progress.
- Quest definitions and per-player quest cooldowns are persisted with runtime
  state.
- Active battles and matchmaking queues are cleared on service startup because
  in-progress combat timers are runtime-only.
- Alembic manages schema changes via `make db-upgrade`.

## Docker deployment

```bash
docker build -f docker/Dockerfile -t yuqa:latest .
```

The container image copies the application source, runs `uv sync` during build,
installs from `uv.lock`, and starts the installed `yuqa` entrypoint. It does not
copy `.env` into the image. The image is built for PostgreSQL use, so set
`DATABASE_URL` to a PostgreSQL connection string when running it. If you want
persistent state outside the container, mount `/data` only for catalog artifacts
or local experiments.

Production deploys should use `docker/compose.yaml`, which starts the bot and a
PostgreSQL service together. The bot container runs as a non-root user with a
read-only root filesystem, dropped Linux capabilities, `no-new-privileges`, a
small `/tmp` tmpfs, JSON logs, log rotation, health checks, and a graceful stop
period.

## CI/CD guidance

A deployment pipeline should run lint and tests, build a versioned container
image, ship the production `.env` outside the image, and deploy
`docker/compose.yaml` with `docker compose up -d --wait`.

Typical deployment variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_KEY`
- `DEPLOY_ENV_FILE`
