"""Tests for backend database helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from apps.backend.database import create_database_schema, create_session_factory, create_sqlite_engine

if TYPE_CHECKING:
    from pathlib import Path


def test_create_sqlite_engine_creates_parent_directory_and_enables_foreign_keys(tmp_path: Path) -> None:
    # Given: one SQLite database path below one missing parent directory.
    database_path = tmp_path / "instance/backend.sqlite3"

    # When: the backend SQLite engine is created.
    engine = create_sqlite_engine(database_path)

    # Then: the parent directory exists and SQLite foreign keys are enabled on new connections.
    try:
        assert database_path.parent.is_dir()
        with engine.connect() as connection:
            pragma_value = connection.scalar(text("PRAGMA foreign_keys"))
        assert pragma_value == 1
    finally:
        engine.dispose()


def test_create_session_factory_disables_autoflush_and_expire_on_commit(tmp_path: Path) -> None:
    # Given: one configured backend SQLite engine.
    engine = create_sqlite_engine(tmp_path / "instance/backend.sqlite3")

    # When: the backend session factory is created.
    session_factory = create_session_factory(engine)

    # Then: the factory uses the configured SQLAlchemy session behavior.
    try:
        with session_factory() as database_session:
            assert database_session.autoflush is False
            assert database_session.expire_on_commit is False
    finally:
        engine.dispose()


def test_create_database_schema_registers_session_tables(tmp_path: Path) -> None:
    # Given: one configured backend SQLite engine with no schema yet.
    engine = create_sqlite_engine(tmp_path / "instance/backend.sqlite3")

    # When: the backend database schema is created.
    try:
        create_database_schema(engine)

        # Then: the expected session tables are created in SQLite.
        with engine.connect() as connection:
            table_names = {
                row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))
            }
        assert "iat_sessions" in table_names
        assert "iat_session_block_plans" in table_names
        assert "iat_session_trial_events" in table_names
    finally:
        engine.dispose()
