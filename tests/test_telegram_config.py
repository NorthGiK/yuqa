"""Tests for Telegram runtime settings parsing."""

from pathlib import Path

import pytest

from src.telegram.config import Settings


def test_settings_from_env_reads_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Settings should parse token, admins, and content path from env vars."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "1, 2,3")
    monkeypatch.setenv("YUQA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("YUQA_AUTO_MIGRATE", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings.from_env()

    assert settings.token == "token-123"
    assert settings.admin_ids == {1, 2, 3}
    assert settings.content_dir == tmp_path
    assert (
        settings.database_url
        == f"sqlite:///{(tmp_path / 'yuqa.db').resolve().as_posix()}"
    )
    assert settings.auto_migrate is False
    assert settings.log_level == "INFO"
    assert settings.log_format == "plain"
    assert settings.metrics_enabled is False
    assert settings.metrics_host == "127.0.0.1"
    assert settings.metrics_port == 9000


def test_settings_from_env_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """BOT_TOKEN must be present."""

    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_IDS", "")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="BOT_TOKEN is required"):
        Settings.from_env()


def test_settings_from_env_validates_admin_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADMIN_IDS should only contain integers."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "1,nope")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="ADMIN_IDS"):
        Settings.from_env()


def test_settings_from_env_accepts_custom_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DATABASE_URL should override the default SQLite path."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/yuqa-test.db")

    settings = Settings.from_env()

    assert settings.database_url == "sqlite:////tmp/yuqa-test.db"


def test_settings_from_env_reads_logging_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logging settings should be explicit and deployment-friendly."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "")
    monkeypatch.setenv("YUQA_LOG_LEVEL", "debug")
    monkeypatch.setenv("YUQA_LOG_FORMAT", "json")

    settings = Settings.from_env()

    assert settings.log_level == "DEBUG"
    assert settings.log_format == "json"


def test_settings_from_env_validates_logging_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid logging settings should fail before the bot starts."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "")
    monkeypatch.setenv("YUQA_LOG_LEVEL", "verbose")

    with pytest.raises(ValueError, match="invalid log level"):
        Settings.from_env()

    monkeypatch.setenv("YUQA_LOG_LEVEL", "INFO")
    monkeypatch.setenv("YUQA_LOG_FORMAT", "xml")

    with pytest.raises(ValueError, match="YUQA_LOG_FORMAT"):
        Settings.from_env()


def test_settings_from_env_reads_metrics_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prometheus metrics endpoint settings should be deployment configurable."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "")
    monkeypatch.setenv("YUQA_METRICS_ENABLED", "true")
    monkeypatch.setenv("YUQA_METRICS_HOST", "0.0.0.0")
    monkeypatch.setenv("YUQA_METRICS_PORT", "9100")

    settings = Settings.from_env()

    assert settings.metrics_enabled is True
    assert settings.metrics_host == "0.0.0.0"
    assert settings.metrics_port == 9100


def test_settings_from_env_validates_metrics_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid metrics ports should fail before runtime binding."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "")
    monkeypatch.setenv("YUQA_METRICS_PORT", "70000")

    with pytest.raises(ValueError, match="YUQA_METRICS_PORT"):
        Settings.from_env()
