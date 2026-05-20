"""Tests for backend catalog routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_list_iats_returns_summaries(catalog_router_client: TestClient) -> None:
    # Given: one backend app with one configured IAT.

    # When: the client requests the IAT list.
    response = catalog_router_client.get("/iats")

    # Then: the route returns one IAT summary.
    assert response.status_code == 200
    assert response.json() == [
        {
            "slug": "sample-iat",
            "title": "Sample IAT",
            "description": "Measures one sample association.",
        }
    ]


def test_get_iat_returns_detail_with_public_image_url(catalog_router_client: TestClient) -> None:
    # Given: one backend app with one configured image-backed IAT.

    # When: the client requests the IAT detail.
    response = catalog_router_client.get("/iats/sample-iat")

    # Then: the route returns one routed image URL.
    assert response.status_code == 200
    assert response.json()["categories"][0]["category"][0]["stimuli"][0]["image_url"].startswith(
        "/stimuli/sample-iat/alpha/"
    )


def test_get_iat_returns_not_found_for_unknown_slug(catalog_router_client: TestClient) -> None:
    # Given: one backend app with no matching IAT slug.

    # When: the client requests one unavailable IAT.
    response = catalog_router_client.get("/iats/missing-iat")

    # Then: the route reports the IAT as missing.
    assert response.status_code == 404
    assert response.json() == {"detail": "IAT not found."}
