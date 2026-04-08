"""Tests for YAML IAT config syncing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from backend.app.database import create_db_session
from backend.app.models import Experiment
from backend.app.services import load_definitions, sync_app_definitions, sync_definitions

if TYPE_CHECKING:
    from fastapi import FastAPI


EXPECTED_GENERATED_BLOCK_COUNT = 4


def test_sync_definitions_loads_text_and_image_experiments(app: FastAPI) -> None:
    """IAT configs should create runnable experiments and preserve image asset URLs."""
    settings = app.state.settings
    definitions_dir = settings.DEFINITIONS_DIR
    settings.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    image_dir = settings.ASSETS_DIR / "project-implicit" / "race-attitudes"
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / "bf14_nc.jpg").write_bytes(b"bf14")
    (image_dir / "wf2_nc.jpg").write_bytes(b"wf2")

    (definitions_dir / "demo.yaml").write_text(
        """
slug: demo-iat
title: Demo Implicit Association Test
description: Demo text-based IAT.
categories:
  - category:
      - slug: flowers
        label: Flowers
        stimuli:
          - text: rose
      - slug: insects
        label: Insects
        stimuli:
          - text: wasp
  - category:
      - slug: pleasant
        label: Pleasant
        stimuli:
          - text: joy
      - slug: unpleasant
        label: Unpleasant
        stimuli:
          - text: grief
""".strip(),
        encoding="utf-8",
    )
    (definitions_dir / "race.yaml").write_text(
        """
slug: race-attitudes
title: Race Attitudes IAT
description: Image-backed race attitude task.
categories:
  - category:
      - slug: black-faces
        label: Black Faces
        stimuli:
          - image: project-implicit/race-attitudes/bf14_nc.jpg
      - slug: white-faces
        label: White Faces
        stimuli:
          - image: project-implicit/race-attitudes/wf2_nc.jpg
  - category:
      - slug: pleasant
        label: Pleasant
        stimuli:
          - text: joy
      - slug: unpleasant
        label: Unpleasant
        stimuli:
          - text: grief
""".strip(),
        encoding="utf-8",
    )

    definitions = load_definitions(definitions_dir)
    db_session = create_db_session(app)
    try:
        sync_definitions(db_session, definitions)
        db_session.commit()
        tests = db_session.execute(select(Experiment).order_by(Experiment.slug)).scalars().all()
        if [test.slug for test in tests] != ["demo-iat", "race-attitudes"]:
            msg = "Expected YAML sync to create both tests."
            raise AssertionError(msg)
        image_stimuli = [
            stimulus
            for category in tests[1].categories
            for stimulus in category.stimuli
            if stimulus.asset_path is not None
        ]
        if [stimulus.asset_path for stimulus in image_stimuli] != [
            "/assets/project-implicit/race-attitudes/bf14_nc.jpg",
            "/assets/project-implicit/race-attitudes/wf2_nc.jpg",
        ]:
            msg = "Expected image stimuli to be exposed under the /assets mount."
            raise AssertionError(msg)
        if len(tests[1].phases) != EXPECTED_GENERATED_BLOCK_COUNT:
            msg = "Expected the software to generate the standard four runnable phases from the dataset config."
            raise AssertionError(msg)
    finally:
        db_session.close()


def test_sync_definitions_rejects_missing_local_asset_files(app: FastAPI) -> None:
    """IAT configs should reject image stimuli that do not exist under the resource root."""
    settings = app.state.settings
    definitions_dir = settings.DEFINITIONS_DIR

    (definitions_dir / "broken.yaml").write_text(
        """
slug: broken-image
title: Broken Image IAT
description: Broken image reference.
categories:
  - category:
      - slug: faces
        label: Faces
        stimuli:
          - image: project-implicit/missing/file.jpg
      - slug: places
        label: Places
        stimuli:
          - text: town
  - category:
      - slug: good
        label: Good
        stimuli:
          - text: joy
      - slug: bad
        label: Bad
        stimuli:
          - text: grief
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"image paths must point to an existing file\."):
        load_definitions(definitions_dir)


def test_sync_app_definitions_returns_none_and_persists_results(app: FastAPI) -> None:
    """The app sync helper should log status instead of returning status text."""
    definitions_dir = app.state.settings.DEFINITIONS_DIR
    (definitions_dir / "demo.yaml").write_text(
        """
slug: demo-iat
title: Demo Implicit Association Test
description: Demo text-based IAT.
categories:
  - category:
      - slug: flowers
        label: Flowers
        stimuli:
          - text: rose
      - slug: insects
        label: Insects
        stimuli:
          - text: wasp
  - category:
      - slug: pleasant
        label: Pleasant
        stimuli:
          - text: joy
      - slug: unpleasant
        label: Unpleasant
        stimuli:
          - text: grief
""".strip(),
        encoding="utf-8",
    )

    result = sync_app_definitions(app)
    if result is not None:
        msg = "Expected app sync helper to log status instead of returning it."
        raise AssertionError(msg)

    db_session = create_db_session(app)
    try:
        test = db_session.execute(select(Experiment).where(Experiment.slug == "demo-iat")).scalar_one_or_none()
        if test is None:
            msg = "Expected app sync helper to persist test definitions."
            raise AssertionError(msg)
    finally:
        db_session.close()


def test_sync_definitions_deletes_removed_yaml_tests_without_attempts(app: FastAPI) -> None:
    """Removing a YAML definition should remove the matching test when it has no attempts."""
    db_session = create_db_session(app)
    try:
        db_session.add(Experiment(slug="obsolete-iat", title="Obsolete", description="Old"))
        db_session.commit()

        results = sync_definitions(db_session, [])
        if results != [type(results[0])(slug="obsolete-iat", action="deleted")]:
            msg = "Expected sync to report deleted tests when YAML definitions are removed."
            raise AssertionError(msg)

        test = db_session.execute(select(Experiment).where(Experiment.slug == "obsolete-iat")).scalar_one_or_none()
        if test is not None:
            msg = "Expected sync to remove tests that are no longer defined."
            raise AssertionError(msg)
    finally:
        db_session.close()
