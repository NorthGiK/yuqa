# Yuqa Codebase Map

## What This Repository Is
Yuqa is a Telegram game bot. The project mixes turn-based battles, card
collection, banners, clans, ideas, a shop, and battle pass systems behind one
bot-facing transport layer.

The codebase is organized around three main concerns:
- Domain rules in `yuqa/<feature>/domain/`
- Telegram transport and presentation in `yuqa/telegram/`
- Persistence adapters in `yuqa/infrastructure/`

## Public Telegram Surfaces
The Telegram layer now exposes stable package-root surfaces that stay import
friendly even as the implementation is split into directories:

- `yuqa.telegram.router`:
  package surface at `yuqa/telegram/router/__init__.py`,
  implementation entry at `yuqa/telegram/router/router.py`
- `yuqa.telegram.services`:
  package surface at `yuqa/telegram/services/__init__.py`,
  implementation entry at `yuqa/telegram/services/services.py`
- `yuqa.telegram.texts`:
  package surface at `yuqa/telegram/texts/__init__.py`,
  aggregated implementation at `yuqa/telegram/texts/texts.py`
- `yuqa.telegram.ui`:
  package surface at `yuqa/telegram/ui/__init__.py`,
  aggregated implementation at `yuqa/telegram/ui/ui.py`

Use those package roots for imports. Edit the implementation modules inside the
matching directory when behavior changes.

## Runtime Flow
1. `main.py`
   Thin launcher that calls the package entrypoint.
2. `yuqa/main.py`
   Loads settings, optionally runs migrations, builds `TelegramServices`,
   starts polling, and shuts services down cleanly.
3. `yuqa/telegram/config.py`
   Parses environment variables into `Settings`.
4. `yuqa/telegram/services/__init__.py`
   Stable import surface for service orchestration.
5. `yuqa/telegram/services/services.py`
   Builds repositories, selects storage mode, and exposes shared application
   helpers.
6. `yuqa/telegram/services/services_contracts.py`
   Describes the typed attributes and helper methods that feature mixins expect
   from `TelegramServices`.
7. `yuqa/telegram/services/services_battles.py`
   Owns battle drafting, round resolution, and matchmaking flows.
8. `yuqa/telegram/services/services_battle_pass.py`
   Owns battle pass seasons, levels, and progress purchase flows.
9. `yuqa/telegram/services/services_players.py`
   Owns player lookup, profile, free rewards, and deck construction flows.
10. `yuqa/telegram/services/services_social.py`
   Owns clan and idea flows.
11. `yuqa/telegram/services/services_content.py`
   Owns cards, banners, shop items, starter cards, and admin content flows.
12. `yuqa/telegram/router/__init__.py`
   Stable router import surface.
13. `yuqa/telegram/router/router.py`
   Thin compatibility builder that assembles the router from public/admin
   registration modules.
14. `yuqa/telegram/router/router_public.py`
   Registers public commands, callbacks, and player-facing wizard entry points.
15. `yuqa/telegram/router/router_admin.py`
   Registers admin commands, callbacks, and admin-only state handlers.
16. `yuqa/telegram/router/router_wizards_players.py`
   Owns clan, idea, profile, and admin-player wizard steps.
17. `yuqa/telegram/router/router_wizards_progression.py`
   Owns battle pass and free-reward wizard steps.
18. `yuqa/telegram/router/router_wizards_content.py`
   Thin compatibility facade for content-admin wizard families.
19. `yuqa/telegram/router/router_wizards_cards.py`
   Owns universe, card, profile-background, and starter-card wizard steps.
20. `yuqa/telegram/router/router_wizards_banners.py`
   Owns banner creation and banner-reward wizard steps.
21. `yuqa/telegram/router/router_wizards_shop.py`
   Owns shop item wizard steps.
22. `yuqa/telegram/router/router_battle.py`
   Owns battle queue entry and start helpers shared by public callbacks.
23. `yuqa/telegram/router/router_views.py`
   Renders reusable screens such as profile, collection, battle, admin
   sections, and gallery pages.
24. `yuqa/telegram/router/router_helpers.py`
   Holds pure parsing and pagination helpers shared by router flows.

## Package Map

### `yuqa/application/`
- App-level abstractions such as unit-of-work style helpers.
- Should not depend on Telegram transport.

### `yuqa/shared/`
- Shared enums, IDs, domain errors, and value objects.
- Intended to stay lightweight and reusable everywhere else.

### `yuqa/<feature>/domain/`
Each feature package follows roughly the same split:
- `entities.py`: dataclasses and behavior-bearing models
- `repositories.py`: repository protocols or lightweight repository shapes
- `services.py`: domain use cases and rule orchestration

Current feature packages:
- `banners`
- `battle_pass`
- `battles`
- `cards`
- `clans`
- `ideas`
- `players`
- `quests`
- `shop`

### `yuqa/telegram/`
- `bot.py`: dispatcher/bot construction
- `callbacks.py`: callback payload schemas
- `compat.py`: aiogram compatibility shims and test doubles
- `config.py`: env parsing
- `reply.py`: safe send/edit helpers
- `router/`: router builder, handler registration, wizard steps, reusable
  router views, and helper functions
- `services/`: storage selection, typed mixin contracts, orchestration mixins,
  and shared service helpers
- `states.py`: FSM state groups
- `texts/`: package root plus family-specific copy modules
- `ui/`: package root plus family-specific markup modules

