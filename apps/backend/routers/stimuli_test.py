"""Tests for backend stimulus routes."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import httpx

from libs.testing.io import TEST_PNG_SIGNATURE

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_stimulus_serves_png(
    catalog_router_client: TestClient,
    published_image_path: PurePosixPath,
) -> None:
    # Given: one backend app with one published PNG stimulus.
    published_image_url = PurePosixPath(f"/api/stimuli/{published_image_path.as_posix()}")

    # When: the client requests the published PNG stimulus.
    response = catalog_router_client.get(published_image_url.as_posix())

    # Then: the route serves the PNG file.
    assert response.status_code == httpx.codes.OK
    assert response.content == TEST_PNG_SIGNATURE
    assert response.headers["content-type"].startswith("image/png")


def test_get_stimulus_returns_not_found_for_unknown_path(catalog_router_client: TestClient) -> None:
    # Given: one backend app without the requested published stimulus path.

    # When: the client requests one unpublished stimulus path.
    response = catalog_router_client.get(f"/api/stimuli/{PurePosixPath('missing/image.png').as_posix()}")

    # Then: the route reports the stimulus as missing.
    assert response.status_code == 404
    assert response.json() == {"detail": "Stimulus not found."}
