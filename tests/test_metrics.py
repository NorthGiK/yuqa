"""Tests for Prometheus metrics rendering."""

from src.shared.metrics import render_metrics


def test_render_metrics_exports_core_runtime_metrics() -> None:
    """Metrics output should be scrapeable by Prometheus."""

    payload = render_metrics(uptime_seconds=12.3456)

    assert "# TYPE yuqa_app_up gauge" in payload
    assert "yuqa_app_up 1" in payload
    assert "# TYPE yuqa_app_uptime_seconds gauge" in payload
    assert "yuqa_app_uptime_seconds 12.346" in payload
