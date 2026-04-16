"""Tests for the agent-facing repository audit script."""

from scripts.agent_audit import build_summary, check_boundaries


def test_build_summary_includes_expected_entrypoints() -> None:
    summary = build_summary()

    assert "yuqa/main.py" in summary["entrypoints"]
    assert "yuqa/telegram/router.py" in summary["entrypoints"]
    assert summary["commands"]["agent_summary"] == "make agent-summary"
    assert summary["recommended_start_points"]["telegram_views"] == (
        "yuqa/telegram/router_views.py"
    )
    assert summary["runtime_flow"][0]["path"] == "main.py"
    assert summary["module_groups"]["telegram_views"] == [
        "yuqa/telegram/router_views.py",
        "yuqa/telegram/texts.py",
        "yuqa/telegram/ui.py",
        "yuqa/telegram/reply.py",
    ]
    assert summary["module_groups"]["telegram_services"] == [
        "yuqa/telegram/services.py",
        "yuqa/telegram/services_battles.py",
        "yuqa/telegram/services_battle_pass.py",
        "yuqa/telegram/services_players.py",
        "yuqa/telegram/services_social.py",
        "yuqa/telegram/services_content.py",
        "yuqa/telegram/services_support.py",
    ]
    assert summary["recommended_start_points"]["battle_orchestration"] == (
        "yuqa/telegram/services_battles.py"
    )
    assert summary["recommended_start_points"]["content_admin_orchestration"] == (
        "yuqa/telegram/services_content.py"
    )
    assert summary["module_groups"]["telegram_texts"][-1] == (
        "yuqa/telegram/texts_admin.py"
    )
    assert summary["module_groups"]["telegram_ui"][-1] == ("yuqa/telegram/ui_admin.py")


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


def test_layer_boundaries_pass_for_current_repo() -> None:
    assert check_boundaries() == []
