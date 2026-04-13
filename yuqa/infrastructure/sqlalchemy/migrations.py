"""Helpers for running Alembic migrations programmatically."""

from pathlib import Path

from alembic import command
from alembic.config import Config


def _project_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[3]


def alembic_config(database_url: str) -> Config:
    """Build an Alembic config pinned to the current repository."""

    root = _project_root()
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        if db_path.name:
            db_path.parent.mkdir(parents=True, exist_ok=True)
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_head(database_url: str) -> None:
    """Apply every pending migration."""

    command.upgrade(alembic_config(database_url), "head")