### `yuqa/infrastructure/`
- `memory.py`: in-memory repositories for tests and fast local flows
- `local.py`: JSON-backed catalog/runtime persistence
- `sqlalchemy/`: SQLAlchemy models, repositories, serialization, migrations,
  and health checks

## Storage Model
The bot can run in three modes:

### Memory
- Constructed with `TelegramServices()`
- Best for tests and isolated service experiments

### Catalog / Local JSON
- Constructed with `TelegramServices(content_path=...)`
- Uses JSON-backed repositories for catalog-like content

### Database
- Constructed with `TelegramServices(content_path=..., database_url=...)`
- Uses SQLAlchemy repositories and Alembic migrations
- Default `DATABASE_URL` falls back to SQLite inside `YUQA_DATA_DIR`
- Active battles and matchmaking queues are cleared on startup; deck drafts and
  finished player progress persist.

## Where Logic Should Live

### Put logic in feature domain services when
- The rule is game logic rather than Telegram UX
- It should be reusable from more than one handler
- It belongs beside entities/repositories from a single feature

### Put logic in `router/router_views.py` when
- It is about rendering or re-rendering a screen
- It combines text, markup, and media preview behavior
- Multiple callbacks or handlers should reuse the same screen builder

### Put logic in `router/router.py`, `router/router_public.py`, or `router/router_admin.py` when
- It is about handler registration
- It is callback/message wiring rather than reusable rendering
- It decides which wizard or screen flow should run

### Put logic in `router/router_wizards_<family>.py`, `router/router_wizards_cards.py`, `router/router_wizards_banners.py`, `router/router_wizards_shop.py`, or `router/router_battle.py` when
- It is FSM input capture or step transitions
- It validates per-step user input before the next state
- It is a reusable wizard step invoked from more than one registration point

### Put logic in `infrastructure/` when
- It is storage-specific
- It is serialization or persistence shape adaptation
- The domain should not know about it

## Hotspots
- `yuqa/telegram/services/services.py`
  Service container and remaining shared helper hotspot.
- `yuqa/telegram/services/services_contracts.py`
  Type-only service contracts for mixin dependencies and IDE completion.
- `yuqa/telegram/services/services_battles.py`
  Battle and matchmaking orchestration.
- `yuqa/telegram/services/services_battle_pass.py`
  Battle pass orchestration.
- `yuqa/telegram/services/services_players.py`
  Player profile, free reward, and deck orchestration.
- `yuqa/telegram/services/services_content.py`
  Card, banner, shop, and starter-card orchestration.
- `yuqa/telegram/router/router_public.py`
  Public command and callback registration.
- `yuqa/telegram/router/router_admin.py`
  Admin command and callback registration.
- `yuqa/telegram/router/router_wizards_cards.py`
  Card/profile-background/starter-card wizard surface.
- `yuqa/telegram/router/router_wizards_banners.py`
  Banner and reward wizard surface.

Use caution before making those files larger. Prefer new helper modules or
feature-level services when the change is cohesive enough.

## Test Inventory

### Domain
- `tests/test_cards.py`
- `tests/test_clans.py`
- `tests/test_ideas.py`
- `tests/test_shop.py`
- `tests/test_banners.py`
- `tests/test_battle_engine.py`
- `tests/test_quests_battlepass.py`
- `tests/test_shared.py`

### Telegram Transport and Presentation
- `tests/test_telegram_layer.py`
- `tests/test_telegram_services.py`
- `tests/test_router_wiring.py`
- `tests/test_reply.py`
- `tests/test_telegram_config.py`
- `tests/test_admin_content.py`

### Persistence
- `tests/test_persistence.py`

### Tooling
- `tests/test_agent_audit.py`

## Recommended First Reads

### If you are debugging startup
1. `yuqa/main.py`
2. `yuqa/telegram/config.py`
3. `yuqa/telegram/services/__init__.py`
4. `yuqa/telegram/services/services.py`
5. `yuqa/telegram/services/services_contracts.py`

### If you are debugging a callback or command
1. `yuqa/telegram/router/__init__.py`
2. `yuqa/telegram/router/router.py`
3. `yuqa/telegram/router/router_public.py` or `yuqa/telegram/router/router_admin.py`
4. The matching `yuqa/telegram/router/router_wizards_players.py`, `yuqa/telegram/router/router_wizards_progression.py`, `yuqa/telegram/router/router_wizards_cards.py`, `yuqa/telegram/router/router_wizards_banners.py`, `yuqa/telegram/router/router_wizards_shop.py`, or `yuqa/telegram/router/router_battle.py`
5. `yuqa/telegram/router/router_views.py`
6. `yuqa/telegram/texts/__init__.py`
7. `yuqa/telegram/texts/texts.py`
8. The matching `yuqa/telegram/texts/texts_<family>.py`
9. `yuqa/telegram/ui/__init__.py`
10. `yuqa/telegram/ui/ui.py`
11. The matching `yuqa/telegram/ui/ui_<family>.py`

### If you are debugging persistence
1. `yuqa/infrastructure/sqlalchemy/repositories.py`
2. `yuqa/infrastructure/sqlalchemy/models.py`
3. `tests/test_persistence.py`

### If you are adding a feature rule
1. `yuqa/<feature>/domain/entities.py`
2. `yuqa/<feature>/domain/services.py`
3. The matching test file under `tests/`
