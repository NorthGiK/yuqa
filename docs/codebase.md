# Yuqa Codebase Map

## What This Repository Is
Yuqa is a Telegram game bot. The project mixes turn-based battles, card collection, banners, clans, ideas, a shop, and battle pass systems behind one bot-facing transport layer.

The codebase is organized around three main concerns:
- Domain rules in `yuqa/<feature>/domain/`
- Telegram transport and presentation in `yuqa/telegram/`
- Persistence adapters in `yuqa/infrastructure/`

## Runtime Flow
1. `main.py`
   Thin launcher that calls the package entrypoint.
2. `yuqa/main.py`
   Loads settings, optionally runs migrations, builds `TelegramServices`, starts polling, and shuts services down cleanly.
3. `yuqa/telegram/config.py`
   Parses environment variables into `Settings`.
4. `yuqa/telegram/services.py`
   Builds repositories, selects storage mode, and exposes shared application helpers.
5. `yuqa/telegram/services_battles.py`
   Owns battle drafting, round resolution, and matchmaking flows.
6. `yuqa/telegram/services_battle_pass.py`
   Owns battle pass seasons, levels, and progress purchase flows.
7. `yuqa/telegram/services_players.py`
   Owns player lookup, profile, free rewards, and deck construction flows.
8. `yuqa/telegram/services_social.py`
   Owns clan and idea flows.
9. `yuqa/telegram/services_content.py`
   Owns cards, banners, shop items, starter cards, and admin content flows.
10. `yuqa/telegram/router.py`
   Thin compatibility builder that assembles the router from public/admin registration modules.
11. `yuqa/telegram/router_public.py`
   Registers public commands, callbacks, and player-facing wizard entry points.
12. `yuqa/telegram/router_admin.py`
   Registers admin commands, callbacks, and admin-only state handlers.
13. `yuqa/telegram/router_wizards_players.py`
   Owns clan, idea, profile, and admin-player wizard steps.
14. `yuqa/telegram/router_wizards_progression.py`
   Owns battle pass and free-reward wizard steps.
15. `yuqa/telegram/router_wizards_content.py`
   Thin compatibility facade for content-admin wizard families.
16. `yuqa/telegram/router_wizards_cards.py`
   Owns universe, card, profile-background, and starter-card wizard steps.
17. `yuqa/telegram/router_wizards_banners.py`
   Owns banner creation and banner-reward wizard steps.
18. `yuqa/telegram/router_wizards_shop.py`
   Owns shop item wizard steps.
19. `yuqa/telegram/router_battle.py`
   Owns battle queue entry and start helpers shared by public callbacks.
20. `yuqa/telegram/router_views.py`
   Renders reusable screens such as profile, collection, battle, admin sections, and gallery pages.
21. `yuqa/telegram/router_helpers.py`
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
- `router.py`: thin compatibility builder and import-stable facade
- `router_public.py`: public command/callback registration
- `router_admin.py`: admin command/callback registration
- `router_wizards_players.py`: player/clan/idea/admin-player wizard steps
- `router_wizards_progression.py`: battle pass and free-reward wizard steps
- `router_wizards_content.py`: compatibility facade for content-admin wizard steps
- `router_wizards_cards.py`: card/profile-background/universe/starter-card wizard steps
- `router_wizards_banners.py`: banner wizard steps
- `router_wizards_shop.py`: shop wizard steps
- `router_battle.py`: battle queue helpers
- `router_views.py`: reusable screens
- `router_helpers.py`: pure helper functions
- `services.py`: service container, storage selection, and shared helpers
- `services_battles.py`: battle and matchmaking orchestration
- `services_battle_pass.py`: battle pass orchestration
- `services_players.py`: player/profile/free-reward/deck orchestration
- `services_social.py`: clan and idea orchestration
- `services_content.py`: card/banner/shop/admin content orchestration
- `services_support.py`: shared service dataclasses and utility helpers
- `states.py`: FSM state groups
- `texts.py`: compatibility facade that re-exports `texts_<family>.py`
- `ui.py`: compatibility facade that re-exports `ui_<family>.py`

### `yuqa/infrastructure/`
- `memory.py`: in-memory repositories for tests and fast local flows
- `local.py`: JSON-backed catalog/runtime persistence
- `sqlalchemy/`: SQLAlchemy models, repositories, serialization, migrations, and health checks

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

## Where Logic Should Live

### Put logic in feature domain services when
- The rule is game logic rather than Telegram UX
- It should be reusable from more than one handler
- It belongs beside entities/repositories from a single feature

### Put logic in `router_views.py` when
- It is about rendering or re-rendering a screen
- It combines text, markup, and media preview behavior
- Multiple callbacks or handlers should reuse the same screen builder

### Put logic in `router_public.py` or `router_admin.py` when
- It is about handler registration
- It is callback/message wiring rather than reusable rendering
- It decides which wizard or screen flow should run

### Put logic in `router_wizards_<family>.py`, `router_wizards_cards.py`, `router_wizards_banners.py`, `router_wizards_shop.py`, or `router_battle.py` when
- It is FSM input capture or step transitions
- It validates per-step user input before the next state
- It is a reusable wizard step invoked from more than one registration point

### Put logic in `infrastructure/` when
- It is storage-specific
- It is serialization or persistence shape adaptation
- The domain should not know about it

## Hotspots
- `yuqa/telegram/services.py`
  Service container and remaining shared helper hotspot.
- `yuqa/telegram/services_battles.py`
  Battle and matchmaking orchestration.
- `yuqa/telegram/services_battle_pass.py`
  Battle pass orchestration.
- `yuqa/telegram/services_players.py`
  Player profile, free reward, and deck orchestration.
- `yuqa/telegram/services_content.py`
  Card, banner, shop, and starter-card orchestration.
- `yuqa/telegram/router_public.py`
  Public command and callback registration.
- `yuqa/telegram/router_admin.py`
  Admin command and callback registration.
- `yuqa/telegram/router_wizards_cards.py`
  Card/profile-background/starter-card wizard surface.
- `yuqa/telegram/router_wizards_banners.py`
  Banner and reward wizard surface.

Use caution before making those files larger. Prefer new helper modules or feature-level services when the change is cohesive enough.

## Test Inventory

### Domain
- `tests/test_cards.py`
- `tests/test_clans.py`
- `tests/test_ideas.py`
- `tests/test_shop.py`
- `tests/test_banners.py`
- `tests/test_battle_engine.py`
- `tests/test_quests_battlepass.py`

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
3. `yuqa/telegram/services.py`

### If you are debugging a callback or command
1. `yuqa/telegram/router.py`
2. `yuqa/telegram/router_public.py` or `yuqa/telegram/router_admin.py`
3. The matching `yuqa/telegram/router_wizards_players.py`, `yuqa/telegram/router_wizards_progression.py`, `yuqa/telegram/router_wizards_cards.py`, `yuqa/telegram/router_wizards_banners.py`, `yuqa/telegram/router_wizards_shop.py`, or `yuqa/telegram/router_battle.py`
4. `yuqa/telegram/router_views.py`
5. `yuqa/telegram/texts.py`
6. The matching `yuqa/telegram/texts_<family>.py`
7. `yuqa/telegram/ui.py`
8. The matching `yuqa/telegram/ui_<family>.py`

### If you are debugging persistence
1. `yuqa/infrastructure/sqlalchemy/repositories.py`
2. `yuqa/infrastructure/sqlalchemy/models.py`
3. `tests/test_persistence.py`

### If you are adding a feature rule
1. `yuqa/<feature>/domain/entities.py`
2. `yuqa/<feature>/domain/services.py`
3. The matching test file under `tests/`
