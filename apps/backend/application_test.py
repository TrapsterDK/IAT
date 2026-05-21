"""Tests for shared backend FastAPI application construction helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from apps.backend.application import create_base_app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


def test_create_base_app_registers_shared_public_routes() -> None:
    # Given: one base backend app created without one custom lifespan handler.
    app = create_base_app(debug=False)

    # When: the registered route paths are inspected.
    registered_paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    # Then: the shared application includes the public API routes and frontend shell routes.
    assert "/" in registered_paths
    assert "/assets/{asset_path:path}" in registered_paths
    assert "/api/iats" in registered_paths
    assert "/api/iats/{slug}" in registered_paths
    assert "/api/sessions" in registered_paths
    assert "/api/sessions/{session_key}/blocks/{block_index}" in registered_paths
    assert "/api/sessions/{session_key}/score" in registered_paths


def test_create_base_app_uses_given_debug_and_lifespan() -> None:
    # Given: one explicit lifespan handler.
    lifecycle_events: list[str] = []

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        lifecycle_events.append("started")
        yield
        lifecycle_events.append("stopped")

    # When: one base backend app is created from those explicit settings.
    app = create_base_app(debug=True, lifespan=lifespan)
    with TestClient(app):
        pass

    # Then: the resulting FastAPI application preserves both options.
    assert app.debug is True
    assert lifecycle_events == ["started", "stopped"]
