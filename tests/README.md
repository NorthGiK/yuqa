# Test Guide

## Purpose
Tests are organized by behavior rather than by package mirroring. Use the file whose scope is closest to the change you are making.

## Domain Tests
- `test_cards.py`
- `test_clans.py`
- `test_shop.py`
- `test_banners.py`
- `test_battle_engine.py`
- `test_quests_battlepass.py`

## Telegram and UX Tests
- `test_telegram_layer.py`
- `test_telegram_services.py`
- `test_router_wiring.py`
- `test_reply.py`
- `test_telegram_config.py`
- `test_admin_content.py`

## Persistence Tests
- `test_persistence.py`

## Tooling Tests
- `test_agent_audit.py`

## Focused Loops
- `make test-file FILE=tests/test_telegram_layer.py`
- `make test-file FILE=tests/test_telegram_services.py`
- `make test-file FILE=tests/test_persistence.py`

## Coverage Heuristic
For each behavior change, add:
- A happy-path assertion
- At least one validation or error-path assertion
- A regression assertion for the exact bug or edge case being fixed
