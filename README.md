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
    player_id=telegram_id,
    quest_id=101,
    action_type=QuestActionType.CARD_LEVEL_UP,
    reward=QuestReward(coins=25),
    cooldown=timedelta(hours=2),
)
```

The helper checks the player's quest cooldown, applies the supplied reward only
when the quest is ready, and persists the next cooldown timestamp.

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

## Persistence model

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
docker build -t yuqa:latest .
```

The container image copies the application source, runs `uv sync` during build,
and starts the bot with `uv run yuqa`. If you want persistent state outside the
container, mount `/data` into the container and keep the SQLite database there.

## GitLab CI/CD

`.gitlab-ci.yml` runs lint and test stages, builds a versioned container image,
and deploys it over SSH with `docker compose up -d --wait`.

Required CI/CD variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_KEY`
- `DEPLOY_ENV_FILE`
