"""Tests for backend catalog service lookups."""

from __future__ import annotations

from pathlib import Path

from apps.backend.repositories.catalog import CatalogRepository
from apps.backend.services.catalog import CatalogService
from apps.backend.settings import IatResourcesSettings
from libs.testing.io import write_json, write_png


def _build_catalog_service(settings: IatResourcesSettings, tmp_path: Path) -> CatalogService:
    resolved_settings = settings.resolve(tmp_path)
    catalog_repository = CatalogRepository(resolved_settings)
    return CatalogService(catalog_repository)


def test_get_iat_returns_published_iat(tmp_path: Path) -> None:
    # Given: one IAT spec that references one PNG below the configured stimuli root.
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
    service = _build_catalog_service(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)), tmp_path)

    # When: the service resolves one configured IAT.
    resolved_iat = service.get_iat("sample-iat")

    # Then: the service returns the published IAT model from the repository boundary.
    assert resolved_iat is not None
    assert resolved_iat.slug == "sample-iat"
    assert resolved_iat.categories[0][0].stimuli[0].text is None
    assert resolved_iat.categories[0][0].stimuli[0].image_path is not None


def test_list_iats_returns_published_iats(tmp_path: Path) -> None:
    # Given: one configured IAT in the repository.
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
                        {
                            "slug": "alpha",
                            "label": "Alpha",
                            "stimuli": [{"text": "alpha"}],
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
    service = _build_catalog_service(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)), tmp_path)

    # When: the service lists the available IATs.
    iat_summaries = service.get_iats()

    # Then: the service returns published IAT models.
    assert [iat_summary.slug for iat_summary in iat_summaries] == ["sample-iat"]


def test_get_stimulus_returns_published_source_path(tmp_path: Path) -> None:
    # Given: one configured IAT in the repository.
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
    service = _build_catalog_service(IatResourcesSettings(iats=(Path("resources/iats/sample-iat.yaml"),)), tmp_path)

    # When: the service resolves one published stimulus path.
    published_iat = service.get_iat("sample-iat")
    assert published_iat is not None
    published_image = published_iat.categories[0][0].stimuli[0].image_path
    assert published_image is not None
    resolved_source_path = service.get_stimulus(published_image)

    # Then: the service returns the original source path.
    assert resolved_source_path == image_path
