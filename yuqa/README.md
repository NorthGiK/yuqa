# `yuqa/` Package Guide

## Purpose
This package contains the whole bot application: domain rules, Telegram transport, shared value objects, and persistence adapters.

## Top-Level Directories
- `application/`
  App-level abstractions that should stay transport-agnostic.
- `banners/`, `battle_pass/`, `battles/`, `cards/`, `clans/`, `ideas/`, `players/`, `quests/`, `shop/`
  Feature packages. Most work should happen inside each feature's `domain/`.
- `infrastructure/`
  Storage adapters for in-memory, local JSON, and SQLAlchemy-backed persistence.
- `shared/`
  Common enums, IDs, errors, and value objects reused across features.
- `telegram/`
  Bot-facing transport, rendering, configuration, and orchestration.

## Telegram Split
- `telegram/router/__init__.py`
  Stable import surface for handler registration helpers.
- `telegram/router/router.py`
  Router builder and compatibility exports.
- `telegram/router/router_views.py`
  Reusable screens and admin section rendering.
- `telegram/router/router_helpers.py`
  Parsing, pagination, and message/media helper functions.
- `telegram/services/__init__.py`
  Stable import surface for the Telegram service container.
- `telegram/services/services.py`
  The main application service container and shared helper host.
- `telegram/services/services_contracts.py`
  Type-only contracts for service mixin attributes and helper methods.
- `telegram/services/services_battles.py`
  Battle drafting, round resolution, and matchmaking.
- `telegram/services/services_battle_pass.py`
  Battle pass season, level, and progress operations.
- `telegram/services/services_support.py`
  Small shared service dataclasses and helpers.
- `telegram/texts/__init__.py`
  Stable import surface for screen copy helpers.
- `telegram/texts/texts.py`
  Re-exports the family-specific text modules.
- `telegram/ui/__init__.py`
  Stable import surface for keyboards and inline markup.
- `telegram/ui/ui.py`
  Re-exports the family-specific UI modules.

## Rule of Thumb
- Feature behavior belongs in `yuqa/<feature>/domain/`.
- Telegram-only interaction flow belongs in `yuqa/telegram/`.
- Persistence details belong in `yuqa/infrastructure/`.
