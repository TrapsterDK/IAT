"""Tests for shared SQLAlchemy custom types."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select

from libs.sqlalchemy.types import UtcDateTime


def test_process_bind_param_normalizes_aware_datetime_to_utc() -> None:
    # Given: one UTC-aware SQLAlchemy datetime type and one non-UTC aware datetime.
    utc_datetime = UtcDateTime()
    source_value = datetime(2026, 1, 1, 10, 30, tzinfo=timezone(-timedelta(hours=5)))

    # When: the type prepares the datetime for persistence.
    bound_value = utc_datetime.process_bind_param(source_value, dialect=object())

    # Then: the persisted datetime is normalized to UTC.
    assert bound_value == datetime(2026, 1, 1, 15, 30, tzinfo=UTC)


def test_process_bind_param_attaches_utc_to_naive_datetime() -> None:
    # Given: one UTC-aware SQLAlchemy datetime type and one naive datetime.
    utc_datetime = UtcDateTime()
    source_value = datetime(2026, 1, 1, 15, 30)  # noqa: DTZ001

    # When: the type prepares the datetime for persistence.
    bound_value = utc_datetime.process_bind_param(source_value, dialect=object())

    # Then: the persisted datetime is treated as UTC.
    assert bound_value == datetime(2026, 1, 1, 15, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("source_value", "expected_value"),
    [
        pytest.param(None, None, id="none"),
        pytest.param(
            datetime(2026, 1, 1, 15, 30),  # noqa: DTZ001
            datetime(2026, 1, 1, 15, 30, tzinfo=UTC),
            id="naive",
        ),
        pytest.param(
            datetime(2026, 1, 1, 15, 30, tzinfo=timezone(-timedelta(hours=5))),
            datetime(2026, 1, 1, 20, 30, tzinfo=UTC),
            id="aware_non_utc",
        ),
    ],
)
def test_process_result_value_returns_aware_utc_datetime(
    source_value: datetime | None,
    expected_value: datetime | None,
) -> None:
    # Given: one UTC-aware SQLAlchemy datetime type and one database-loaded datetime value.
    utc_datetime = UtcDateTime()

    # When: the type converts the loaded value.
    result_value = utc_datetime.process_result_value(source_value, dialect=object())

    # Then: the returned datetime is always one timezone-aware UTC value.
    assert result_value == expected_value


def test_sqlite_round_trip_returns_aware_utc_datetime() -> None:
    # Given: one in-memory SQLite table using the shared UTC datetime type.
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    metadata = MetaData()
    test_table = Table(
        "events",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("received_at_utc", UtcDateTime(), nullable=False),
    )
    metadata.create_all(engine)
    source_value = datetime(2026, 1, 1, 10, 30, tzinfo=timezone(-timedelta(hours=5)))

    # When: SQLAlchemy persists and reloads one timestamp through SQLite.
    with engine.begin() as connection:
        connection.execute(test_table.insert().values(id=1, received_at_utc=source_value))
        loaded_value = connection.scalar(select(test_table.c.received_at_utc).where(test_table.c.id == 1))

    # Then: the round-tripped value remains timezone-aware UTC.
    assert loaded_value == datetime(2026, 1, 1, 15, 30, tzinfo=UTC)
