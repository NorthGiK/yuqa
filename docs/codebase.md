# Yuqa Codebase Map

## What This Repository Is
Yuqa is a Telegram game bot. The project mixes turn-based battles, card
collection, banners, clans, ideas, a shop, and battle pass systems behind one
bot-facing transport layer.

The codebase is organized around three main concerns:
- Domain rules in `src/<feature>/domain/`
- Telegram transport and presentation in `src/telegram/`
- Persistence adapters in `src/infrastructure/`

## Public Telegram Surfaces
The Telegram layer now exposes stable package-root surfaces that stay import
friendly even as the implementation is split into directories:

- `src.telegram.router`:
  package surface at `src/telegram/router/__init__.py`,
  implementation entry at `src/telegram/router/router.py`
- `src.telegram.services`:
  package surface at `src/telegram/services/__init__.py`,
  implementation entry at `src/telegram/services/services.py`
- `src.telegram.texts`:
  package surface at `src/telegram/texts/__init__.py`,
  aggregated implementation at `src/telegram/texts/texts.py`
- `src.telegram.ui`:
  package surface at `src/telegram/ui/__init__.py`,
  aggregated implementation at `src/telegram/ui/ui.py`

Use those package roots for imports. Edit the implementation modules inside the
matching directory when behavior changes.

## Runtime Flow
1. `main.py`
   Thin launcher that calls the package entrypoint.
2. `src/main.py`
   Loads settings, optionally runs migrations, builds `TelegramServices`,
   starts polling, and shuts services down cleanly.
3. `src/telegram/config.py`
   Parses environment variables into `Settings`.
4. `src/telegram/services/__init__.py`
   Stable import surface for service orchestration.
5. `src/telegram/services/services.py`
   Builds repositories, selects storage mode, and exposes shared application
   helpers.
6. `src/telegram/services/contracts.py`
   Describes the typed attributes and helper methods that feature mixins expect
   from `TelegramServices`.
7. `src/telegram/services/battles.py`
   Owns battle drafting, round resolution, and matchmaking flows.
8. `src/telegram/services/battle_pass.py`
   Owns battle pass seasons, levels, and progress purchase flows.
9. `src/telegram/services/players.py`
   Owns player lookup, profile, free rewards, and deck construction flows.
10. `src/telegram/services/social.py`
   Owns clan and idea flows.
11. `src/telegram/services/content.py`
   Owns cards, banners, shop items, starter cards, and admin content flows.
12. `src/telegram/services/quests.py`
   Owns cooldown-aware quest completion for player actions.
13. `src/telegram/router/__init__.py`
   Stable router import surface.
14. `src/telegram/router/router.py`
   Thin compatibility builder that assembles the router from public/admin
   registration modules.
15. `src/telegram/router/public.py`
   Registers public commands, callbacks, and player-facing wizard entry points.
16. `src/telegram/router/admin.py`
   Registers admin commands, callbacks, and admin-only state handlers.
17. `src/telegram/router/wizards_players.py`
   Owns clan, idea, profile, and admin-player wizard steps.
18. `src/telegram/router/wizards_progression.py`
   Owns battle pass and free-reward wizard steps.
19. `src/telegram/router/wizards_content.py`
   Thin compatibility facade for content-admin wizard families.
20. `src/telegram/router/wizards_cards.py`
   Owns universe, card, profile-background, and starter-card wizard steps.
21. `src/telegram/router/wizards_banners.py`
   Owns banner creation and banner-reward wizard steps.
22. `src/telegram/router/wizards_shop.py`
   Owns shop item wizard steps.
23. `src/telegram/router/battle.py`
   Owns battle queue entry and start helpers shared by public callbacks.
24. `src/telegram/router/views.py`
   Renders reusable screens such as profile, collection, battle, admin
   sections, and gallery pages.
25. `src/telegram/router/helpers.py`
   Holds pure parsing and pagination helpers shared by router flows.

## Package Map

### `src/application/`
- App-level abstractions such as unit-of-work style helpers.
- Should not depend on Telegram transport.

### `src/shared/`
- Shared enums, IDs, domain errors, and value objects.
- Intended to stay lightweight and reusable everywhere else.

### `src/<feature>/domain/`
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

### `src/telegram/`
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

