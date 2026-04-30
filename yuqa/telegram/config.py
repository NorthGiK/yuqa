"""Runtime settings for the Telegram layer."""

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _required_env(name: str) -> str:
    """Read a required environment variable."""

    value = getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _parse_admin_ids(raw: str) -> set[int]:
    """Parse comma-separated Telegram admin ids."""

    admin_ids: set[int] = set()
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            admin_ids.add(int(value))
        except ValueError as error:
            raise ValueError(
                f"ADMIN_IDS must be a comma-separated list of integers, got: '{value}'"
            ) from error
    return admin_ids


def _parse_bool(raw: str, *, default: bool) -> bool:
    """Parse a loose boolean value from the environment."""

    value = raw.strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: '{raw}'")


def _default_database_url(content_dir: Path) -> str:
    """Build the default SQLite URL inside the data directory."""

    db_path = (content_dir / "yuqa.db").expanduser().resolve()
    return f"sqlite:///{db_path.as_posix()}"


@dataclass(slots=True)
class Settings:
    """Process configuration loaded from environment variables."""

    token: str
    admin_ids: set[int]
    content_dir: Path
    database_url: str
    auto_migrate: bool

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from standard environment variables."""

        content_dir = Path(getenv("YUQA_DATA_DIR", "data/yuqa")).expanduser()
        return cls(
            token=_required_env("BOT_TOKEN"),
            admin_ids=_parse_admin_ids(getenv("ADMIN_IDS", "")),
            content_dir=content_dir,
            database_url=getenv("DATABASE_URL", "").strip()
            or _default_database_url(content_dir),
            auto_migrate=_parse_bool(getenv("YUQA_AUTO_MIGRATE", "true"), default=True),
        )
