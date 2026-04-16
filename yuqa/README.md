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
- `telegram/router.py`
  Handler registration and FSM flows.
- `telegram/router_views.py`
  Reusable screens and admin section rendering.
- `telegram/router_helpers.py`
  Parsing, pagination, and message/media helper functions.
- `telegram/services.py`
  The main application service container and shared helper host.
- `telegram/services_battles.py`
  Battle drafting, round resolution, and matchmaking.
- `telegram/services_battle_pass.py`
  Battle pass season, level, and progress operations.
- `telegram/services_support.py`
  Small shared service dataclasses and helpers.
- `telegram/texts.py`
  Screen copy and text-formatting helpers.
- `telegram/ui.py`
  Keyboards and inline button markup.

## Rule of Thumb
- Feature behavior belongs in `yuqa/<feature>/domain/`.
- Telegram-only interaction flow belongs in `yuqa/telegram/`.
- Persistence details belong in `yuqa/infrastructure/`.
