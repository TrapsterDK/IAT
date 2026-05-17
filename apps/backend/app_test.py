"""Tests for backend FastAPI application composition."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.backend.app import create_app
from apps.backend.models.iat import StimulusResponse
from apps.backend.settings import IAT_RESOURCES_CONFIG_PATH_ENV_VAR, IatResourcesSettings, load_settings
from libs.testing.io import TEST_PNG_SIGNATURE, write_json, write_png


def test_create_app_wires_iat_detail_and_stimulus_routes(tmp_path: Path) -> None:
    # Given: one configured IAT with one published PNG stimulus.
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
                        {
                            "slug": "beta",
                            "label": "Beta",
                            "stimuli": [{"text": "beta"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "gamma",
                            "label": "Gamma",
                            "stimuli": [{"text": "gamma"}],
                        },
                        {
                            "slug": "delta",
                            "label": "Delta",
                            "stimuli": [{"text": "delta"}],
                        },
                    ]
                },
            ],
        },
    )
    write_png(image_path)
    settings = IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path)

    # When: the client requests the IAT detail and then follows the returned stimulus URL.
    with TestClient(create_app(settings)) as client:
        detail_response = client.get("/api/iats/sample-iat")
        stimulus_path = detail_response.json()["categories"][0]["category"][0]["stimuli"][0]["image_url"]
        stimulus_response = client.get(stimulus_path)

    # Then: the composed app serves both routes consistently.
    assert detail_response.status_code == 200
    assert stimulus_path.startswith("/api/stimuli/sample-iat/alpha/")
    assert stimulus_response.status_code == 200
    assert stimulus_response.content == TEST_PNG_SIGNATURE
    assert stimulus_response.headers["content-type"].startswith("image/png")


def test_create_app_rejects_non_configured_iats(tmp_path: Path) -> None:
    # Given: one backend app configured to expose only one explicit IAT file.
    allowed_spec_path = tmp_path / "resources/iats/sample-iat.yaml"
    hidden_spec_path = tmp_path / "resources/iats/hidden-iat.yaml"
    image_path = tmp_path / "resources/stimuli/face/example/images/seed-0.png"
    write_json(
        allowed_spec_path,
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
                        {
                            "slug": "beta",
                            "label": "Beta",
                            "stimuli": [{"text": "beta"}],
                        },
                    ]
                },
                {
                    "category": [
                        {
                            "slug": "gamma",
                            "label": "Gamma",
                            "stimuli": [{"text": "gamma"}],
                        },
                        {
                            "slug": "delta",
                            "label": "Delta",
                            "stimuli": [{"text": "delta"}],
                        },
                    ]
                },
            ],
        },
    )
    write_json(
        hidden_spec_path,
        {
            "slug": "hidden-iat",
            "title": "Hidden IAT",
            "description": "Hidden.",
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
    write_png(image_path)
    settings = IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path)

    # When: the client requests one non-configured IAT.
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/iats/hidden-iat")

    # Then: the app reports the IAT as unavailable.
    assert response.status_code == 404


def test_create_app_uses_explicit_settings_without_main_owned_loading(tmp_path: Path) -> None:
    # Given: one backend app created from one explicitly loaded settings object.
    settings_path = tmp_path / "iat-settings.yaml"
    write_json(
        settings_path,
        {
            "iats": [],
        },
    )

    # When: the app is created directly and settings are loaded separately.
    resolved_settings = load_settings({IAT_RESOURCES_CONFIG_PATH_ENV_VAR: str(settings_path)})
    with TestClient(create_app(resolved_settings)) as client:
        response = client.get("/api/iats")

    # Then: the app is constructed successfully from the caller-supplied settings.
    assert response.status_code == 200
    assert response.json() == []


def test_create_app_uses_debug_setting(tmp_path: Path) -> None:
    # Given: one resolved backend settings object with debug disabled.
    settings = IatResourcesSettings(debug=False, iats=()).resolve(tmp_path)

    # When: one FastAPI app is created from those settings.
    app = create_app(settings)

    # Then: the FastAPI debug mode follows the provided settings.
    assert app.debug is False


def test_create_app_wires_session_creation_route(tmp_path: Path) -> None:
    # Given: one configured backend app with one published text-only IAT.
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
    settings = IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path)

    # When: the client creates one participant session.
    with TestClient(create_app(settings)) as client:
        created_response = client.post("/api/sessions", json={"iat_slug": "sample-iat"})

    # Then: the composed app exposes the session creation route and returns one bootstrap payload.
    assert created_response.status_code == 201
    assert created_response.json()["session_key"]


def test_backend_response_models_are_frozen() -> None:
    # Given: one validated public response model.
    stimulus = StimulusResponse(text="alpha")

    # When: one field is reassigned after validation.
    # Then: the frozen response model rejects mutation.
    with pytest.raises(ValidationError, match="Instance is frozen"):
        stimulus.text = "beta"
