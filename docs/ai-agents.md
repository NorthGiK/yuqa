# AI Agent Guide

## One-Minute Read
1. Run `make agent-summary`.
2. Read `AGENTS.md`.
3. Use the stable package roots for imports:
   `yuqa.telegram.router`, `yuqa.telegram.services`,
   `yuqa.telegram.texts`, `yuqa.telegram.ui`.
4. Edit the implementation modules inside those directories when behavior
   changes.

## Public Surfaces
- `yuqa.telegram.router`:
  import-stable router API backed by `yuqa/telegram/router/__init__.py` and
  implemented in `yuqa/telegram/router/router.py`.
- `yuqa.telegram.services`:
  import-stable service container API backed by
  `yuqa/telegram/services/__init__.py` and implemented in
  `yuqa/telegram/services/services.py`.
- `yuqa.telegram.texts`:
  import-stable text renderer API backed by `yuqa/telegram/texts/__init__.py`
  and aggregated in `yuqa/telegram/texts/texts.py`.
- `yuqa.telegram.ui`:
  import-stable markup API backed by `yuqa/telegram/ui/__init__.py` and
  aggregated in `yuqa/telegram/ui/ui.py`.

## Codebase Shape
- `main.py` is only a launcher.
- `yuqa/main.py` is the runtime bootstrap.
- `yuqa/telegram/services/services.py` is the service container and storage selector.
- `yuqa/telegram/services/services_contracts.py` defines type-only mixin contracts for IDE completion.
- `yuqa/telegram/services/services_battles.py` owns battle drafting, round resolution, and matchmaking.
- `yuqa/telegram/services/services_battle_pass.py` owns battle pass seasons, levels, and progress.
- `yuqa/telegram/services/services_players.py` owns player lookup, profiles, free rewards, and deck construction.
- `yuqa/telegram/services/services_social.py` owns clans and ideas.
- `yuqa/telegram/services/services_content.py` owns cards, banners, shop items, starter cards, and content-admin flows.
- `yuqa/telegram/services/services_support.py` holds small shared service helpers.
- `yuqa/telegram/router/router.py` assembles the router from the public/admin handler modules.
- `yuqa/telegram/router/router_public.py` owns public command and callback registration.
- `yuqa/telegram/router/router_admin.py` owns admin command and callback registration.
- `yuqa/telegram/router/router_wizards_players.py` owns clan, idea, profile, and admin-player wizard steps.
- `yuqa/telegram/router/router_wizards_progression.py` owns battle pass and free-reward wizard steps.
- `yuqa/telegram/router/router_wizards_content.py` is the compatibility facade for content-admin wizard families.
- `yuqa/telegram/router/router_wizards_cards.py` owns universe, card, profile-background, and starter-card wizard steps.
- `yuqa/telegram/router/router_wizards_banners.py` owns banner creation and banner-reward wizard steps.
- `yuqa/telegram/router/router_wizards_shop.py` owns shop item wizard steps.
- `yuqa/telegram/router/router_battle.py` owns battle entry and queue helpers shared by public callbacks.
- `yuqa/telegram/router/router_views.py` owns reusable screens and admin section rendering.
- `yuqa/telegram/router/router_helpers.py` owns parsing, pagination, and media extraction.
- `yuqa/telegram/texts/texts.py` re-exports the family text modules.
- `yuqa/telegram/ui/ui.py` re-exports the family UI modules.

## Stable Boundaries
- Domain packages in `yuqa/<feature>/domain/` must not import Telegram or infrastructure.
- `yuqa/telegram/` is allowed to depend on domain and shared code.
- `yuqa/infrastructure/` adapts storage and serialization only.
- `yuqa/shared/` should stay dependency-light.
- `yuqa/application/` must remain transport-agnostic.

## Storage Modes
- `TelegramServices()`:
  fastest path for tests and isolated logic work.
- `TelegramServices(content_path=...)`:
  JSON-backed catalog/runtime storage without SQLAlchemy.
- `TelegramServices(content_path=..., database_url=...)`:
  persistent database-backed runtime with Alembic migrations.

## Task Playbooks

