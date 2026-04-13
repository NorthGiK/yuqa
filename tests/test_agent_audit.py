"""Tests for the agent-facing repository audit script."""

from scripts.agent_audit import build_summary, check_boundaries


def test_build_summary_includes_expected_entrypoints() -> None:
    summary = build_summary()

    assert "yuqa/main.py" in summary["entrypoints"]
    assert "yuqa/telegram/router.py" in summary["entrypoints"]
    assert summary["commands"]["agent_summary"] == "make agent-summary"


def test_build_summary_reports_known_feature() -> None:
    summary = build_summary()

    cards_feature = next(
        feature for feature in summary["features"] if feature["name"] == "cards"
    )

    assert "entities.py" in cards_feature["domain_modules"]
    assert "yuqa/cards/domain/entities.py" in cards_feature["files"]


def test_layer_boundaries_pass_for_current_repo() -> None:
    assert check_boundaries() == []
