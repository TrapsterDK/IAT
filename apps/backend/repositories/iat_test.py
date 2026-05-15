"""Tests for the backend filesystem-backed IAT repository."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path, PurePosixPath

import pytest

from apps.backend.repositories.iat import IatRepository
from apps.backend.settings import IatResourcesSettings
from libs.testing.io import write_json, write_png, write_yaml


def _published_image_path(iat_slug: str, category_slug: str, image_path: Path) -> PurePosixPath:
    image_key = (
        base64.urlsafe_b64encode(hashlib.sha256(str(image_path).encode("utf-8")).digest()).decode("ascii").rstrip("=")
    )
    return PurePosixPath(f"{iat_slug}/{category_slug}/{image_key}.png")


def test_get_iats_keeps_configured_order(tmp_path: Path) -> None:
    # Given: two configured IAT spec files in one explicit order.
    resources_root = tmp_path / "resources"
    write_json(
        resources_root / "iats/bravo.yaml",
        {
            "slug": "bravo",
            "title": "Bravo",
            "description": "bravo description.",
            "categories": [
                {
                    "category": [
                        {"slug": "left", "label": "Left", "stimuli": [{"text": "bravo"}]},
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    write_json(
        resources_root / "iats/alpha.yaml",
        {
            "slug": "alpha",
            "title": "Alpha",
            "description": "alpha description.",
            "categories": [
                {
                    "category": [
                        {"slug": "left", "label": "Left", "stimuli": [{"text": "alpha"}]},
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    repository = IatRepository(
        IatResourcesSettings(iats=(Path("resources/iats/bravo.yaml"), Path("resources/iats/alpha.yaml"))).resolve(
            tmp_path
        )
    )

    # When: the repository lists the published IATs.
    published_iats = repository.get_iats()

    # Then: the published IAT order follows the configured settings order.
    assert [published_iat.slug for published_iat in published_iats] == ["bravo", "alpha"]


def test_get_iat_returns_published_stimuli(tmp_path: Path) -> None:
    # Given: one configured IAT with one published image stimulus and text stimuli.
    resources_root = tmp_path / "resources"
    image_path = resources_root / "stimuli/face/example/images/seed-0.png"
    write_json(
        resources_root / "iats/sample-iat.yaml",
        {
            "slug": "sample-iat",
            "title": "Sample-Iat",
            "description": "sample-iat description.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "left",
                            "label": "Left",
                            "stimuli": [
                                {"image": "../stimuli/face/example/images/seed-0.png"},
                                {"text": "left"},
                            ],
                        },
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    write_png(image_path)
    repository = IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))

    # When: the repository returns the configured IAT by slug.
    published_iat = repository.get_iat("sample-iat")

    # Then: the published IAT contains one routed image path and the remaining text stimuli.
    assert published_iat is not None
    assert published_iat.slug == "sample-iat"
    assert published_iat.title == "Sample-Iat"
    assert published_iat.description == "sample-iat description."
    assert published_iat.categories[0][0].stimuli[0].text is None
    assert published_iat.categories[0][0].stimuli[0].image == _published_image_path("sample-iat", "left", image_path)
    assert published_iat.categories[0][0].stimuli[1].text == "left"
    assert published_iat.categories[0][0].stimuli[1].image is None
    assert published_iat.categories[0][1].stimuli[0].text == "right"
    assert published_iat.categories[1][0].stimuli[0].text == "up"
    assert published_iat.categories[1][1].stimuli[0].text == "down"


def test_get_iat_returns_none_for_unknown_slug(tmp_path: Path) -> None:
    # Given: one repository with one configured IAT.
    resources_root = tmp_path / "resources"
    write_json(
        resources_root / "iats/sample-iat.yaml",
        {
            "slug": "sample-iat",
            "title": "Sample-Iat",
            "description": "sample-iat description.",
            "categories": [
                {
                    "category": [
                        {"slug": "left", "label": "Left", "stimuli": [{"text": "sample"}]},
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    repository = IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))

    # When: the repository looks up one unavailable slug.
    published_iat = repository.get_iat("missing-iat")

    # Then: the unavailable slug returns no published IAT.
    assert published_iat is None


def test_get_stimuli_returns_published_source_path(tmp_path: Path) -> None:
    # Given: one configured IAT that publishes one image outside the shared stimuli directory.
    resources_root = tmp_path / "resources"
    source_image_path = resources_root / "private/seed-0.png"
    write_json(
        resources_root / "iats/sample-iat.yaml",
        {
            "slug": "sample-iat",
            "title": "Sample-Iat",
            "description": "sample-iat description.",
            "categories": [
                {
                    "category": [
                        {"slug": "left", "label": "Left", "stimuli": [{"image": "../private/seed-0.png"}]},
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    write_png(source_image_path)
    repository = IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))

    # When: the repository resolves the published image path.
    resolved_source_path = repository.get_stimuli(_published_image_path("sample-iat", "left", source_image_path))

    # Then: the repository returns the original source image path.
    assert resolved_source_path == source_image_path


def test_rejects_duplicate_iat_slugs(tmp_path: Path) -> None:
    # Given: two configured IAT files that declare the same slug.
    resources_root = tmp_path / "resources"
    write_json(
        resources_root / "iats/alpha.yaml",
        {
            "slug": "duplicate",
            "title": "Alpha",
            "description": "alpha description.",
            "categories": [
                {
                    "category": [
                        {"slug": "left", "label": "Left", "stimuli": [{"text": "alpha"}]},
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    write_json(
        resources_root / "iats/bravo.yaml",
        {
            "slug": "duplicate",
            "title": "Bravo",
            "description": "bravo description.",
            "categories": [
                {
                    "category": [
                        {"slug": "left", "label": "Left", "stimuli": [{"text": "bravo"}]},
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )

    # When: the repository loads the configured IAT files.
    # Then: duplicate configured IAT slugs are rejected.
    with pytest.raises(ValueError, match="IAT slugs must be unique across the configured repository"):
        IatRepository(
            IatResourcesSettings(iats=(Path("resources/iats/alpha.yaml"), Path("resources/iats/bravo.yaml"))).resolve(
                tmp_path
            )
        )


@pytest.mark.parametrize(
    "published_image",
    [
        pytest.param(PurePosixPath("missing/image.png"), id="unknown_image"),
        pytest.param(PurePosixPath("../iats/sample-iat.yaml"), id="path_traversal"),
        pytest.param(PurePosixPath("face/example/manifest.yaml"), id="unpublished_non_png_file"),
    ],
)
def test_get_stimuli_returns_none_for_unpublished_images(
    tmp_path: Path,
    published_image: PurePosixPath,
) -> None:
    # Given: one repository without a published image for the requested path.
    resources_root = tmp_path / "resources"
    manifest_path = resources_root / "stimuli/face/example/manifest.yaml"
    write_yaml(manifest_path, {"slug": "example"})
    repository = IatRepository(IatResourcesSettings(iats=()).resolve(tmp_path))

    # When: the repository resolves one unpublished image path.
    resolved_source_path = repository.get_stimuli(published_image)

    # Then: the unpublished image path is rejected.
    assert resolved_source_path is None


def test_reuses_published_path_for_same_image(tmp_path: Path) -> None:
    # Given: one category that references the same source image twice.
    resources_root = tmp_path / "resources"
    image_path = resources_root / "stimuli/face/example/images/seed-0.png"
    write_json(
        resources_root / "iats/sample-iat.yaml",
        {
            "slug": "sample-iat",
            "title": "Sample-Iat",
            "description": "sample-iat description.",
            "categories": [
                {
                    "category": [
                        {
                            "slug": "left",
                            "label": "Left",
                            "stimuli": [
                                {"image": "../stimuli/face/example/images/seed-0.png"},
                                {"image": "../stimuli/face/example/images/seed-0.png"},
                            ],
                        },
                        {"slug": "right", "label": "Right", "stimuli": [{"text": "right"}]},
                    ]
                },
                {
                    "category": [
                        {"slug": "up", "label": "Up", "stimuli": [{"text": "up"}]},
                        {"slug": "down", "label": "Down", "stimuli": [{"text": "down"}]},
                    ]
                },
            ],
        },
    )
    write_png(image_path)
    repository = IatRepository(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)).resolve(tmp_path))

    # When: the repository publishes the configured IAT.
    published_iat = repository.get_iat("sample-iat")

    # Then: the repeated source image gets the same published image key both times.
    assert published_iat is not None
    expected_image = _published_image_path("sample-iat", "left", image_path)
    assert published_iat.categories[0][0].stimuli[0].image == expected_image
    assert published_iat.categories[0][0].stimuli[1].image == expected_image
    assert repository.get_stimuli(expected_image) == image_path
