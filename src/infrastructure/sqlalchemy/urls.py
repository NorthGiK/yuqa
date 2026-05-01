"""Database URL helpers for synchronous SQLAlchemy runtime paths."""

from pathlib import Path

from sqlalchemy.engine import make_url


ASYNC_DRIVER_SYNC_DRIVER = {
    "sqlite+aiosqlite": "sqlite",
    "postgresql+asyncpg": "postgresql+psycopg2",
}


def sync_database_url(database_url: str) -> str:
    """Return a database URL suitable for synchronous SQLAlchemy engines."""

    url = make_url(database_url)
    drivername = ASYNC_DRIVER_SYNC_DRIVER.get(url.drivername)
    if drivername is None:
        return database_url
    return str(url.set(drivername=drivername))


def ensure_sqlite_parent(database_url: str) -> None:
    """Create the parent directory for file-backed SQLite databases."""

    url = make_url(sync_database_url(database_url))
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        return
    db_path = Path(url.database)
    if db_path.name:
        db_path.parent.mkdir(parents=True, exist_ok=True)
