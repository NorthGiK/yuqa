"""Tests for the agent-facing repository audit script."""

from pathlib import Path

from scripts.agent_audit import build_summary, check_boundaries
from yuqa.telegram import router, services, texts, ui


ROOT = Path(__file__).resolve().parents[1]


def test_build_summary_includes_expected_entrypoints() -> None:
    summary = build_summary()

    assert "yuqa/main.py" in summary["entrypoints"]
    assert "yuqa/telegram/router/__init__.py" in summary["entrypoints"]
    assert summary["commands"]["agent_summary"] == "make agent-summary"
    assert summary["recommended_start_points"]["telegram_views"] == (
        "yuqa/telegram/router/router_views.py"
    )
    assert summary["runtime_flow"][0]["path"] == "main.py"
    assert summary["module_groups"]["telegram_flow"] == [
        "yuqa/telegram/router/__init__.py",
        "yuqa/telegram/router/router.py",
        "yuqa/telegram/router/router_public.py",
        "yuqa/telegram/router/router_admin.py",
        "yuqa/telegram/states.py",
        "yuqa/telegram/callbacks.py",
    ]
    assert summary["module_groups"]["telegram_views"] == [
        "yuqa/telegram/router/router_views.py",
        "yuqa/telegram/texts/__init__.py",
        "yuqa/telegram/texts/texts.py",
        "yuqa/telegram/ui/__init__.py",
        "yuqa/telegram/ui/ui.py",
        "yuqa/telegram/reply.py",
    ]
    assert summary["module_groups"]["telegram_wizards"] == [
        "yuqa/telegram/router/router_wizards_players.py",
        "yuqa/telegram/router/router_wizards_progression.py",
        "yuqa/telegram/router/router_wizards_content.py",
        "yuqa/telegram/router/router_wizards_cards.py",
        "yuqa/telegram/router/router_wizards_banners.py",
        "yuqa/telegram/router/router_wizards_shop.py",
        "yuqa/telegram/router/router_battle.py",
    ]
    assert summary["module_groups"]["telegram_services"] == [
        "yuqa/telegram/services/__init__.py",
        "yuqa/telegram/services/services.py",
        "yuqa/telegram/services/services_contracts.py",
        "yuqa/telegram/services/services_battles.py",
        "yuqa/telegram/services/services_battle_pass.py",
        "yuqa/telegram/services/services_players.py",
        "yuqa/telegram/services/services_social.py",
        "yuqa/telegram/services/services_content.py",
        "yuqa/telegram/services/services_support.py",
    ]
    assert summary["recommended_start_points"]["battle_orchestration"] == (
        "yuqa/telegram/services/services_battles.py"
    )
    assert summary["recommended_start_points"]["service_contracts"] == (
        "yuqa/telegram/services/services_contracts.py"
    )
    assert summary["recommended_start_points"]["telegram_admin_handlers"] == (
        "yuqa/telegram/router/router_admin.py"
    )
    assert summary["recommended_start_points"]["content_admin_orchestration"] == (
        "yuqa/telegram/services/services_content.py"
    )
    assert summary["public_surfaces"]["router"]["implementation"] == (
        "yuqa/telegram/router/router.py"
    )
    assert summary["module_groups"]["telegram_texts"][-1] == (
        "yuqa/telegram/texts/texts_admin.py"
    )
    assert summary["module_groups"]["telegram_ui"][-1] == (
        "yuqa/telegram/ui/ui_admin.py"
    )


def test_build_summary_reports_known_feature() -> None:
    summary = build_summary()

    cards_feature = next(
        feature for feature in summary["features"] if feature["name"] == "cards"
    )

    assert "entities.py" in cards_feature["domain_modules"]
    assert "yuqa/cards/domain/entities.py" in cards_feature["files"]
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


def test_container_runtime_matches_application_entrypoint() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert 'DATABASE_URL=sqlite:////data/yuqa.db' in dockerfile
    assert 'CMD ["uv", "run", "yuqa"]' in dockerfile
    assert "image: ${YUQA_IMAGE:-yuqa:latest}" in compose
    assert "yuqa-data:/data" in compose
