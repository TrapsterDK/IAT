"""Executable entrypoint for the backend FastAPI server."""

from __future__ import annotations

import os

import uvicorn

from apps.backend.app import create_app
from apps.backend.settings import load_settings

if __name__ == "__main__":
    settings = load_settings(os.environ)
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
