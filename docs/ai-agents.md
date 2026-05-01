# AI Agent Guide

## One-Minute Read
1. Run `make agent-summary`.
2. Read `AGENTS.md`.
3. Use the stable package roots for imports:
   `src.telegram.router`, `src.telegram.services`,
   `src.telegram.texts`, `src.telegram.ui`.
4. Edit the implementation modules inside those directories when behavior
   changes.

## Public Surfaces
- `src.telegram.router`:
  import-stable router API backed by `src/telegram/router/__init__.py` and
  implemented in `src/telegram/router/router.py`.
- `src.telegram.services`:
  import-stable service container API backed by
  `src/telegram/services/__init__.py` and implemented in
  `src/telegram/services/services.py`.
- `src.telegram.texts`:
  import-stable text renderer API backed by `src/telegram/texts/__init__.py`
  and aggregated in `src/telegram/texts/texts.py`.
- `src.telegram.ui`:
  import-stable markup API backed by `src/telegram/ui/__init__.py` and
  aggregated in `src/telegram/ui/ui.py`.

## Codebase Shape
- `main.py` is only a launcher.
- `src/main.py` is the runtime bootstrap.
- `src/telegram/services/services.py` is the service container and storage selector.
- `src/telegram/services/contracts.py` defines type-only mixin contracts for IDE completion.
- `src/telegram/services/battles.py` owns battle drafting, round resolution, and matchmaking.
- `src/telegram/services/battle_pass.py` owns battle pass seasons, levels, and progress.
- `src/telegram/services/players.py` owns player lookup, profiles, free rewards, and deck construction.
- `src/telegram/services/social.py` owns clans and ideas.
- `src/telegram/services/content.py` owns cards, banners, shop items, starter cards, and content-admin flows.
- `src/telegram/services/quests.py` owns cooldown-aware quest completion for player actions.
- `src/telegram/services/support.py` holds small shared service helpers.
- `src/telegram/router/router.py` assembles the router from the public/admin handler modules.
- `src/telegram/router/public.py` owns public command and callback registration.
- `src/telegram/router/admin.py` owns admin command and callback registration.
- `src/telegram/router/wizards_players.py` owns clan, idea, profile, and admin-player wizard steps.
- `src/telegram/router/wizards_progression.py` owns battle pass and free-reward wizard steps.
- `src/telegram/router/wizards_content.py` is the compatibility facade for content-admin wizard families.
- `src/telegram/router/wizards_cards.py` owns universe, card, profile-background, and starter-card wizard steps.
- `src/telegram/router/wizards_banners.py` owns banner creation and banner-reward wizard steps.
- `src/telegram/router/wizards_shop.py` owns shop item wizard steps.
- `src/telegram/router/battle.py` owns battle entry and queue helpers shared by public callbacks.
- `src/telegram/router/views.py` owns reusable screens and admin section rendering.
- `src/telegram/router/helpers.py` owns parsing, pagination, and media extraction.
- `src/telegram/texts/texts.py` re-exports the family text modules.
- `src/telegram/ui/ui.py` re-exports the family UI modules.

## Stable Boundaries
- Domain packages in `src/<feature>/domain/` must not import Telegram or infrastructure.
- `src/telegram/` is allowed to depend on domain and shared code.
- `src/infrastructure/` adapts storage and serialization only.
- `src/shared/` should stay dependency-light.
- `src/application/` must remain transport-agnostic.

## Storage Modes
- `TelegramServices()`:
  isolated temporary SQLite-backed runtime for tests and isolated logic work.
- `TelegramServices(content_path=...)`:
  JSON-backed catalog content with temporary SQLite-backed runtime state.
- `TelegramServices(content_path=..., database_url=...)`:
  persistent database-backed runtime with Alembic migrations.
- Quest definitions and per-player quest cooldowns are part of persisted runtime
  state.

## Task Playbooks

### Runtime Bug
Open these files in order:
1. `src/main.py`
2. `src/telegram/services/__init__.py`
3. `src/telegram/services/services.py`
4. `src/telegram/services/contracts.py`
5. `src/telegram/services/battles.py`
6. `src/telegram/services/battle_pass.py`
7. `src/telegram/services/players.py`
8. `src/telegram/services/content.py`
9. `src/telegram/services/quests.py`
10. `src/telegram/router/__init__.py`
11. `src/telegram/router/router.py`
12. `src/telegram/router/public.py`
13. `src/telegram/router/admin.py`
14. `src/telegram/router/views.py`

