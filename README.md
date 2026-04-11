# Yuqa

Telegram game bot with persistent runtime storage, Alembic migrations, and
container deployment support.

## Local development

```bash
make sync
cp .env.example .env
make db-upgrade
make run
```

By default the bot stores state in SQLite at `data/yuqa/yuqa.db`. Override it
with `DATABASE_URL` to use PostgreSQL or another SQLAlchemy-supported database.

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
