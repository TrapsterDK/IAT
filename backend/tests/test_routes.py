"""Integration tests for API route behavior."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, NoReturn, TypeGuard

from sqlalchemy import select

from backend.app.database import create_db_session
from backend.app.models import Attempt, Experiment, Showing, ShowingInput

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

type JSONPrimitive = str | int | float | bool | None
type JSONValue = JSONPrimitive | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
type ShowingObjectList = list[dict[str, object]]

EXPECTED_SHOWING_COUNT = 6
EXPECTED_PHASE_COUNT = 2
EXPECTED_LEFT_CATEGORY_COUNT = 2
DEFAULT_ENVIRONMENT = {
    "userAgent": "pytest",
    "platform": "linux",
    "language": "en-US",
    "viewportWidth": 1280,
    "viewportHeight": 720,
    "devicePixelRatio": 1,
    "visibilityInterruptions": 0,
}


def _fail(message: str) -> NoReturn:
    raise TypeError(message)


def _is_json_value(value: object) -> TypeGuard[JSONValue]:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _is_json_object(value: object) -> TypeGuard[JSONObject]:
    return isinstance(value, dict) and all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())


def _require_json_object(value: object, context: str) -> JSONObject:
    if not _is_json_object(value):
        _fail(f"Expected {context} to be a JSON object.")
    return value


def _is_showing_object_list(value: object) -> TypeGuard[ShowingObjectList]:
    return isinstance(value, list) and all(isinstance(showing, dict) for showing in value)


def _create_attempt_payload(client: TestClient) -> JSONObject:
    response = client.post("/api/tests/demo-iat/attempts")
    if response.status_code != HTTPStatus.CREATED:
        raise AssertionError("Expected attempt creation to return HTTP 201.")
    return _require_json_object(response.json(), "attempt payload")


def _showing_list(payload: dict[str, object]) -> ShowingObjectList:
    showings = payload.get("showings")
    if not _is_showing_object_list(showings):
        _fail("Expected completion payload showings to be JSON objects.")
    return showings


def _build_completion_payload(payload: JSONObject) -> dict[str, object]:
    attempt_payload = _require_json_object(payload.get("attempt"), "attempt payload")
    phases = payload.get("phases")
    if not isinstance(phases, list):
        _fail("Expected phases in test payload.")

    stimuli_by_category = payload.get("stimuliByCategory")
    if not isinstance(stimuli_by_category, dict):
        _fail("Expected stimuliByCategory in test payload.")

    attempt_token = attempt_payload.get("attemptToken")
    if not isinstance(attempt_token, str) or not attempt_token:
        _fail("Expected attempt token in test payload.")

    showings: list[dict[str, object]] = []
    for phase_index, raw_phase in enumerate(phases):
        phase = _require_json_object(raw_phase, f"phase {phase_index}")
        phase_id = phase.get("id")
        showings_per_category = phase.get("showingsPerCategory")
        categories = _require_json_object(phase.get("categories"), f"phase {phase_index} categories")
        if not isinstance(phase_id, int) or not isinstance(showings_per_category, int):
            _fail("Expected phase id and showingsPerCategory in test payload.")

        showing_index = 0
        for side in ("left", "right"):
            raw_categories = categories.get(side)
            if not isinstance(raw_categories, list):
                _fail(f"Expected {side} categories in phase payload.")
            for raw_category in raw_categories:
                category = _require_json_object(raw_category, f"{side} category")
                category_id = category.get("id")
                if not isinstance(category_id, int):
                    _fail("Expected category id in phase payload.")
                raw_stimuli = stimuli_by_category.get(str(category_id))
                if not isinstance(raw_stimuli, list) or not raw_stimuli:
                    _fail("Expected stimuli for every category in test payload.")
                for offset in range(showings_per_category):
                    raw_stimulus = _require_json_object(raw_stimuli[offset % len(raw_stimuli)], "stimulus")
                    stimulus_id = raw_stimulus.get("id")
                    if not isinstance(stimulus_id, int):
                        _fail("Expected stimulus id in test payload.")
                    showings.append(
                        {
                            "phaseId": phase_id,
                            "stimulusId": stimulus_id,
                            "showingIndex": showing_index,
                            "stimulusOnsetMs": 100.5 + showing_index,
                            "inputs": [
                                {
                                    "inputIndex": 0,
                                    "side": side,
                                    "inputSource": "keyboard",
                                    "eventTimestampMs": 550.5 + showing_index,
                                    "handlerTimestampMs": 550.75 + showing_index,
                                }
                            ],
                        }
                    )
                    showing_index += 1

    return {"attemptToken": attempt_token, "environment": dict(DEFAULT_ENVIRONMENT), "showings": showings}


def test_list_tests_returns_seeded_test(client: TestClient, seeded_experiment: Experiment) -> None:
    """The test list endpoint should expose available tests."""
    del seeded_experiment
    response = client.get("/api/tests")

    if response.status_code != HTTPStatus.OK:
        raise AssertionError("Expected the tests endpoint to return successfully.")
    payload = _require_json_object(response.json(), "tests payload")
    tests = payload.get("tests")
    if not isinstance(tests, list) or not tests:
        raise AssertionError("Expected at least one test in the listing payload.")


def test_create_attempt_returns_attempt_payload(
    app: FastAPI, client: TestClient, seeded_experiment: Experiment
) -> None:
    """Creating an attempt should return the SPA bootstrap payload."""
    del seeded_experiment
    response = client.post("/api/tests/demo-iat/attempts")

    if response.status_code != HTTPStatus.CREATED:
        raise AssertionError("Expected attempt creation to return HTTP 201.")

    payload = _require_json_object(response.json(), "attempt payload")
    test_payload = _require_json_object(payload.get("test"), "test payload")
    attempt_payload = _require_json_object(payload.get("attempt"), "attempt payload")

    if test_payload.get("slug") != "demo-iat":
        raise AssertionError("Expected the created attempt payload to reference the seeded test.")
    public_id = attempt_payload.get("publicId")
    if not isinstance(public_id, str) or not public_id:
        raise AssertionError("Expected a non-empty public attempt id in the payload.")

    db_session = create_db_session(app)
    try:
        created_attempt = db_session.execute(select(Attempt).where(Attempt.public_id == public_id)).scalar_one_or_none()
        if created_attempt is not None:
            raise AssertionError("Expected attempt creation to remain stateless until completion submission.")
    finally:
        db_session.close()


def test_complete_attempt_persists_relational_showings(
    app: FastAPI,
    client: TestClient,
    seeded_experiment: Experiment,
) -> None:
    """Completing an attempt should persist relational showing rows."""
    del seeded_experiment
    attempt_payload = _create_attempt_payload(client)
    public_id = _require_json_object(attempt_payload.get("attempt"), "attempt payload").get("publicId")
    if not isinstance(public_id, str):
        _fail("Expected publicId in attempt payload.")
    response = client.post(f"/api/attempts/{public_id}/complete", json=_build_completion_payload(attempt_payload))

    if response.status_code != HTTPStatus.OK:
        raise AssertionError("Expected attempt completion to succeed.")

    completion_payload = _require_json_object(response.json(), "completion payload")
    summary = _require_json_object(completion_payload.get("summary"), "completion summary")
    if summary.get("showingCount") != EXPECTED_SHOWING_COUNT:
        raise AssertionError("Expected the completion summary to report every stored showing.")

    db_session = create_db_session(app)
    try:
        stored_showings = db_session.execute(select(Showing)).scalars().all()
        stored_inputs = db_session.execute(select(ShowingInput)).scalars().all()
        if len(stored_showings) != EXPECTED_SHOWING_COUNT:
            raise AssertionError("Expected every showing row to be persisted.")
        if len(stored_inputs) != EXPECTED_SHOWING_COUNT:
            raise AssertionError("Expected one input row for every stored showing in the fixture payload.")
    finally:
        db_session.close()


def test_complete_attempt_rejects_stimulus_not_used_in_phase(client: TestClient, seeded_experiment: Experiment) -> None:
    """Completion should reject stimuli that do not belong to the submitted phase."""
    del seeded_experiment
    attempt_payload = _create_attempt_payload(client)
    run_payload = _require_json_object(attempt_payload.get("attempt"), "attempt payload")
    public_id = run_payload.get("publicId")
    if not isinstance(public_id, str):
        _fail("Expected publicId in attempt payload.")

    payload = _build_completion_payload(attempt_payload)
    showings = _showing_list(payload)
    first_showing = showings[0]

    phases = attempt_payload.get("phases")
    if not isinstance(phases, list) or len(phases) < EXPECTED_PHASE_COUNT:
        _fail("Expected at least two phases in attempt payload.")
    second_phase = _require_json_object(phases[1], "second phase")
    categories = _require_json_object(second_phase.get("categories"), "second phase categories")
    left_categories = categories.get("left")
    if not isinstance(left_categories, list) or len(left_categories) < EXPECTED_LEFT_CATEGORY_COUNT:
        _fail("Expected two left categories in second phase.")
    invalid_category = _require_json_object(left_categories[1], "secondary left category")
    invalid_category_id = invalid_category.get("id")
    if not isinstance(invalid_category_id, int):
        _fail("Expected category id in secondary left category.")
    stimuli_by_category = attempt_payload.get("stimuliByCategory")
    if not isinstance(stimuli_by_category, dict):
        _fail("Expected stimuliByCategory in attempt payload.")
    invalid_stimuli = stimuli_by_category.get(str(invalid_category_id))
    if not isinstance(invalid_stimuli, list) or not invalid_stimuli:
        _fail("Expected stimuli for invalid category.")
    invalid_stimulus = _require_json_object(invalid_stimuli[0], "invalid stimulus")
    invalid_stimulus_id = invalid_stimulus.get("id")
    if not isinstance(invalid_stimulus_id, int):
        _fail("Expected stimulus id in invalid stimulus.")

    first_showing["stimulusId"] = invalid_stimulus_id

    response = client.post(f"/api/attempts/{public_id}/complete", json=payload)

    if response.status_code != HTTPStatus.BAD_REQUEST:
        raise AssertionError("Expected invalid phase/stimulus combinations to be rejected.")


def test_complete_attempt_rejects_incomplete_showing_sets(client: TestClient, seeded_experiment: Experiment) -> None:
    """Completion should require every configured showing exactly once."""
    del seeded_experiment
    attempt_payload = _create_attempt_payload(client)
    run_payload = _require_json_object(attempt_payload.get("attempt"), "attempt payload")
    public_id = run_payload.get("publicId")
    if not isinstance(public_id, str):
        _fail("Expected publicId in attempt payload.")
    payload = _build_completion_payload(attempt_payload)
    showings = _showing_list(payload)
    showings.pop()

    response = client.post(f"/api/attempts/{public_id}/complete", json=payload)

    if response.status_code != HTTPStatus.BAD_REQUEST:
        raise AssertionError("Expected incomplete completion payloads to be rejected.")


def test_complete_attempt_is_idempotent_after_completion(
    app: FastAPI,
    client: TestClient,
    seeded_experiment: Experiment,
) -> None:
    """Completion retries should return the stored summary instead of duplicating showings."""
    del seeded_experiment
    attempt_payload = _create_attempt_payload(client)
    run_payload = _require_json_object(attempt_payload.get("attempt"), "attempt payload")
    public_id = run_payload.get("publicId")
    if not isinstance(public_id, str):
        _fail("Expected publicId in attempt payload.")
    payload = _build_completion_payload(attempt_payload)

    first_response = client.post(f"/api/attempts/{public_id}/complete", json=payload)
    second_response = client.post(f"/api/attempts/{public_id}/complete", json=payload)

    if first_response.status_code != HTTPStatus.OK or second_response.status_code != HTTPStatus.OK:
        raise AssertionError("Expected repeated completion submissions to succeed idempotently.")

    first_summary = _require_json_object(
        _require_json_object(first_response.json(), "first response").get("summary"),
        "first summary",
    )
    second_summary = _require_json_object(
        _require_json_object(second_response.json(), "second response").get("summary"),
        "second summary",
    )
    if first_summary != second_summary:
        raise AssertionError("Expected repeated completion submissions to return the same summary.")

    db_session = create_db_session(app)
    try:
        stored_showings = db_session.execute(select(Showing)).scalars().all()
        if len(stored_showings) != EXPECTED_SHOWING_COUNT:
            raise AssertionError("Expected repeated completion submissions not to duplicate stored showings.")
    finally:
        db_session.close()


def test_missing_test_returns_api_error_payload(client: TestClient) -> None:
    """Missing tests should return the documented API error shape."""
    response = client.post("/api/tests/does-not-exist/attempts")

    if response.status_code != HTTPStatus.NOT_FOUND:
        raise AssertionError("Expected missing tests to return HTTP 404.")

    payload = _require_json_object(response.json(), "missing test payload")
    if payload.get("error") != "Test not found.":
        raise AssertionError("Expected missing tests to return the standardized error payload.")