### New Domain Rule
Open:
1. `src/<feature>/domain/entities.py`
2. `src/<feature>/domain/services.py`
3. `src/<feature>/domain/repositories.py`
4. The matching test file in `tests/`

### Telegram UI or Copy Change
Open:
1. `src/telegram/router/views.py`
2. `src/telegram/texts/__init__.py`
3. `src/telegram/texts/texts.py`
4. The matching `src/telegram/texts/<family>.py`
5. `src/telegram/ui/__init__.py`
6. `src/telegram/ui/ui.py`
7. The matching `src/telegram/ui/<family>.py`
8. `tests/test_telegram_layer.py`

### Wizard or Handler Flow Change
Open:
1. `src/telegram/router/router.py`
2. `src/telegram/router/public.py` or `src/telegram/router/admin.py`
3. The matching `src/telegram/router/wizards_players.py`, `src/telegram/router/wizards_progression.py`, `src/telegram/router/wizards_cards.py`, `src/telegram/router/wizards_banners.py`, `src/telegram/router/wizards_shop.py`, or `src/telegram/router/battle.py`
4. `src/telegram/states.py`
5. `tests/test_router_wiring.py`
6. `tests/test_telegram_services.py`

### Persistence Bug
Open:
1. `src/infrastructure/sqlalchemy/repositories.py`
2. `src/infrastructure/sqlalchemy/models.py`
3. `src/infrastructure/local.py`
4. `tests/test_persistence.py`

### Quest Action Completion
Open:
1. `src/quests/domain/entities.py`
2. `src/quests/domain/services.py`
3. `src/telegram/services/quests.py`
4. The router that performs the action
5. `tests/test_quests_battlepass.py`

## Hotspots
- `src/telegram/services/services.py`
- `src/telegram/services/contracts.py`
- `src/telegram/services/battles.py`
- `src/telegram/services/battle_pass.py`
- `src/telegram/services/players.py`
- `src/telegram/services/content.py`
- `src/telegram/services/quests.py`
- `src/telegram/router/public.py`
- `src/telegram/router/admin.py`
- `src/telegram/router/wizards_cards.py`
- `src/telegram/router/wizards_banners.py`

Before expanding those files, confirm the logic cannot live in:
- A feature `domain/services.py`
- `router/views.py`
- `router/helpers.py`
- `router/wizards_players.py`, `router/wizards_progression.py`, `router/wizards_cards.py`, `router/wizards_banners.py`, `router/wizards_shop.py`, or `router/battle.py`
- `texts/<family>.py` or `ui/<family>.py`
- A storage adapter in `src/infrastructure/`

## Test Map
- Domain behavior:
  `tests/test_cards.py`, `tests/test_clans.py`, `tests/test_ideas.py`,
  `tests/test_shop.py`, `tests/test_banners.py`,
  `tests/test_battle_engine.py`, `tests/test_quests_battlepass.py`,
  `tests/test_shared.py`
- Telegram transport and UX:
  `tests/test_telegram_layer.py`, `tests/test_telegram_services.py`,
  `tests/test_router_wiring.py`, `tests/test_reply.py`,
  `tests/test_telegram_config.py`, `tests/test_admin_content.py`
- Persistence:
  `tests/test_persistence.py`
- Tooling:
  `tests/test_agent_audit.py`

## Heuristics
- Prefer changing domain modules over embedding rules in Telegram handlers.
- Prefer changing `router/views.py` over adding rendering logic directly inside callbacks.
- Keep callback schemas in `src/telegram/callbacks.py` aligned with the matching handler family in `router/public.py` or `router/admin.py`.
- Keep text-generation changes in the matching `src/telegram/texts/<family>.py` module and keyboard changes in the matching `src/telegram/ui/<family>.py` module.
- Add focused regression coverage close to the behavior you changed.

## Extra Docs
- `docs/codebase.md`: fuller architecture and package map.
- `src/README.md`: package-level navigation.
- `tests/README.md`: test inventory and where to add coverage.
