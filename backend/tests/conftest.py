"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.app.config import Settings
from backend.app.database import Base, create_db_session, get_engine
from backend.app.models import Category, Experiment, ExperimentVariant, Phase, Stimulus

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from fastapi import FastAPI


class TestSettings(Settings):
    """Test-specific application configuration."""

    model_config = Settings.model_config


@pytest.fixture
def app(tmp_path: Path) -> Generator[FastAPI]:
    """Create a test application backed by a temporary SQLite database."""
    resource_root = tmp_path / "resources"
    definitions_dir = resource_root / "iats"
    resource_root.mkdir(parents=True, exist_ok=True)
    definitions_dir.mkdir(parents=True, exist_ok=True)
    settings = TestSettings(
        SECRET_KEY=secrets.token_urlsafe(24),
        DATABASE_URL=f"sqlite:///{tmp_path / 'test.sqlite3'}",
        ASSETS_DIR=resource_root,
        DEFINITIONS_DIR=definitions_dir,
        PROJECT_IMPLICIT_ASSETS_DIR=resource_root / "project-implicit",
    )

    app = create_app(settings)

    yield app

    Base.metadata.drop_all(bind=get_engine(app))


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    """Create a FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_experiment(app: FastAPI) -> Experiment:
    """Insert a demo test definition for integration tests."""
    session = create_db_session(app)
    test = Experiment(
        slug="demo-iat",
        title="Demo IAT",
        description="Demo",
    )
    session.add(test)
    session.flush()

    baseline = ExperimentVariant(
        test_id=test.id,
        key_event_mode="keyup",
        preload_assets=False,
        inter_trial_interval_ms=250,
        response_timeout_ms=5000,
    )
    optimized = ExperimentVariant(
        test_id=test.id,
        key_event_mode="keydown",
        preload_assets=True,
        inter_trial_interval_ms=150,
        response_timeout_ms=5000,
    )
    session.add_all([baseline, optimized])
    session.flush()

    flowers = Category(test_id=test.id, code="flowers", label="Flowers")
    insects = Category(test_id=test.id, code="insects", label="Insects")
    pleasant = Category(test_id=test.id, code="pleasant", label="Pleasant")
    unpleasant = Category(test_id=test.id, code="unpleasant", label="Unpleasant")
    session.add_all([flowers, insects, pleasant, unpleasant])
    session.flush()

    session.add_all(
        [
            Stimulus(category_id=flowers.id, text_value="rose", asset_path=None),
            Stimulus(category_id=flowers.id, text_value=None, asset_path="/stimuli/flowers/rose.png"),
            Stimulus(category_id=insects.id, text_value="wasp", asset_path=None),
            Stimulus(category_id=pleasant.id, text_value="joy", asset_path=None),
            Stimulus(category_id=unpleasant.id, text_value="grief", asset_path=None),
        ]
    )

    session.add_all(
        [
            Phase(
                test_id=test.id,
                sequence_number=1,
                showings_per_category=1,
                left_primary_category_id=flowers.id,
                left_secondary_category_id=None,
                right_primary_category_id=insects.id,
                right_secondary_category_id=None,
            ),
            Phase(
                test_id=test.id,
                sequence_number=2,
                showings_per_category=1,
                left_primary_category_id=flowers.id,
                left_secondary_category_id=pleasant.id,
                right_primary_category_id=insects.id,
                right_secondary_category_id=unpleasant.id,
            ),
        ]
    )

    session.commit()
    session.close()
    return test
