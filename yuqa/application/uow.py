"""Unit of work protocol for application services."""

from typing import Protocol


class UnitOfWork(Protocol):
    """Async unit of work contract."""

    async def __aenter__(self):
        """Enter the transaction scope."""

    async def __aexit__(self, exc_type, exc, tb):
        """Leave the transaction scope."""

    async def commit(self) -> None:
        """Commit the transaction."""

    async def rollback(self) -> None:
        """Rollback the transaction."""
