"""Shared FastAPI application construction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from apps.backend.routers.catalog import router as catalog_router
from apps.backend.routers.frontend import router as frontend_router
from apps.backend.routers.sessions import router as sessions_router
from apps.backend.routers.stimuli import router as stimuli_router

if TYPE_CHECKING:
    from starlette.types import Lifespan


def create_base_app(*, debug: bool, lifespan: Lifespan[FastAPI] | None = None) -> FastAPI:
    """Create one backend app with the shared public routers registered.

    Args:
        debug: Whether FastAPI debug mode should be enabled.
        lifespan: Optional FastAPI lifespan handler.

    Returns:
        The configured FastAPI application.
    """
    app = FastAPI(title="IAT Backend", debug=debug, lifespan=lifespan)
    app.include_router(sessions_router, prefix="/api")
    app.include_router(catalog_router, prefix="/api")
    app.include_router(stimuli_router)
    app.include_router(frontend_router)
    return app
