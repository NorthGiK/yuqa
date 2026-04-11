"""SQLAlchemy models used by the persistent document store."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from yuqa.infrastructure.sqlalchemy.base import Base


def _now() -> datetime:
    """Return a timezone-aware timestamp for new rows."""

    return datetime.now(timezone.utc)


class StateDocumentORM(Base):
    """Named JSON document persisted in the relational database."""

    __tablename__ = "state_documents"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
