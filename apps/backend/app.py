"""FastAPI application composition for the backend IAT API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from apps.backend.dependencies import BackendServices
from apps.backend.repositories.iat import IatRepository
from apps.backend.routers.iats import router as iats_router
from apps.backend.routers.stimuli import router as stimuli_router
from apps.backend.services.iat import IatService

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
        app.state.services = BackendServices(iat_service=IatService(IatRepository(settings)))
        yield

    app = FastAPI(title="IAT Backend", debug=settings.debug, lifespan=lifespan)
    app.include_router(iats_router, prefix="/api")
    app.include_router(stimuli_router, prefix="/api")

    return app
