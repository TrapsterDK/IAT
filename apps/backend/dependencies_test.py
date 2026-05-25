"""Tests for backend FastAPI dependency helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, FastAPI, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session  # noqa: TC002

from apps.backend.dependencies import (
    BackendRuntime,
    get_catalog_service,
    get_db_session,
    get_runtime,
    get_session_service,
)
from apps.backend.models.session import (
    ClientContext,
    CompletedBlockInput,
    CompletedTrialInput,
    SessionCreateInput,
    SessionMode,
    TrialEventInput,
    TrialEventType,
)
from apps.backend.settings import SessionScoreInterpretationSettings

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


def _runtime_app(expected_runtime: BackendRuntime | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/runtime")
    def read_runtime(runtime: Annotated[BackendRuntime, Depends(get_runtime)]) -> dict[str, bool]:
        return {"matches": runtime is expected_runtime}

    return app


def _catalog_service_app(expected_catalog_service: object | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/catalog-service")
    def read_catalog_service(catalog_service: Annotated[object, Depends(get_catalog_service)]) -> dict[str, bool]:
        return {"matches": catalog_service is expected_catalog_service}

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


def test_get_catalog_service_returns_service_from_backend_services(backend_runtime: BackendRuntime) -> None:
    # Given: one FastAPI app whose application state stores one typed backend runtime container.
    expected_catalog_service = backend_runtime.catalog_service
    app = _catalog_service_app(expected_catalog_service)
    app.state.runtime = backend_runtime

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/catalog-service")

    # Then: the stored IAT service is returned.
    assert response.status_code == 200
    assert response.json() == {"matches": True}


def test_get_catalog_service_raises_when_backend_services_are_missing() -> None:
    # Given: one FastAPI app whose application state has no backend runtime container.
    app = _catalog_service_app()

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/catalog-service")

    # Then: the missing services container is rejected.
    assert response.status_code == 500


def test_get_catalog_service_raises_when_backend_services_have_unexpected_type() -> None:
    # Given: one FastAPI app whose application state stores one unexpected runtime object.
    app = _catalog_service_app()
    app.state.runtime = object()

    # When: one client resolves the shared IAT service dependency through one endpoint.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/catalog-service")

    # Then: the unexpected runtime object is rejected.
    assert response.status_code == 500


def test_get_db_session_yields_one_request_scoped_database_session(
    backend_runtime: BackendRuntime,
) -> None:
    # Given: one FastAPI app that exposes the request-scoped database session dependency.
    app = FastAPI()

    @app.get("/db-session")
    def read_db_session(database_session: Annotated[Session, Depends(get_db_session)]) -> dict[str, int]:
        return {"query_result": database_session.scalar(text("SELECT 1"))}

    app.state.runtime = backend_runtime

    # When: one client resolves the database session dependency through one endpoint.
    with TestClient(app) as client:
        response = client.get("/db-session")

    # Then: the dependency yields one SQLAlchemy session object.
    assert response.status_code == 200
    assert response.json() == {"query_result": 1}


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


def test_get_db_session_function_scope_commits_before_response_is_returned(
    backend_runtime: BackendRuntime,
) -> None:
    # Given: one endpoint uses the database-session dependency with function scope.
    app = FastAPI()
    observed_persisted_row_counts: list[int] = []

    @app.middleware("http")
    async def capture_persisted_row_count(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        with backend_runtime.session_factory() as verify_session:
            observed_persisted_row_counts.append(
                int(verify_session.scalar(text("SELECT COUNT(*) FROM request_events")))
            )

        return response

    @app.post("/db-session")
    def write_with_function_scoped_session(
        database_session: Annotated[Session, Depends(get_db_session, scope="function")],
    ) -> dict[str, int]:
        database_session.execute(text("INSERT INTO request_events (value) VALUES (1)"))
        visible_row_count = database_session.scalar(text("SELECT COUNT(*) FROM request_events"))
        return {"request_visible": int(visible_row_count)}

    app.state.runtime = backend_runtime

    with backend_runtime.session_factory() as setup_session:
        setup_session.execute(text("DROP TABLE IF EXISTS request_events"))
        setup_session.execute(text("CREATE TABLE request_events (value INTEGER NOT NULL)"))
        setup_session.commit()

    # When: one client completes one successful request through the function-scoped dependency.
    with TestClient(app) as client:
        response = client.post("/db-session")

    # Then: middleware after the route handler observes the committed write before the response is returned.
    assert response.status_code == 200
    assert response.json() == {"request_visible": 1}
    assert observed_persisted_row_counts == [1]


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


def test_get_session_service_uses_runtime_score_interpretation_settings(
    session_runtime: BackendRuntime,
) -> None:
    # Given: one runtime whose score-interpretation settings classify the sample score as neutral.
    neutral_runtime = BackendRuntime(
        catalog_repository=session_runtime.catalog_repository,
        catalog_service=session_runtime.catalog_service,
        frontend_dist_directory=session_runtime.frontend_dist_directory,
        session_factory=session_runtime.session_factory,
        settings=session_runtime.settings.model_copy(
            update={
                "session_score_interpretation": SessionScoreInterpretationSettings(
                    little_to_no_association_upper_bound=10.0,
                    slight_association_upper_bound=11.0,
                    moderate_association_upper_bound=12.0,
                )
            }
        ),
    )
    app = FastAPI()
    app.state.runtime = neutral_runtime
    request = Request({"type": "http", "app": app})

    # When: the function-scoped session service completes and scores one sample session.
    with session_runtime.session_factory() as database_session:
        session_service = get_session_service(request, database_session)
        state, run_plan = session_service.create_session(
            SessionCreateInput(
                iat_slug="sample-iat",
                client_context=ClientContext(),
                session_mode=SessionMode.PARTICIPANT,
                plan_seed=None,
            )
        )
        for block_index, block in enumerate(run_plan.blocks, start=1):
            session_service.complete_block(
                state.session_key,
                block_index,
                CompletedBlockInput(
                    trials=tuple(
                        CompletedTrialInput(
                            events=(
                                TrialEventInput(
                                    event_type=(
                                        TrialEventType.LEFT
                                        if trial.correct_response_side.value == TrialEventType.LEFT.value
                                        else TrialEventType.RIGHT
                                    ),
                                    elapsed_ms=350 + block_index * 50,
                                ),
                            )
                        )
                        for trial in block.trials
                    )
                ),
            )
        database_session.commit()
        score_result = session_service.get_score(state.session_key)

    # Then: the resolved service uses the runtime score-interpretation settings for one public score result.
    assert score_result.headline == "Little to no automatic association."
