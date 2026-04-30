"""Helpers for running Alembic migrations programmatically."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from yuqa.infrastructure.sqlalchemy.urls import ensure_sqlite_parent, sync_database_url


def _project_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[3]


def alembic_config(database_url: str) -> Config:
    """Build an Alembic config pinned to the current repository."""

    root = _project_root()
    sync_url = sync_database_url(database_url)
    ensure_sqlite_parent(sync_url)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", sync_url)
    return config


def upgrade_head(database_url: str) -> None:
    """Apply every pending migration."""

    command.upgrade(alembic_config(database_url), "head")
