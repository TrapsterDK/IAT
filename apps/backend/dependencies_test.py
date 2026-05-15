"""Tests for backend FastAPI dependency helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from apps.backend.dependencies import BackendServices, get_iat_service, get_services
from apps.backend.repositories.iat import IatRepository
from apps.backend.services.iat import IatService
from apps.backend.settings import IatResourcesSettings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def empty_iat_service(tmp_path: Path) -> IatService:
    return IatService(IatRepository(IatResourcesSettings(iats=()).resolve(tmp_path)))


def _services_app(expected_services: BackendServices | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/services")
    def read_services(services: Annotated[BackendServices, Depends(get_services)]) -> dict[str, bool]:
        return {"matches": services is expected_services}

    return app


def _iat_service_app(expected_iat_service: IatService | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/iat-service")
    def read_iat_service(iat_service: Annotated[IatService, Depends(get_iat_service)]) -> dict[str, bool]:
        return {"matches": iat_service is expected_iat_service}

    return app


def test_get_services_returns_backend_services_from_app_state(empty_iat_service: IatService) -> None:
    # Given: one FastAPI app whose application state stores one typed backend services container.
    expected_services = BackendServices(iat_service=empty_iat_service)
    app = _services_app(expected_services)
    app.state.services = expected_services

    # When: one client resolves the shared services dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/services")

    # Then: the stored services container is returned.
    assert response.status_code == 200
    assert response.json() == {"matches": True}


def test_get_services_raises_when_backend_services_are_missing() -> None:
    # Given: one FastAPI app whose application state has no backend services container.
    app = _services_app()

    # When: one client resolves the shared services dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/services")

    # Then: the missing services container is rejected.
    assert response.status_code == 500


def test_get_services_raises_when_backend_services_have_unexpected_type() -> None:
    # Given: one FastAPI app whose application state stores one unexpected services object.
    app = _services_app()
    app.state.services = object()

    # When: one client resolves the shared services dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/services")

    # Then: the unexpected services object is rejected.
    assert response.status_code == 500


def test_get_iat_service_returns_service_from_backend_services(empty_iat_service: IatService) -> None:
    # Given: one FastAPI app whose application state stores one typed backend services container.
    expected_iat_service = empty_iat_service
    app = _iat_service_app(expected_iat_service)
    app.state.services = BackendServices(iat_service=expected_iat_service)

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/iat-service")

    # Then: the stored IAT service is returned.
    assert response.status_code == 200
    assert response.json() == {"matches": True}


def test_get_iat_service_raises_when_backend_services_are_missing() -> None:
    # Given: one FastAPI app whose application state has no backend services container.
    app = _iat_service_app()

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/iat-service")

    # Then: the missing services container is rejected.
    assert response.status_code == 500


def test_get_iat_service_raises_when_backend_services_have_unexpected_type() -> None:
    # Given: one FastAPI app whose application state stores one unexpected services object.
    app = _iat_service_app()
    app.state.services = object()

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/iat-service")

    # Then: the unexpected services object is rejected.
    assert response.status_code == 500
