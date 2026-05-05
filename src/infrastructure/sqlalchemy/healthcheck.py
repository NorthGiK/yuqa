"""Container healthcheck entrypoint."""

from dataclasses import dataclass
import json
from os import getenv
from pathlib import Path
from typing import Any

from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.sqlalchemy.migrations import alembic_config
from src.infrastructure.sqlalchemy.repositories import create_sync_engine
from src.infrastructure.sqlalchemy.urls import database_driver, safe_database_url


load_dotenv()


@dataclass(frozen=True, slots=True)
class HealthcheckResult:
    """Database readiness result for container health checks."""

    healthy: bool
    status: str
    database_driver: str
    database_url: str
    expected_revision: str | None = None
    current_revision: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        return {
            "healthy": self.healthy,
            "status": self.status,
            "database_driver": self.database_driver,
            "database_url": self.database_url,
            "expected_revision": self.expected_revision,
            "current_revision": self.current_revision,
            "error": self.error,
        }


def _default_database_url() -> str:
    """Return the same default database URL as runtime settings."""

    data_dir = Path(getenv("YUQA_DATA_DIR", "data/yuqa")).expanduser().resolve()
    return f"sqlite:///{(data_dir / 'yuqa.db').as_posix()}"


def check_database(database_url: str) -> HealthcheckResult:
    """Check database reachability and Alembic schema revision."""

    try:
        expected_revision = ScriptDirectory.from_config(
            alembic_config(database_url)
        ).get_current_head()
        driver = database_driver(database_url)
        safe_url = safe_database_url(database_url)
    except Exception as error:
        return HealthcheckResult(
            healthy=False,
            status="configuration_error",
            database_driver="unknown",
            database_url="<invalid>",
            error=str(error),
        )

    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT 1 FROM players LIMIT 1")).scalar_one_or_none()
            current_revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
    except SQLAlchemyError as error:
        return HealthcheckResult(
            healthy=False,
            status="database_unavailable",
            database_driver=driver,
            database_url=safe_url,
            expected_revision=expected_revision,
            error=str(error),
        )
    finally:
        engine.dispose()

    if current_revision != expected_revision:
        return HealthcheckResult(
            healthy=False,
            status="migration_mismatch",
            database_driver=driver,
            database_url=safe_url,
            expected_revision=expected_revision,
            current_revision=current_revision,
        )
    return HealthcheckResult(
        healthy=True,
        status="ok",
        database_driver=driver,
        database_url=safe_url,
        expected_revision=expected_revision,
        current_revision=current_revision,
    )


def main() -> int:
    """Run the healthcheck and print a machine-readable result."""

    database_url = getenv("DATABASE_URL", "").strip() or _default_database_url()
    result = check_database(database_url)
    print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
