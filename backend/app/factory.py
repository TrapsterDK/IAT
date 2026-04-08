"""Application factory functions."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import Settings
from backend.app.database import init_db
from backend.app.logging import configure_logging
from backend.app.routes.api import api_router
from backend.app.services import sync_app_definitions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create tables and sync YAML definitions before serving requests."""
    sync_app_definitions(app)
    yield


def _http_error_message(exc: HTTPException) -> str:
    if isinstance(exc.detail, str) and exc.detail:
        return exc.detail

    try:
        return HTTPStatus(exc.status_code).phrase
    except ValueError:
        return "Request failed."


def create_app(settings: Settings) -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging(settings)
    app = FastAPI(title="IAT", lifespan=lifespan)
    app.state.settings = settings

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            content={"error": _http_error_message(exc)},
            status_code=exc.status_code,
        )

    init_db(app, settings)
    Path(settings.ASSETS_DIR).mkdir(parents=True, exist_ok=True)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/assets", StaticFiles(directory=settings.ASSETS_DIR), name="assets")
    app.include_router(api_router)

    return app
