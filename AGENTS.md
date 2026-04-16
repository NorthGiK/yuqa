# Repository Guidelines

## Fast Start
- Run `make agent-summary` first. It prints the current architecture map, runtime flow, grouped edit paths, feature coverage, and hotspot files.
- Run `make agent-check` before and after edits when touching domain code.
- Use `make test-file FILE=...` for focused loops and `make test` before finishing.

## Runtime Flow
1. `main.py`: tiny CLI shim.
2. `yuqa/main.py`: loads env, optionally runs migrations, builds the app, starts polling.
3. `yuqa/telegram/services.py`: chooses storage mode, wires repositories, and holds shared service helpers.
4. `yuqa/telegram/services_battles.py`: battle drafting, round resolution, and matchmaking.
5. `yuqa/telegram/services_battle_pass.py`: battle pass seasons, levels, and progress flows.
6. `yuqa/telegram/services_players.py`: player lookup, profile, free rewards, and deck construction.
7. `yuqa/telegram/services_social.py`: clans and ideas.
8. `yuqa/telegram/services_content.py`: cards, banners, shop, starter cards, and admin content.
9. `yuqa/telegram/router.py`: registers handlers and FSM flows.
10. `yuqa/telegram/router_views.py`: renders screens reused by handlers.
11. `yuqa/telegram/router_helpers.py`: parsing, pagination, and media extraction helpers.

## Layer Boundaries
- `yuqa/<feature>/domain/`: pure game rules, entities, repositories, and domain services.
- `yuqa/telegram/`: bot transport, callbacks, FSM state, screen rendering, copy, and markup.
- `yuqa/infrastructure/`: adapters for in-memory, JSON-backed, and SQLAlchemy-backed persistence.
- `yuqa/shared/`: enums, IDs, errors, and reusable value objects.
- `yuqa/application/`: app-level abstractions that must stay transport-agnostic.

## Edit Paths
- Domain rule change: start in `yuqa/<feature>/domain/services.py`, then entities/repositories, then feature tests.
- Telegram handler or wizard flow: start in `yuqa/telegram/router.py` and `yuqa/telegram/states.py`.
- Telegram screen, copy, or markup: start in `yuqa/telegram/router_views.py`, then `yuqa/telegram/texts.py` or `yuqa/telegram/texts_<family>.py`, and `yuqa/telegram/ui.py` or `yuqa/telegram/ui_<family>.py`.
- Battle or matchmaking bug: start in `yuqa/telegram/services_battles.py`, then `tests/test_telegram_services.py`.
- Battle pass bug: start in `yuqa/telegram/services_battle_pass.py`, then `tests/test_quests_battlepass.py` and `tests/test_telegram_services.py`.
- Player/profile/free reward/deck bug: start in `yuqa/telegram/services_players.py`, then `tests/test_telegram_services.py`.
- Clan or idea bug: start in `yuqa/telegram/services_social.py`, then `tests/test_telegram_services.py`.
- Card/banner/shop/admin content bug: start in `yuqa/telegram/services_content.py`, then `tests/test_admin_content.py` and `tests/test_telegram_services.py`.
- Persistence bug: inspect `yuqa/infrastructure/local.py` or `yuqa/infrastructure/sqlalchemy/repositories.py`, then `tests/test_persistence.py`.
- Config or startup issue: inspect `yuqa/telegram/config.py` and `yuqa/main.py`.

## Hotspots
- `yuqa/telegram/services.py`: service container and shared helpers. Keep feature-specific flows in the dedicated service modules.
- `yuqa/telegram/services_battles.py`: battle and matchmaking orchestration.
- `yuqa/telegram/services_battle_pass.py`: season and progress orchestration.
- `yuqa/telegram/services_players.py`: player profile, free reward, and deck orchestration.
- `yuqa/telegram/services_content.py`: cards, banners, shop, and starter-card orchestration.
- `yuqa/telegram/texts.py` and `yuqa/telegram/ui.py`: thin compatibility facades. Prefer editing the matching `texts_<family>.py` or `ui_<family>.py` module.
- `yuqa/telegram/router.py`: handler wiring and wizard state transitions. Keep reusable rendering logic in `router_views.py`.

## Tests
- Domain tests: `tests/test_cards.py`, `tests/test_clans.py`, `tests/test_shop.py`, `tests/test_banners.py`, `tests/test_battle_engine.py`, `tests/test_quests_battlepass.py`.
- Telegram behavior: `tests/test_telegram_layer.py`, `tests/test_telegram_services.py`, `tests/test_router_wiring.py`, `tests/test_reply.py`, `tests/test_telegram_config.py`.
- Persistence: `tests/test_persistence.py`.
- Tooling and repo map: `tests/test_agent_audit.py`.

## Environment
- `BOT_TOKEN` is required.
- `ADMIN_IDS` is a comma-separated list of Telegram user IDs.
- `YUQA_DATA_DIR` defaults to `data/yuqa`.
- If `DATABASE_URL` is blank, the app uses SQLite inside `YUQA_DATA_DIR`.
- `YUQA_AUTO_MIGRATE=true` applies Alembic migrations during startup.

## Coding Rules
- Use Python 3.14, 4-space indentation, and type hints on public APIs.
- Keep domain rules out of `yuqa/telegram/` unless they are transport-specific.
- Prefer smaller helper/view modules over expanding the main router.
- Add happy-path, validation-path, and regression coverage for each change.
