"""Tests for backend IAT routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_iat_service
from apps.backend.repositories.iat import IatRepository
from apps.backend.routers.iats import router
from apps.backend.routers.stimuli import router as stimuli_router
from apps.backend.services.iat import IatService
from apps.backend.settings import IatResourcesSettings
from libs.testing.io import write_json, write_png


def _app_with_iat_service(iat_service: IatService) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.include_router(stimuli_router, prefix="/api")
    app.dependency_overrides[get_iat_service] = lambda: iat_service
    return app


def test_list_iats_returns_summaries(tmp_path: Path) -> None:
    # Given: one app with one configured IAT service.
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
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
    app = _app_with_iat_service(
        IatService(
            IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))
        )
    )

    # When: the client requests the IAT list.
    with TestClient(app) as client:
        response = client.get("/api/iats")

    # Then: the route returns one IAT summary.
    assert response.status_code == 200
    assert response.json() == [
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
        }
    ]


def test_get_iat_returns_detail_with_public_image_url(tmp_path: Path) -> None:
    # Given: one app with one configured image-backed IAT.
    spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    image_path = tmp_path / "resources/stimuli/face/example/images/seed-0.png"
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
    write_png(image_path)
    app = _app_with_iat_service(
        IatService(
            IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))
        )
    )

    # When: the client requests the IAT detail.
    with TestClient(app) as client:
        response = client.get("/api/iats/sample-iat")

    # Then: the route returns one routed image URL.
    assert response.status_code == 200
    assert response.json()["categories"][0]["category"][0]["stimuli"][0]["image_url"].startswith(
        "/api/stimuli/sample-iat/alpha/"
    )


def test_get_iat_returns_not_found_for_unknown_slug(tmp_path: Path) -> None:
    # Given: one app with one empty IAT service.
    app = _app_with_iat_service(IatService(IatRepository(IatResourcesSettings(iats=()).resolve(tmp_path))))

    # When: the client requests one unavailable IAT.
    with TestClient(app) as client:
        response = client.get("/api/iats/missing-iat")

    # Then: the route reports the IAT as missing.
    assert response.status_code == 404
    assert response.json() == {"detail": "IAT not found."}
