# AI Agent Guide

## Fast path

1. Run `make agent-summary` to get a compact JSON map of the repository.
2. Run `make agent-check` before and after edits to catch layer violations.
3. For a runtime issue, start in `yuqa/main.py`, then follow into `yuqa/telegram/services.py` and `yuqa/telegram/router.py`.
4. For feature rules, work inside `yuqa/<feature>/domain/`.
5. For storage issues, inspect `yuqa/infrastructure/local.py` and `yuqa/infrastructure/sqlalchemy/repositories.py`.

## Stable architecture boundaries

- `yuqa/<feature>/domain/` holds entities, repositories, and domain services.
- `yuqa/telegram/` is the transport layer. Keep bot handlers, callbacks, texts, and UI here.
- `yuqa/infrastructure/` is for adapters only.
- `yuqa/shared/` should stay dependency-light and reusable across features.

## Runtime shape

- `main.py` is the CLI entrypoint.
- `yuqa/main.py` loads settings, optionally applies migrations, builds services, and starts polling.
- `TelegramServices` chooses one of three storage modes:
  - memory: `TelegramServices()`
  - JSON catalog: `TelegramServices(content_path=...)`
  - database: `TelegramServices(content_path=..., database_url=...)`

## Hotspots

- `yuqa/telegram/router.py` is large and owns most command and callback wiring.
- `yuqa/telegram/services.py` is large and owns most application orchestration.
- Before editing either file, confirm there is not already a smaller domain service or repository that should absorb the logic instead.

## Test strategy

- Use `make test-file FILE=...` for focused iteration.
- In-memory `TelegramServices()` is the fastest way to exercise behavior without persistence setup.
- Persistence behavior is covered separately in `tests/test_persistence.py`.

## Agent heuristics

- Prefer changing domain modules over adding logic directly to the Telegram router.
- Add regression tests beside the feature you changed.
- If an edit crosses transport and domain boundaries, stop and verify the split is still coherent.
