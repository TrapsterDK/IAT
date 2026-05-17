"""SQLAlchemy bootstrap helpers for the backend SQLite database."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from apps.backend import database_schema  # noqa: F401
from apps.backend.database_base import Base

if TYPE_CHECKING:
    from pathlib import Path
    from sqlite3 import Connection as SQLiteConnection


def create_sqlite_engine(database_path: Path) -> Engine:
    """Create one configured SQLite SQLAlchemy engine.

    Args:
        database_path: Absolute filesystem path for the SQLite file.

    Returns:
        The configured SQLAlchemy engine.
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite_connection(dbapi_connection: SQLiteConnection, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create one synchronous SQLAlchemy session factory.

    Args:
        engine: Configured database engine.

    Returns:
        The configured SQLAlchemy sessionmaker.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_database_schema(engine: Engine) -> None:
    """Create all configured backend database tables.

    Args:
        engine: Configured database engine.
    """
    Base.metadata.create_all(engine)
