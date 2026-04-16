# AI Agent Guide

## One-Minute Read
1. Run `make agent-summary`.
2. Read `AGENTS.md`.
3. Only open this file if you need the longer map or task-specific edit paths.

## Codebase Shape
- `main.py` is only a launcher.
- `yuqa/main.py` is the runtime bootstrap.
- `yuqa/telegram/services.py` is the service container and storage selector.
- `yuqa/telegram/services_battles.py` owns battle drafting, round resolution, and matchmaking.
- `yuqa/telegram/services_battle_pass.py` owns battle pass seasons, levels, and progress.
- `yuqa/telegram/services_players.py` owns player lookup, profiles, free rewards, and deck construction.
- `yuqa/telegram/services_social.py` owns clans and ideas.
- `yuqa/telegram/services_content.py` owns cards, banners, shop items, starter cards, and content-admin flows.
- `yuqa/telegram/services_support.py` holds small shared service helpers.
- `yuqa/telegram/router.py` owns handler registration and FSM flows.
- `yuqa/telegram/router_views.py` owns reusable screens and admin section rendering.
- `yuqa/telegram/router_helpers.py` owns parsing, pagination, and media extraction.
- `yuqa/telegram/texts.py` is the compatibility facade for `texts_<family>.py`.
- `yuqa/telegram/ui.py` is the compatibility facade for `ui_<family>.py`.

## Stable Boundaries
- Domain packages in `yuqa/<feature>/domain/` must not import Telegram or infrastructure.
- `yuqa/telegram/` is allowed to depend on domain and shared code.
- `yuqa/infrastructure/` adapts storage and serialization only.
- `yuqa/shared/` should stay dependency-light.
- `yuqa/application/` must remain transport-agnostic.

## Storage Modes
- `TelegramServices()`:
  Fastest path for tests and isolated logic work.
- `TelegramServices(content_path=...)`:
  JSON-backed catalog/runtime storage without SQLAlchemy.
- `TelegramServices(content_path=..., database_url=...)`:
  Persistent database-backed runtime with Alembic migrations.

## Task Playbooks

### Runtime Bug
Open these files in order:
1. `yuqa/main.py`
2. `yuqa/telegram/services.py`
3. `yuqa/telegram/services_battles.py`
4. `yuqa/telegram/services_battle_pass.py`
5. `yuqa/telegram/services_players.py`
6. `yuqa/telegram/services_content.py`
7. `yuqa/telegram/router.py`
8. `yuqa/telegram/router_views.py`

### New Domain Rule
Open:
1. `yuqa/<feature>/domain/entities.py`
2. `yuqa/<feature>/domain/services.py`
3. `yuqa/<feature>/domain/repositories.py`
4. The matching test file in `tests/`

### Telegram UI or Copy Change
Open:
1. `yuqa/telegram/router_views.py`
2. `yuqa/telegram/texts.py`
3. The matching `yuqa/telegram/texts_<family>.py`
4. `yuqa/telegram/ui.py`
5. The matching `yuqa/telegram/ui_<family>.py`
4. `tests/test_telegram_layer.py`

### Wizard or Handler Flow Change
Open:
1. `yuqa/telegram/router.py`
2. `yuqa/telegram/states.py`
3. `tests/test_router_wiring.py`
4. `tests/test_telegram_services.py`

### Persistence Bug
Open:
1. `yuqa/infrastructure/sqlalchemy/repositories.py`
2. `yuqa/infrastructure/sqlalchemy/models.py`
3. `yuqa/infrastructure/local.py`
4. `tests/test_persistence.py`

## Hotspots
- `yuqa/telegram/services.py`
- `yuqa/telegram/services_battles.py`
- `yuqa/telegram/services_battle_pass.py`
- `yuqa/telegram/services_players.py`
- `yuqa/telegram/services_content.py`
- `yuqa/telegram/router.py`

Before expanding those files, confirm the logic cannot live in:
- A feature `domain/services.py`
- `router_views.py`
- `router_helpers.py`
- `texts_<family>.py` or `ui_<family>.py`
- A storage adapter in `yuqa/infrastructure/`

## Test Map
- Domain behavior:
  `tests/test_cards.py`, `tests/test_clans.py`, `tests/test_shop.py`, `tests/test_banners.py`, `tests/test_battle_engine.py`, `tests/test_quests_battlepass.py`
- Telegram transport and UX:
  `tests/test_telegram_layer.py`, `tests/test_telegram_services.py`, `tests/test_router_wiring.py`, `tests/test_reply.py`, `tests/test_telegram_config.py`
- Persistence:
  `tests/test_persistence.py`
- Tooling:
  `tests/test_agent_audit.py`

## Heuristics
- Prefer changing domain modules over embedding rules in Telegram handlers.
- Prefer changing `router_views.py` over adding rendering logic directly inside callbacks.
- Keep callback schemas in `yuqa/telegram/callbacks.py` aligned with router handling.
- Keep text-generation changes in the matching `yuqa/telegram/texts_<family>.py` module and keyboard changes in the matching `yuqa/telegram/ui_<family>.py` module.
- Add focused regression coverage close to the behavior you changed.

## Extra Docs
- `docs/codebase.md`: fuller architecture and package map.
- `yuqa/README.md`: package-level navigation.
- `tests/README.md`: test inventory and where to add coverage.
