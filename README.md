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

## AI-agent workflow

The repository includes an agent-focused inspection script and guide:

```bash
make agent-summary
make agent-check
```

- `make agent-summary` prints a compact JSON map of entrypoints, features,
  storage modes, and hotspot files.
- `make agent-check` validates a few layer boundaries so domain modules do not
  quietly depend on Telegram or persistence adapters.
- `docs/ai-agents.md` provides the shortest path to the correct modules for
  runtime, transport, domain, and persistence work.

## Persistence model

- Static catalog data from `data/yuqa/catalog.json` is imported into the
  database on the first boot.
- Runtime state such as players, cards, clans, battles, matchmaking queue, and
  drafts is persisted so restarts do not reset player progress.
- Alembic manages schema changes via `make db-upgrade`.

## Docker deployment

```bash
docker build -t yuqa:latest .
docker compose up -d
```

`compose.yaml` mounts `/data` as a persistent volume, enables container
healthchecks, and restarts the bot automatically if it crashes.

## GitLab CI/CD

`.gitlab-ci.yml` runs lint and test stages, builds a versioned container image,
and deploys it over SSH with `docker compose up -d --wait`.

Required CI/CD variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_KEY`
- `DEPLOY_ENV_FILE`
