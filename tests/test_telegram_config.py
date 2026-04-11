"""Tests for Telegram runtime settings parsing."""

from pathlib import Path

import pytest

from yuqa.telegram.config import Settings


def test_settings_from_env_reads_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Settings should parse token, admins, and content path from env vars."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "1, 2,3")
    monkeypatch.setenv("YUQA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("YUQA_AUTO_MIGRATE", "false")

    settings = Settings.from_env()

    assert settings.token == "token-123"
    assert settings.admin_ids == {1, 2, 3}
    assert settings.content_dir == tmp_path
    assert settings.database_url == f"sqlite:///{(tmp_path / 'yuqa.db').resolve().as_posix()}"
    assert settings.auto_migrate is False


def test_settings_from_env_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """BOT_TOKEN must be present."""

    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_IDS", "")

    with pytest.raises(ValueError, match="BOT_TOKEN is required"):
        Settings.from_env()


def test_settings_from_env_validates_admin_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADMIN_IDS should only contain integers."""

    monkeypatch.setenv("BOT_TOKEN", "token-123")
    monkeypatch.setenv("ADMIN_IDS", "1,nope")

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
