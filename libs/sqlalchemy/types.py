"""Custom SQLAlchemy column types shared across the repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    """Persist datetimes in UTC and always return timezone-aware UTC values."""

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        """Initialize one UTC-aware datetime SQLAlchemy type."""
        super().__init__(timezone=True)

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:  # noqa: ARG002
        """Normalize one bound datetime to UTC before persistence.

        Args:
            value: Datetime value being persisted.
            dialect: SQLAlchemy dialect performing the bind.

        Returns:
            The normalized UTC datetime value.
        """
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:  # noqa: ARG002
        """Normalize one loaded datetime to one timezone-aware UTC value.

        Args:
            value: Datetime value loaded from the database.
            dialect: SQLAlchemy dialect performing the load.

        Returns:
            The normalized timezone-aware UTC datetime value.
        """
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)
