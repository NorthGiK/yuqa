"""Shared ORM helpers."""

from datetime import datetime, timezone


def _now() -> datetime:
    """Return a timezone-aware timestamp for new rows."""

    return datetime.now(timezone.utc)
