"""Tests for backend FastAPI dependency helpers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.backend.dependencies import (
    BackendRuntime,
    get_db_session,
    get_iat_service,
    get_runtime,
    get_session_service,
)
from apps.backend.domain.session.models import ClientContext


def _runtime_app(expected_runtime: BackendRuntime | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/runtime")
    def read_runtime(runtime: Annotated[BackendRuntime, Depends(get_runtime)]) -> dict[str, bool]:
        return {"matches": runtime is expected_runtime}

    return app


def _iat_service_app(expected_iat_service: object | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/iat-service")
    def read_iat_service(iat_service: Annotated[object, Depends(get_iat_service)]) -> dict[str, bool]:
        return {"matches": iat_service is expected_iat_service}

    return app


def test_get_runtime_returns_backend_runtime_from_app_state(
    backend_runtime: BackendRuntime,
) -> None:
    # Given: one FastAPI app whose application state stores one typed backend runtime container.
    app = _runtime_app(backend_runtime)
    app.state.runtime = backend_runtime

    # When: one client resolves the shared runtime dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/runtime")

    # Then: the stored runtime container is returned.
    assert response.status_code == 200
    assert response.json() == {"matches": True}


def test_get_runtime_raises_when_backend_runtime_is_missing() -> None:
    # Given: one FastAPI app whose application state has no backend runtime container.
    app = _runtime_app()

    # When: one client resolves the shared runtime dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/runtime")

    # Then: the missing runtime container is rejected.
    assert response.status_code == 500


def test_get_runtime_raises_when_backend_runtime_has_unexpected_type() -> None:
    # Given: one FastAPI app whose application state stores one unexpected runtime object.
    app = _runtime_app()
    app.state.runtime = object()

    # When: one client resolves the shared runtime dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/runtime")

    # Then: the unexpected runtime object is rejected.
    assert response.status_code == 500


def test_get_iat_service_returns_service_from_backend_services(backend_runtime: BackendRuntime) -> None:
    # Given: one FastAPI app whose application state stores one typed backend runtime container.
    expected_iat_service = backend_runtime.iat_service
    app = _iat_service_app(expected_iat_service)
    app.state.runtime = backend_runtime

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/iat-service")

    # Then: the stored IAT service is returned.
    assert response.status_code == 200
    assert response.json() == {"matches": True}


def test_get_iat_service_raises_when_backend_services_are_missing() -> None:
    # Given: one FastAPI app whose application state has no backend runtime container.
    app = _iat_service_app()

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/iat-service")

    # Then: the missing services container is rejected.
    assert response.status_code == 500


def test_get_iat_service_raises_when_backend_services_have_unexpected_type() -> None:
    # Given: one FastAPI app whose application state stores one unexpected runtime object.
    app = _iat_service_app()
    app.state.runtime = object()

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/iat-service")

    # Then: the unexpected runtime object is rejected.
    assert response.status_code == 500


def test_get_db_session_yields_one_request_scoped_database_session(
    backend_runtime: BackendRuntime,
) -> None:
    # Given: one FastAPI app that exposes the request-scoped database session dependency.
    app = FastAPI()

    @app.get("/db-session")
    def read_db_session(database_session: Annotated[Session, Depends(get_db_session)]) -> dict[str, bool]:
        return {"is_session": isinstance(database_session, Session)}

    app.state.runtime = backend_runtime

    # When: one client resolves the database session dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/db-session")

    # Then: the dependency yields one SQLAlchemy session object.
    assert response.status_code == 200
    assert response.json() == {"is_session": True}


def test_get_db_session_commits_request_scoped_changes(
    backend_runtime: BackendRuntime,
) -> None:
    # Given: one request-scoped session dependency writes one row to one prepared table.
    app = FastAPI()

    @app.post("/db-session")
    def write_with_request_session(database_session: Annotated[Session, Depends(get_db_session)]) -> dict[str, int]:
        database_session.execute(text("INSERT INTO request_events (value) VALUES (1)"))
        return {"written": 1}

    app.state.runtime = backend_runtime

    with backend_runtime.session_factory() as setup_session:
        setup_session.execute(text("DROP TABLE IF EXISTS request_events"))
        setup_session.execute(text("CREATE TABLE request_events (value INTEGER NOT NULL)"))
        setup_session.commit()

    # When: one client completes one successful request that uses the database session dependency.
    with TestClient(app) as client:
        response = client.post("/db-session")

    # Then: the dependency commits the request-scoped transaction.
    with backend_runtime.session_factory() as verify_session:
        persisted_row_count = verify_session.scalar(text("SELECT COUNT(*) FROM request_events"))

    assert response.status_code == 200
    assert response.json() == {"written": 1}
    assert persisted_row_count == 1


def test_get_db_session_rolls_back_request_failures(
    backend_runtime: BackendRuntime,
) -> None:
    # Given: one request-scoped session dependency writes one row before one failing request raises an error.
    app = FastAPI()

    @app.post("/db-session")
    def fail_after_write(database_session: Annotated[Session, Depends(get_db_session)]) -> None:
        database_session.execute(text("INSERT INTO request_events (value) VALUES (1)"))
        raise RuntimeError("boom")

    app.state.runtime = backend_runtime

    with backend_runtime.session_factory() as setup_session:
        setup_session.execute(text("DROP TABLE IF EXISTS request_events"))
        setup_session.execute(text("CREATE TABLE request_events (value INTEGER NOT NULL)"))
        setup_session.commit()

    # When: one client triggers one failing request that uses the database session dependency.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/db-session")

    # Then: the dependency rolls back the request-scoped transaction.
    with backend_runtime.session_factory() as verify_session:
        persisted_row_count = verify_session.scalar(text("SELECT COUNT(*) FROM request_events"))

    assert response.status_code == 500
    assert persisted_row_count == 0


def test_get_session_service_uses_runtime_settings_for_created_sessions(
    session_runtime: BackendRuntime,
) -> None:
    # Given: one runtime with one published IAT and non-default session thresholds.
    app = FastAPI()
    app.state.runtime = session_runtime
    request = Request({"type": "http", "app": app})

    # When: the request-scoped session service creates one participant session.
    with session_runtime.session_factory() as database_session:
        session_service = get_session_service(request, database_session)
        state, run_plan = session_service.create_session("sample-iat", ClientContext())

    # Then: the created session uses the runtime-configured thresholds and remains running.
    assert run_plan.anticipation_threshold_ms == session_runtime.settings.anticipation_threshold_ms
    assert run_plan.response_timeout_ms == session_runtime.settings.response_timeout_ms
    assert state.completed_at_utc is None
