# Repository Guidelines

## Project Structure & Module Organization
`yuqa/` is the main package. Features are split by domain: `cards`, `battles`, `shop`, `clans`, `quests`, `battle_pass`, and `players`. Most domains follow `domain/entities.py`, `domain/services.py`, and `domain/repositories.py`.

`yuqa/telegram/` contains the bot-facing layer, including routers, handlers, texts, UI, and config. `yuqa/infrastructure/` holds adapters such as `memory.py`, `local.py`, and `sqlalchemy/`. Shared enums, IDs, errors, and value objects live in `yuqa/shared/`. Tests mirror the behavior by feature under `tests/`. Runtime catalog data is stored in `data/yuqa/catalog.json`.

## Build, Test, and Development Commands
- `make sync`: install dependencies, including dev tools, with `uv sync --extra dev`.
- `make run`: start the Telegram bot with `uv run yuqa`.
- `make test`: run the full test suite with `uv run pytest -q`.
- `make test-file FILE=tests/test_shop.py`: run one test file.
- `make lint`: run Ruff checks.
- `make format`: format Python files with Ruff.
- `make clean`: remove Python cache directories.

## Coding Style & Naming Conventions
Use Python 3.14, 4-space indentation, and type hints on public APIs. Follow the existing style: `@dataclass(slots=True)` for entities/value objects, `snake_case` for modules/functions/variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants.

Keep domain rules in `domain/services.py` and transport concerns in `yuqa/telegram/`. Use Ruff for formatting and linting before committing.

## Testing Guidelines
Pytest is the test runner, with `pytest-asyncio` configured for `asyncio_mode = auto`. Name files `test_*.py` and tests `test_<behavior>()`. For async flows, use `@pytest.mark.asyncio`.

Each feature change should include happy-path coverage, at least one validation or error-path assertion, and regression coverage for fixed bugs.

## Commit & Pull Request Guidelines
Use Conventional Commits, for example `feat: add clan invite validation` or `fix: prevent negative wallet spend`. Pull requests should include a short problem statement, a summary of changes, and test evidence such as `make test` output. Note any config or data changes, especially updates to `data/yuqa/catalog.json` or required environment variables.

## Security & Configuration Tips
Configuration comes from `BOT_TOKEN` (required), `ADMIN_IDS`, and optional `YUQA_DATA_DIR`. Use `.env.example` as a template, keep secrets in local `.env`, and never commit production tokens.