### Runtime Bug
Open these files in order:
1. `yuqa/main.py`
2. `yuqa/telegram/services/__init__.py`
3. `yuqa/telegram/services/services.py`
4. `yuqa/telegram/services/services_contracts.py`
5. `yuqa/telegram/services/services_battles.py`
6. `yuqa/telegram/services/services_battle_pass.py`
7. `yuqa/telegram/services/services_players.py`
8. `yuqa/telegram/services/services_content.py`
9. `yuqa/telegram/router/__init__.py`
10. `yuqa/telegram/router/router.py`
11. `yuqa/telegram/router/router_public.py`
12. `yuqa/telegram/router/router_admin.py`
13. `yuqa/telegram/router/router_views.py`

### New Domain Rule
Open:
1. `yuqa/<feature>/domain/entities.py`
2. `yuqa/<feature>/domain/services.py`
3. `yuqa/<feature>/domain/repositories.py`
4. The matching test file in `tests/`

### Telegram UI or Copy Change
Open:
1. `yuqa/telegram/router/router_views.py`
2. `yuqa/telegram/texts/__init__.py`
3. `yuqa/telegram/texts/texts.py`
4. The matching `yuqa/telegram/texts/texts_<family>.py`
5. `yuqa/telegram/ui/__init__.py`
6. `yuqa/telegram/ui/ui.py`
7. The matching `yuqa/telegram/ui/ui_<family>.py`
8. `tests/test_telegram_layer.py`

### Wizard or Handler Flow Change
Open:
1. `yuqa/telegram/router/router.py`
2. `yuqa/telegram/router/router_public.py` or `yuqa/telegram/router/router_admin.py`
3. The matching `yuqa/telegram/router/router_wizards_players.py`, `yuqa/telegram/router/router_wizards_progression.py`, `yuqa/telegram/router/router_wizards_cards.py`, `yuqa/telegram/router/router_wizards_banners.py`, `yuqa/telegram/router/router_wizards_shop.py`, or `yuqa/telegram/router/router_battle.py`
4. `yuqa/telegram/states.py`
5. `tests/test_router_wiring.py`
6. `tests/test_telegram_services.py`

### Persistence Bug
Open:
1. `yuqa/infrastructure/sqlalchemy/repositories.py`
2. `yuqa/infrastructure/sqlalchemy/models.py`
3. `yuqa/infrastructure/local.py`
4. `tests/test_persistence.py`

## Hotspots
- `yuqa/telegram/services/services.py`
- `yuqa/telegram/services/services_contracts.py`
- `yuqa/telegram/services/services_battles.py`
- `yuqa/telegram/services/services_battle_pass.py`
- `yuqa/telegram/services/services_players.py`
- `yuqa/telegram/services/services_content.py`
- `yuqa/telegram/router/router_public.py`
- `yuqa/telegram/router/router_admin.py`
- `yuqa/telegram/router/router_wizards_cards.py`
- `yuqa/telegram/router/router_wizards_banners.py`

Before expanding those files, confirm the logic cannot live in:
- A feature `domain/services.py`
- `router/router_views.py`
- `router/router_helpers.py`
- `router/router_wizards_players.py`, `router/router_wizards_progression.py`, `router/router_wizards_cards.py`, `router/router_wizards_banners.py`, `router/router_wizards_shop.py`, or `router/router_battle.py`
- `texts/texts_<family>.py` or `ui/ui_<family>.py`
- A storage adapter in `yuqa/infrastructure/`

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
- Prefer changing `router/router_views.py` over adding rendering logic directly inside callbacks.
- Keep callback schemas in `yuqa/telegram/callbacks.py` aligned with the matching handler family in `router/router_public.py` or `router/router_admin.py`.
- Keep text-generation changes in the matching `yuqa/telegram/texts/texts_<family>.py` module and keyboard changes in the matching `yuqa/telegram/ui/ui_<family>.py` module.
- Add focused regression coverage close to the behavior you changed.

## Extra Docs
- `docs/codebase.md`: fuller architecture and package map.
- `yuqa/README.md`: package-level navigation.
- `tests/README.md`: test inventory and where to add coverage.
