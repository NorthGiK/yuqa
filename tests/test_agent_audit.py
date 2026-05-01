"""Tests for the agent-facing repository audit script."""

from pathlib import Path

from scripts.agent_audit import build_summary, check_boundaries
from src.telegram import router, services, texts, ui


ROOT = Path(__file__).resolve().parents[1]


def test_build_summary_includes_expected_entrypoints() -> None:
    summary = build_summary()

    assert "src/main.py" in summary["entrypoints"]
    assert "src/telegram/router/__init__.py" in summary["entrypoints"]
    assert summary["commands"]["agent_summary"] == "make agent-summary"
    assert summary["recommended_start_points"]["telegram_views"] == (
        "src/telegram/router/views.py"
    )
    assert summary["runtime_flow"][0]["path"] == "main.py"
    assert summary["module_groups"]["telegram_flow"] == [
        "src/telegram/router/__init__.py",
        "src/telegram/router/router.py",
        "src/telegram/router/public.py",
        "src/telegram/router/admin.py",
        "src/telegram/states.py",
        "src/telegram/callbacks.py",
    ]
    assert summary["module_groups"]["telegram_views"] == [
        "src/telegram/router/views.py",
        "src/telegram/texts/__init__.py",
        "src/telegram/texts/texts.py",
        "src/telegram/ui/__init__.py",
        "src/telegram/ui/ui.py",
        "src/telegram/reply.py",
    ]
    assert summary["module_groups"]["telegram_wizards"] == [
        "src/telegram/router/wizards_players.py",
        "src/telegram/router/wizards_progression.py",
        "src/telegram/router/wizards_content.py",
        "src/telegram/router/wizards_cards.py",
        "src/telegram/router/wizards_banners.py",
        "src/telegram/router/wizards_shop.py",
        "src/telegram/router/battle.py",
    ]
    assert summary["module_groups"]["telegram_services"] == [
        "src/telegram/services/__init__.py",
        "src/telegram/services/services.py",
        "src/telegram/services/contracts.py",
        "src/telegram/services/battles.py",
        "src/telegram/services/battle_pass.py",
        "src/telegram/services/players.py",
        "src/telegram/services/social.py",
        "src/telegram/services/content.py",
        "src/telegram/services/quests.py",
        "src/telegram/services/support.py",
    ]
    assert summary["recommended_start_points"]["battle_orchestration"] == (
        "src/telegram/services/battles.py"
    )
    assert summary["recommended_start_points"]["service_contracts"] == (
        "src/telegram/services/contracts.py"
    )
    assert summary["recommended_start_points"]["telegram_admin_handlers"] == (
        "src/telegram/router/admin.py"
    )
    assert summary["recommended_start_points"]["content_admin_orchestration"] == (
        "src/telegram/services/content.py"
    )
    assert summary["recommended_start_points"]["quest_orchestration"] == (
        "src/telegram/services/quests.py"
    )
    assert summary["public_surfaces"]["router"]["implementation"] == (
        "src/telegram/router/router.py"
    )
    assert summary["module_groups"]["telegram_texts"][-1] == (
        "src/telegram/texts/admin.py"
    )
    assert summary["module_groups"]["telegram_ui"][-1] == (
        "src/telegram/ui/admin.py"
    )


def test_build_summary_reports_known_feature() -> None:
    summary = build_summary()

    cards_feature = next(
        feature for feature in summary["features"] if feature["name"] == "cards"
    )

    assert "entities.py" in cards_feature["domain_modules"]
    assert "src/cards/domain/entities.py" in cards_feature["files"]
    assert cards_feature["test_status"] == "direct"


def test_build_summary_maps_feature_tests_by_import_not_just_filename() -> None:
    summary = build_summary()

    battles_feature = next(
        feature for feature in summary["features"] if feature["name"] == "battles"
    )

    assert "tests/test_battle_engine.py" in battles_feature["tests"]
    assert "battles" not in summary["feature_test_gaps"]
    assert "ideas" not in summary["feature_test_gaps"]


def test_public_surfaces_remain_import_stable() -> None:
    assert callable(router.build_router)
    assert services.TelegramServices.__name__ == "TelegramServices"
    assert callable(texts.menu_text)
    assert callable(ui.main_menu_markup)


def test_layer_boundaries_pass_for_current_repo() -> None:
    assert check_boundaries() == []
