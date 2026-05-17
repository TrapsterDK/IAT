"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from apps.backend.database import create_database_schema, create_session_factory, create_sqlite_engine
from apps.backend.dependencies import BackendRuntime
from apps.backend.repositories.iat import IatRepository
from apps.backend.services.iat import IatService
from apps.backend.settings import IatResourcesSettings
from libs.testing.io import write_json

if TYPE_CHECKING:
    from collections.abc import Iterator


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


@pytest.fixture
def backend_runtime(tmp_path: Path) -> Iterator[BackendRuntime]:
    """Provide one backend runtime without published IAT resources.

    Args:
        tmp_path: Temporary test workspace root.

    Yields:
        One backend runtime without configured published IATs.
    """
    settings = IatResourcesSettings(iats=()).resolve(tmp_path)
    engine = create_sqlite_engine(settings.database_path)
    iat_repository = IatRepository(settings)

    try:
        yield BackendRuntime(
            iat_repository=iat_repository,
            iat_service=IatService(iat_repository),
            session_factory=create_session_factory(engine),
            settings=settings,
        )
    finally:
        engine.dispose()


@pytest.fixture
def session_runtime(tmp_path: Path) -> Iterator[BackendRuntime]:
    """Provide one backend runtime with one published sample IAT.

    Args:
        tmp_path: Temporary test workspace root.

    Yields:
        One backend runtime with one configured sample IAT and session schema.
    """
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    _write_sample_text_iat_spec(spec_path)
    settings = IatResourcesSettings(
        database_path=Path("instance/backend.sqlite3"),
        anticipation_threshold_ms=125,
        response_timeout_ms=825,
        iats=(Path("resources/iats/sample-iat.yaml"),),
    ).resolve(tmp_path)
    engine = create_sqlite_engine(settings.database_path)
    iat_repository = IatRepository(settings)
    create_database_schema(engine)

    try:
        yield BackendRuntime(
            iat_repository=iat_repository,
            iat_service=IatService(iat_repository),
            session_factory=create_session_factory(engine),
            settings=settings,
        )
    finally:
        engine.dispose()