### `src/infrastructure/`
- `local.py`: JSON-backed catalog persistence and shared serializers
- `sqlalchemy/`: SQLAlchemy models, repositories, serialization, migrations,
  and health checks

## Storage Model
The bot can run in three modes:

### Temporary SQLite
- Constructed with `TelegramServices()`
- Uses an isolated SQLite document store for tests and isolated service
  experiments

### Catalog / Local JSON
- Constructed with `TelegramServices(content_path=...)`
- Uses JSON-backed repositories for catalog-like content and temporary SQLite
  for runtime state

### Database
- Constructed with `TelegramServices(content_path=..., database_url=...)`
- Uses SQLAlchemy repositories and Alembic migrations
- Default `DATABASE_URL` falls back to SQLite inside `YUQA_DATA_DIR`
- Active battles and matchmaking queues are cleared on startup; deck drafts and
  finished player progress persist.
- Quest definitions and per-player quest cooldowns persist with runtime state.

## Where Logic Should Live

### Put logic in feature domain services when
- The rule is game logic rather than Telegram UX
- It should be reusable from more than one handler
- It belongs beside entities/repositories from a single feature

### Put logic in `router/views.py` when
- It is about rendering or re-rendering a screen
- It combines text, markup, and media preview behavior
- Multiple callbacks or handlers should reuse the same screen builder

### Put logic in `router/router.py`, `router/public.py`, or `router/admin.py` when
- It is about handler registration
- It is callback/message wiring rather than reusable rendering
- It decides which wizard or screen flow should run

### Put logic in `router/wizards_<family>.py`, `router/wizards_cards.py`, `router/wizards_banners.py`, `router/wizards_shop.py`, or `router/battle.py` when
- It is FSM input capture or step transitions
- It validates per-step user input before the next state
- It is a reusable wizard step invoked from more than one registration point

### Put logic in `infrastructure/` when
- It is storage-specific
- It is serialization or persistence shape adaptation
- The domain should not know about it

## Hotspots
- `src/telegram/services/services.py`
  Service container and remaining shared helper hotspot.
- `src/telegram/services/contracts.py`
  Type-only service contracts for mixin dependencies and IDE completion.
- `src/telegram/services/battles.py`
  Battle and matchmaking orchestration.
- `src/telegram/services/battle_pass.py`
  Battle pass orchestration.
- `src/telegram/services/players.py`
  Player profile, free reward, and deck orchestration.
- `src/telegram/services/content.py`
  Card, banner, shop, and starter-card orchestration.
- `src/telegram/services/quests.py`
  Cooldown-aware quest completion orchestration.
- `src/telegram/router/public.py`
  Public command and callback registration.
- `src/telegram/router/admin.py`
  Admin command and callback registration.
- `src/telegram/router/wizards_cards.py`
  Card/profile-background/starter-card wizard surface.
- `src/telegram/router/wizards_banners.py`
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
1. `src/main.py`
2. `src/telegram/config.py`
3. `src/telegram/services/__init__.py`
4. `src/telegram/services/services.py`
5. `src/telegram/services/contracts.py`

### If you are debugging a callback or command
1. `src/telegram/router/__init__.py`
2. `src/telegram/router/router.py`
3. `src/telegram/router/public.py` or `src/telegram/router/admin.py`
4. The matching `src/telegram/router/wizards_players.py`, `src/telegram/router/wizards_progression.py`, `src/telegram/router/wizards_cards.py`, `src/telegram/router/wizards_banners.py`, `src/telegram/router/wizards_shop.py`, or `src/telegram/router/battle.py`
5. `src/telegram/router/views.py`
6. `src/telegram/texts/__init__.py`
7. `src/telegram/texts/texts.py`
8. The matching `src/telegram/texts/<family>.py`
9. `src/telegram/ui/__init__.py`
10. `src/telegram/ui/ui.py`
11. The matching `src/telegram/ui/<family>.py`

### If you are debugging persistence
1. `src/infrastructure/sqlalchemy/repositories.py`
2. `src/infrastructure/sqlalchemy/models.py`
3. `tests/test_persistence.py`

### If you are adding a feature rule
1. `src/<feature>/domain/entities.py`
2. `src/<feature>/domain/services.py`
3. The matching test file under `tests/`

### If you are wiring a quest action
1. `src/quests/domain/entities.py`
2. `src/quests/domain/services.py`
3. `src/telegram/services/quests.py`
4. The router that owns the player action
