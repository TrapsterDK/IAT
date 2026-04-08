"""Load and synchronize IAT YAML definitions into the relational model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from loguru import logger
from sqlalchemy import delete, select

from backend.app.config import CategoryConfig, IatDefinitionConfig, load_iat_config
from backend.app.database import create_db_session
from backend.app.models import (
    Attempt,
    Category,
    Experiment,
    ExperimentVariant,
    KeyEventMode,
    Phase,
    Stimulus,
)

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi import FastAPI
    from sqlalchemy.orm import Session as DBSession


DEFAULT_VARIANT_ROWS = [
    (KeyEventMode.KEYUP, False, 250, 5000),
    (KeyEventMode.KEYDOWN, True, 150, 5000),
]


@dataclass(frozen=True)
class DefinitionSyncResult:
    """One definition synchronization outcome."""

    slug: str
    action: Literal["created", "updated", "unchanged", "deleted"]


def _test_has_attempts(db_session: DBSession, test_id: int) -> bool:
    return (
        db_session.execute(
            select(Attempt.id).join(ExperimentVariant).where(ExperimentVariant.test_id == test_id).limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _delete_missing_definitions(
    db_session: DBSession,
    definitions: list[IatDefinitionConfig],
) -> list[DefinitionSyncResult]:
    defined_slugs = {definition.slug for definition in definitions}
    existing_tests = db_session.execute(select(Experiment).order_by(Experiment.slug)).scalars().all()
    deleted_results: list[DefinitionSyncResult] = []

    for test in existing_tests:
        if test.slug in defined_slugs:
            continue
        if _test_has_attempts(db_session, test.id):
            msg = f"Test {test.slug} already has attempts and cannot be removed from definitions."
            raise ValueError(msg)
        db_session.delete(test)
        deleted_results.append(DefinitionSyncResult(slug=test.slug, action="deleted"))

    return deleted_results


def _asset_url(relative_path: str) -> str:
    return f"/assets/{relative_path}"


def _category_rows(definition: IatDefinitionConfig) -> list[tuple[str, str, int, CategoryConfig]]:
    target_left, target_right = definition.categories[0].category
    attribute_left, attribute_right = definition.categories[1].category

    return [
        (target_left.slug, target_left.label, 1, target_left),
        (target_right.slug, target_right.label, 2, target_right),
        (attribute_left.slug, attribute_left.label, 3, attribute_left),
        (attribute_right.slug, attribute_right.label, 4, attribute_right),
    ]


def _flatten_stimuli(definition: IatDefinitionConfig) -> list[tuple[str, str | None, str | None]]:
    rows: list[tuple[str, str | None, str | None]] = []
    for code, _label, _position, category in _category_rows(definition):
        rows.extend(
            (
                code,
                stimulus.text,
                _asset_url(stimulus.image.as_posix()) if stimulus.image else None,
            )
            for stimulus in category.stimuli
        )
    return rows


def _generated_phases(
    definition: IatDefinitionConfig,
) -> list[tuple[int, int, str, str | None, str, str | None]]:
    target_left, target_right = definition.categories[0].category
    attribute_left, attribute_right = definition.categories[1].category

    return [
        (
            1,
            4,
            target_left.slug,
            None,
            target_right.slug,
            None,
        ),
        (
            2,
            4,
            attribute_left.slug,
            None,
            attribute_right.slug,
            None,
        ),
        (
            3,
            4,
            target_left.slug,
            attribute_left.slug,
            target_right.slug,
            attribute_right.slug,
        ),
        (
            4,
            4,
            target_left.slug,
            attribute_right.slug,
            target_right.slug,
            attribute_left.slug,
        ),
    ]


def _definition_metadata_changed(existing: Experiment, definition: IatDefinitionConfig) -> bool:
    return existing.title != definition.title or existing.description != definition.description


def _definition_structure_changed(existing: Experiment, definition: IatDefinitionConfig) -> bool:
    existing_variants = [
        (
            variant.key_event_mode,
            variant.preload_assets,
            variant.inter_trial_interval_ms,
            variant.response_timeout_ms,
        )
        for variant in sorted(existing.variants, key=lambda item: item.id)
    ]
    if existing_variants != DEFAULT_VARIANT_ROWS:
        return True

    existing_categories = [
        (category.code, category.label) for category in sorted(existing.categories, key=lambda item: item.id)
    ]
    definition_categories = [(code, label) for code, label, _position, _category in _category_rows(definition)]
    if existing_categories != definition_categories:
        return True

    existing_stimuli = [
        (stimulus.category.code, stimulus.text_value, stimulus.asset_path)
        for category in sorted(existing.categories, key=lambda item: item.id)
        for stimulus in sorted(category.stimuli, key=lambda item: item.id)
    ]
    if existing_stimuli != _flatten_stimuli(definition):
        return True

    existing_phases = [
        (
            phase.sequence_number,
            phase.showings_per_category,
            phase.left_primary_category.code,
            phase.left_secondary_category.code if phase.left_secondary_category is not None else None,
            phase.right_primary_category.code,
            phase.right_secondary_category.code if phase.right_secondary_category is not None else None,
        )
        for phase in existing.phases
    ]
    return existing_phases != _generated_phases(definition)


def _apply_definition_metadata(test: Experiment, definition: IatDefinitionConfig) -> None:
    test.title = definition.title
    test.description = definition.description


def _replace_test_contents(db_session: DBSession, test: Experiment, definition: IatDefinitionConfig) -> None:
    db_session.execute(delete(ExperimentVariant).where(ExperimentVariant.test_id == test.id))
    db_session.execute(delete(Phase).where(Phase.test_id == test.id))
    db_session.execute(
        delete(Stimulus).where(Stimulus.category_id.in_(select(Category.id).where(Category.test_id == test.id)))
    )
    db_session.execute(delete(Category).where(Category.test_id == test.id))
    db_session.flush()

    _apply_definition_metadata(test, definition)
    db_session.flush()

    for variant in DEFAULT_VARIANT_ROWS:
        key_event_mode, preload_assets, inter_trial_interval_ms, response_timeout_ms = variant
        db_session.add(
            ExperimentVariant(
                test_id=test.id,
                key_event_mode=key_event_mode,
                preload_assets=preload_assets,
                inter_trial_interval_ms=inter_trial_interval_ms,
                response_timeout_ms=response_timeout_ms,
            )
        )
    db_session.flush()

    category_by_code: dict[str, Category] = {}
    for code, label, _position, _category in _category_rows(definition):
        category_record = Category(test_id=test.id, code=code, label=label)
        db_session.add(category_record)
        db_session.flush()
        category_by_code[code] = category_record

    for code, _label, _position, category in _category_rows(definition):
        for stimulus in category.stimuli:
            db_session.add(
                Stimulus(
                    category_id=category_by_code[code].id,
                    text_value=stimulus.text,
                    asset_path=_asset_url(stimulus.image.as_posix()) if stimulus.image else None,
                )
            )

    for phase_row in _generated_phases(definition):
        (
            sequence_number,
            showings_per_category,
            left_primary,
            left_secondary,
            right_primary,
            right_secondary,
        ) = phase_row
        db_session.add(
            Phase(
                test_id=test.id,
                sequence_number=sequence_number,
                showings_per_category=showings_per_category,
                left_primary_category_id=category_by_code[left_primary].id,
                left_secondary_category_id=(
                    category_by_code[left_secondary].id if left_secondary is not None else None
                ),
                right_primary_category_id=category_by_code[right_primary].id,
                right_secondary_category_id=(
                    category_by_code[right_secondary].id if right_secondary is not None else None
                ),
            )
        )


def sync_definition(db_session: DBSession, definition: IatDefinitionConfig) -> DefinitionSyncResult:
    """Synchronize one IAT config into the relational database."""
    statement = select(Experiment).where(Experiment.slug == definition.slug)
    test = db_session.execute(statement).scalar_one_or_none()

    if test is None:
        test = Experiment(
            slug=definition.slug,
            title=definition.title,
            description=definition.description,
        )
        db_session.add(test)
        db_session.flush()
        _replace_test_contents(db_session, test, definition)
        return DefinitionSyncResult(slug=definition.slug, action="created")

    metadata_changed = _definition_metadata_changed(test, definition)
    structure_changed = _definition_structure_changed(test, definition)

    if not metadata_changed and not structure_changed:
        return DefinitionSyncResult(slug=definition.slug, action="unchanged")

    if structure_changed:
        if _test_has_attempts(db_session, test.id):
            msg = f"Test {definition.slug} already has attempts and cannot change structure."
            raise ValueError(msg)
        _replace_test_contents(db_session, test, definition)
        return DefinitionSyncResult(slug=definition.slug, action="updated")

    _apply_definition_metadata(test, definition)
    return DefinitionSyncResult(slug=definition.slug, action="updated")


def load_definitions(definitions_dir: Path) -> list[IatDefinitionConfig]:
    """Load all YAML IAT definitions from the configured directory."""
    return [load_iat_config(path) for path in sorted(definitions_dir.glob("*.yaml"))]


def sync_definitions(db_session: DBSession, definitions: list[IatDefinitionConfig]) -> list[DefinitionSyncResult]:
    """Synchronize a list of YAML definitions into the database."""
    results = _delete_missing_definitions(db_session, definitions)
    results.extend(sync_definition(db_session, definition) for definition in definitions)
    db_session.commit()
    return results


def sync_app_definitions(app: FastAPI) -> None:
    """Load the app's configured IAT definitions and sync them into the database."""
    settings = app.state.settings
    definitions = load_definitions(settings.DEFINITIONS_DIR)
    db_session = create_db_session(app)
    try:
        results = sync_definitions(db_session, definitions)
        for result in results:
            logger.info("Definition {} {}", result.slug, result.action)
    finally:
        db_session.close()
