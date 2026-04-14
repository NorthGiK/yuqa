"""Container healthcheck entrypoint."""

from os import getenv
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

from yuqa.infrastructure.sqlalchemy.repositories import create_sync_engine


load_dotenv()


def _default_database_url() -> str:
    """Return the same default database URL as runtime settings."""

    data_dir = Path(getenv("YUQA_DATA_DIR", "data/yuqa")).expanduser().resolve()
    return f"sqlite:///{(data_dir / 'yuqa.db').as_posix()}"


def main() -> int:
    """Check that the database is reachable and the document table exists."""

    database_url = getenv("DATABASE_URL", "").strip() or _default_database_url()
    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(
                text("SELECT 1 FROM state_documents LIMIT 1")
            ).scalar_one_or_none()
    except SQLAlchemyError:
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
