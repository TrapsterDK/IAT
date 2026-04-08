"""FastAPI application entrypoint."""

from __future__ import annotations

import uvicorn

from backend.app import create_app
from backend.app.config import get_config

settings = get_config()
app = create_app(settings)


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.UVICORN_HOST,
        port=settings.UVICORN_PORT,
        reload=settings.UVICORN_RELOAD,
    )
