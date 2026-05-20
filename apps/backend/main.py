"""Executable entrypoint for the backend FastAPI server."""

from __future__ import annotations

import os

import uvicorn

from apps.backend.app import create_app
from apps.backend.settings import load_settings


def main() -> None:
    """Load backend settings from the environment and start the Uvicorn server."""
    settings = load_settings(os.environ)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
