# Yuqa

Telegram game bot with persistent runtime storage, Alembic migrations, and
container deployment support.

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

- `yuqa/telegram/router/` for handler registration, wizard steps, and reusable views
- `yuqa/telegram/services/` for storage selection, typed mixin contracts, and
  orchestration mixins
- `yuqa/telegram/texts/` for copy and text-formatting helpers
- `yuqa/telegram/ui/` for keyboards and inline markup

Import from the stable package roots:

- `yuqa.telegram.router`
- `yuqa.telegram.services`
- `yuqa.telegram.texts`
- `yuqa.telegram.ui`

Edit the implementation modules inside those directories when behavior changes.

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
- Active battles and matchmaking queues are cleared on service startup because
  in-progress combat timers are runtime-only.
- Alembic manages schema changes via `make db-upgrade`.

## Docker deployment

```bash
docker build -t yuqa:latest .
docker compose up -d
```

`compose.yaml` mounts `/data` as a persistent volume. The image healthcheck
uses the same SQLite URL format as the application, and Compose restarts the
bot automatically if it crashes.

## GitLab CI/CD

`.gitlab-ci.yml` runs lint and test stages, builds a versioned container image,
and deploys it over SSH with `docker compose up -d --wait`.

Required CI/CD variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_KEY`
- `DEPLOY_ENV_FILE`
