"""FastAPI application composition for the backend catalog and session API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from apps.backend.database import create_database_schema, create_session_factory, create_sqlite_engine
from apps.backend.dependencies import BackendRuntime
from apps.backend.repositories.catalog import CatalogRepository
from apps.backend.routers.catalog import router as catalog_router
from apps.backend.routers.sessions import router as sessions_router
from apps.backend.routers.stimuli import router as stimuli_router
from apps.backend.services.catalog import CatalogService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from apps.backend.settings import ResolvedIatResources


def create_app(settings: ResolvedIatResources) -> FastAPI:
    """Create the backend FastAPI application.

    Args:
        settings: Explicit resolved backend settings.

    Returns:
        The configured backend FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_sqlite_engine(settings.database_path)
        try:
            catalog_repository = CatalogRepository(settings)
            create_database_schema(engine)
            app.state.runtime = BackendRuntime(
                catalog_repository=catalog_repository,
                catalog_service=CatalogService(catalog_repository),
                session_factory=create_session_factory(engine),
                settings=settings,
            )
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="IAT Backend", debug=settings.debug, lifespan=lifespan)
    app.include_router(catalog_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(stimuli_router, prefix="/api")

    return app
