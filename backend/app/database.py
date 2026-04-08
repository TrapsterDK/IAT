"""Database wiring and SQLAlchemy helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.engine import Engine

    from backend.app.config import Settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def create_db_session(app: FastAPI) -> Session:
    """Create a SQLAlchemy session for request-scoped use."""
    return app.state.session_factory()


def get_engine(app: FastAPI) -> Engine:
    """Return the SQLAlchemy engine stored on the FastAPI app."""
    return app.state.engine


def init_db(app: FastAPI, settings: Settings) -> None:
    """Initialise SQLAlchemy integration for the FastAPI app."""
    engine = create_engine(settings.DATABASE_URL, future=True)
    app_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.engine = engine
    app.state.session_factory = app_session_factory
    Base.metadata.create_all(bind=engine)
