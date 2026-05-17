"""Import backend ORM models so SQLAlchemy metadata is fully registered."""

from __future__ import annotations

from apps.backend.repositories.session.schema import SessionRecord, SessionTrialEventRecord

__all__ = ["SessionRecord", "SessionTrialEventRecord"]
