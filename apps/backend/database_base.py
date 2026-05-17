"""Shared SQLAlchemy declarative base for backend database models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for backend database models."""
