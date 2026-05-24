"""Shared pytest fixtures for backend router tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from apps.backend.app import create_app
from apps.backend.database import create_session_factory
from apps.backend.dependencies import BackendRuntime
from apps.backend.frontend import resolve_frontend_dist_directory
from apps.backend.repositories.catalog import CatalogRepository
from apps.backend.routers.catalog import router as catalog_router
from apps.backend.routers.stimuli import router as stimuli_router
from apps.backend.services.catalog import CatalogService
from apps.backend.settings import IatResourcesSettings, ResolvedIatResources
from libs.testing.io import write_json, write_png

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


def _write_sample_image_iat_spec(spec_path: Path) -> None:
    write_json(
        spec_path,
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "alpha",
                            "label": "Alpha",
                            "stimuli": [{"image": "../stimuli/face/example/images/seed-0.png"}],
                        },
                        {"slug": "beta", "label": "Beta", "stimuli": [{"text": "beta"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "gamma", "label": "Gamma", "stimuli": [{"text": "gamma"}]},
                        {"slug": "delta", "label": "Delta", "stimuli": [{"text": "delta"}]},
                    ]
                },
            ],
        },
    )


def _write_sample_text_iat_spec(spec_path: Path) -> None:
    write_json(
        spec_path,
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
            "categories": [
                {
                    "category": [
                        {"slug": "alpha", "label": "Alpha", "stimuli": [{"text": "alpha"}]},
                        {"slug": "beta", "label": "Beta", "stimuli": [{"text": "beta"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "gamma", "label": "Gamma", "stimuli": [{"text": "gamma"}]},
                        {"slug": "delta", "label": "Delta", "stimuli": [{"text": "delta"}]},
                    ]
                },
            ],
        },
    )


def _write_duplicate_label_iat_spec(spec_path: Path) -> None:
    write_json(
        spec_path,
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
            "categories": [
                {
                    "category": [
                        {"slug": "alpha", "label": "Alpha", "stimuli": [{"text": "alpha"}]},
                        {"slug": "beta", "label": "Alpha", "stimuli": [{"text": "beta"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "gamma", "label": "Gamma", "stimuli": [{"text": "gamma"}]},
                        {"slug": "delta", "label": "Delta", "stimuli": [{"text": "delta"}]},
                    ]
                },
            ],
        },
    )


@pytest.fixture
def image_catalog_settings(tmp_path: Path) -> ResolvedIatResources:
    """Provide resolved resources for one image-backed sample IAT.

    Args:
        tmp_path: Temporary test workspace root.

    Returns:
        Resolved backend resources for one sample IAT with one image stimulus.
    """
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    image_path = tmp_path / "resources/stimuli/face/example/images/seed-0.png"
    _write_sample_image_iat_spec(spec_path)
    write_png(image_path)
    return IatResourcesSettings(
        database_path=Path("instance/router-test.sqlite3"),
        iats=(Path("resources/iats/sample-iat.yaml"),),
    ).resolve(tmp_path)


@pytest.fixture
def published_image_path(image_catalog_settings: ResolvedIatResources) -> PurePosixPath:
    """Return one published image path from the sample image-backed IAT.

    Args:
        image_catalog_settings: Resolved resources for the sample image-backed IAT.

    Returns:
        One published image path from the sample IAT.
    """
    published_iat = CatalogRepository(image_catalog_settings).get_iat("sample-iat")
    if published_iat is None:
        raise RuntimeError("Expected the sample IAT to be published for router tests.")

    image_path = published_iat.categories[0][0].stimuli[0].image_path
    if image_path is None:
        raise RuntimeError("Expected one published image stimulus for router tests.")

    return image_path


@pytest.fixture
def catalog_router_client(image_catalog_settings: ResolvedIatResources) -> Iterator[TestClient]:
    """Provide one focused app that serves catalog and stimulus routes.

    Args:
        image_catalog_settings: Resolved resources for the sample image-backed IAT.

    Yields:
        One test client backed by focused catalog and stimulus routes.
    """
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    catalog_repository = CatalogRepository(image_catalog_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.runtime = BackendRuntime(
        catalog_repository=catalog_repository,
        catalog_service=CatalogService(catalog_repository),
        frontend_dist_directory=resolve_frontend_dist_directory(),
        session_factory=create_session_factory(engine),
        settings=image_catalog_settings,
    )
    app.include_router(catalog_router, prefix="/api")
    app.include_router(stimuli_router)

    with TestClient(app) as client:
        yield client


@pytest.fixture
def session_client(tmp_path: Path) -> Iterator[TestClient]:
    """Provide one full backend app client for session route tests.

    Args:
        tmp_path: Temporary test workspace root.

    Yields:
        One test client backed by the full backend application.
    """
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    _write_sample_text_iat_spec(spec_path)
    settings = IatResourcesSettings(
        database_path=Path("instance/backend.sqlite3"),
        iats=(Path("resources/iats/sample-iat.yaml"),),
    ).resolve(tmp_path)

    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def image_session_client(tmp_path: Path) -> Iterator[TestClient]:
    """Provide one full backend app client for image-backed session route tests.

    Args:
        tmp_path: Temporary test workspace root.

    Yields:
        One test client backed by the full backend application.
    """
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    image_path = tmp_path / "resources/stimuli/face/example/images/seed-0.png"
    _write_sample_image_iat_spec(spec_path)
    write_png(image_path)
    settings = IatResourcesSettings(
        database_path=Path("instance/backend.sqlite3"),
        iats=(Path("resources/iats/sample-iat.yaml"),),
    ).resolve(tmp_path)

    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def duplicate_label_session_client(tmp_path: Path) -> Iterator[TestClient]:
    """Provide one backend app client whose published IAT yields duplicate session block labels.

    Args:
        tmp_path: Temporary test workspace root.

    Yields:
        One test client backed by the full backend application.
    """
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    _write_duplicate_label_iat_spec(spec_path)
    settings = IatResourcesSettings(
        database_path=Path("instance/backend.sqlite3"),
        iats=(Path("resources/iats/sample-iat.yaml"),),
    ).resolve(tmp_path)

    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        yield client
