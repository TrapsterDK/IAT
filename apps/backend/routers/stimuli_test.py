"""Tests for backend stimulus routes."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.backend.dependencies import get_iat_service
from apps.backend.repositories.iat import IatRepository
from apps.backend.routers.stimuli import router
from apps.backend.services.iat import IatService
from apps.backend.settings import IatResourcesSettings
from libs.testing.io import TEST_PNG_SIGNATURE, write_json, write_png


def _app_with_iat_service(iat_service: IatService) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_iat_service] = lambda: iat_service
    return app


def test_get_stimulus_serves_png(tmp_path: Path) -> None:
    # Given: one app with one published PNG stimulus.
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
    service = IatService(
        IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))
    )
    published_iat = service.get_iat("sample-iat")
    assert published_iat is not None
    published_image = published_iat.categories[0][0].stimuli[0].image
    assert published_image is not None
    app = _app_with_iat_service(service)

    # When: the client requests the published PNG stimulus.
    with TestClient(app) as client:
        response = client.get(f"/api/stimuli/{published_image.as_posix()}")

    # Then: the route serves the PNG file.
    assert response.status_code == httpx.codes.OK
    assert response.content == TEST_PNG_SIGNATURE
    assert response.headers["content-type"].startswith("image/png")


def test_get_stimulus_returns_not_found_for_unknown_path(tmp_path: Path) -> None:
    # Given: one app with one empty IAT service.
    app = _app_with_iat_service(IatService(IatRepository(IatResourcesSettings(iats=()).resolve(tmp_path))))

    # When: the client requests one unpublished stimulus path.
    with TestClient(app) as client:
        response = client.get(f"/api/stimuli/{PurePosixPath('missing/image.png').as_posix()}")

    # Then: the route reports the stimulus as missing.
    assert response.status_code == 404
    assert response.json() == {"detail": "Stimulus not found."}
