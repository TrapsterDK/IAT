"""Shared FastAPI dependencies for the backend API."""

from __future__ import annotations

from dataclasses import dataclass
from secrets import randbelow, token_urlsafe
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session  # noqa: TC002

from apps.backend.repositories.session.plan import SessionPlanRepository
from apps.backend.repositories.session.scoring import SessionScoringRepository
from apps.backend.repositories.session.session import SessionRepository
from apps.backend.services.session import SessionService

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from sqlalchemy.orm import sessionmaker

    from apps.backend.repositories.catalog import CatalogRepository
    from apps.backend.services.catalog import CatalogService
    from apps.backend.settings import ResolvedIatResources


@dataclass(slots=True)
class BackendRuntime:
    """Application runtime dependencies stored on FastAPI application state."""

    catalog_repository: CatalogRepository
    catalog_service: CatalogService
    frontend_dist_directory: Path
    session_factory: sessionmaker[Session]
    settings: ResolvedIatResources


def get_runtime(request: Request) -> BackendRuntime:
    """Return the configured backend runtime dependencies from application state.

    Args:
        request: Current request used to access application state.

    Returns:
        The configured backend runtime dependencies.

    Raises:
        RuntimeError: Backend application runtime dependencies have not been configured.
        TypeError: The configured backend runtime dependencies have one unexpected type.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise RuntimeError("Backend runtime dependencies are not configured.")

    if not isinstance(runtime, BackendRuntime):
        raise TypeError("Backend runtime dependencies have one unexpected type.")

    return runtime


def get_catalog_service(request: Request) -> CatalogService:
    """Return the configured backend catalog service from application state.

    Args:
        request: Current request used to access application state.

    Returns:
        The configured backend catalog service.

    Raises:
        RuntimeError: Backend application runtime dependencies have not been configured.
        TypeError: The configured backend runtime dependencies have one unexpected type.
    """
    return get_runtime(request).catalog_service


def get_frontend_dist_directory(request: Request) -> Path:
    """Return the configured frontend asset directory from application state.

    Args:
        request: Current request used to access application state.

    Returns:
        The configured built frontend `dist/` directory.

    Raises:
        RuntimeError: Backend application runtime dependencies have not been configured.
        TypeError: The configured backend runtime dependencies have one unexpected type.
    """
    return get_runtime(request).frontend_dist_directory


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield one request-scoped SQLAlchemy session.

    Args:
        request: Current request used to access application state.

    Yields:
        One request-scoped SQLAlchemy session.
    """
    database_session = get_runtime(request).session_factory()
    try:
        yield database_session
        database_session.commit()
    except Exception:
        database_session.rollback()
        raise
    finally:
        database_session.close()


def get_session_service(
    request: Request,
    database_session: Annotated[Session, Depends(get_db_session)],
) -> SessionService:
    """Return one request-scoped participant session service.

    Args:
        request: Current request used to access application state.
        database_session: Request-scoped SQLAlchemy session.

    Returns:
        The configured request-scoped session service.
    """
    runtime = get_runtime(request)
    return SessionService(
        catalog_repository=runtime.catalog_repository,
        session_repository=SessionRepository(database_session, session_key_factory=build_session_key),
        plan_repository=SessionPlanRepository(database_session),
        scoring_repository=SessionScoringRepository(database_session),
        plan_seed_provider=build_plan_seed,
        score_interpretation=runtime.settings.session_score_interpretation,
    )


def build_plan_seed() -> int:
    """Return one random seed for deterministic session run-plan generation.

    Returns:
        One random seed for deterministic session run-plan generation.
    """
    return randbelow(2**31)


def build_session_key() -> str:
    """Return one opaque public session identifier for client-facing routes.

    Returns:
        One opaque public session identifier for client-facing routes.
    """
    return token_urlsafe(18)
