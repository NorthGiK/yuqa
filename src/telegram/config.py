"""Runtime settings for the Telegram layer."""

from dataclasses import dataclass
import logging
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


def _parse_port(raw: str, *, name: str) -> int:
    """Parse a TCP port from the environment."""

    try:
        port = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer port") from error
    if not 1 <= port <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535")
    return port


def _parse_log_level(raw: str) -> str:
    """Parse a standard logging level from the environment."""

    value = (raw or "INFO").strip().upper()
    if value not in logging.getLevelNamesMapping():
        raise ValueError(f"invalid log level: '{raw}'")
    return value


def _parse_log_format(raw: str) -> str:
    """Parse the configured log output format."""

    value = (raw or "plain").strip().lower()
    if value not in {"plain", "json"}:
        raise ValueError("YUQA_LOG_FORMAT must be 'plain' or 'json'")
    return value


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
    log_level: str = "INFO"
    log_format: str = "plain"
    metrics_enabled: bool = False
    metrics_host: str = "127.0.0.1"
    metrics_port: int = 9000

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
            log_level=_parse_log_level(getenv("YUQA_LOG_LEVEL", "INFO")),
            log_format=_parse_log_format(getenv("YUQA_LOG_FORMAT", "plain")),
            metrics_enabled=_parse_bool(
                getenv("YUQA_METRICS_ENABLED", "false"),
                default=False,
            ),
            metrics_host=getenv("YUQA_METRICS_HOST", "127.0.0.1").strip()
            or "127.0.0.1",
            metrics_port=_parse_port(getenv("YUQA_METRICS_PORT", "9000"), name="YUQA_METRICS_PORT"),
        )
