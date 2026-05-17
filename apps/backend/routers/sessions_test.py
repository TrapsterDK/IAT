"""Tests for backend session routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from sqlalchemy import select

from apps.backend.domain.session.models import TrialEventType
from apps.backend.models.session import SessionBootstrapResponse
from apps.backend.repositories.session.schema import SessionRecord, SessionTrialEventRecord

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_create_session_returns_minimal_bootstrap(session_client: TestClient) -> None:
    # Given: one backend app with one published text-only IAT and one empty session store.

    # When: one participant starts a session.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})

    # Then: the bootstrap returns the deterministic plan with the minimal public contract.
    assert created_response.status_code == 201
    created_payload = created_response.json()
    created_session = SessionBootstrapResponse.model_validate(created_payload)
    first_block = created_session.blocks[0]

    assert created_session.session_key
    assert created_session.anticipation_threshold_ms < created_session.response_timeout_ms
    assert [block.is_practice for block in created_session.blocks] == [True, True, True, False, True, True, False]
    assert first_block.left_labels == ("Alpha",)
    assert first_block.right_labels == ("Beta",)
    assert [len(block.trials) for block in created_session.blocks] == [2, 2, 4, 4, 2, 4, 4]
    assert first_block.is_practice is True
    assert {trial.stimulus.text for trial in first_block.trials} == {"alpha", "beta"}


def test_create_session_returns_public_stimulus_urls_for_image_trials(image_session_client: TestClient) -> None:
    # Given: one backend app with one published image-backed IAT and one empty session store.

    # When: one participant starts a session.
    created_response = image_session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})

    # Then: image-backed trials expose one routed public stimulus URL.
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())
    image_trials = [trial for trial in created_session.blocks[0].trials if trial.stimulus.image_url is not None]

    assert image_trials
    first_image_url = image_trials[0].stimulus.image_url
    assert first_image_url is not None
    assert first_image_url.startswith("/api/stimuli/sample-iat/alpha/")


def test_create_session_returns_not_found_for_unknown_iat_slug(session_client: TestClient) -> None:
    # Given: one session-creation payload that references one unavailable IAT slug.

    # When: the client creates one session.
    response = session_client.post("/api/sessions", json={"iat_slug": "missing-iat"})

    # Then: the route reports the IAT as unavailable.
    assert response.status_code == 404
    assert response.json() == {"detail": "IAT not found."}


def test_create_session_returns_server_error_for_invalid_iat_configuration(
    duplicate_label_session_client: TestClient,
) -> None:
    # Given: one backend app whose published IAT cannot produce one valid session run plan.

    # When: one participant starts a session.
    response = duplicate_label_session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})

    # Then: the route returns one generic server error for the invalid IAT configuration.
    assert response.status_code == 500
    assert response.json() == {"detail": "IAT configuration is invalid."}


@pytest.mark.parametrize(
    ("payload", "expected_fragment"),
    [
        pytest.param({}, "iat_slug", id="missing_iat_slug"),
        pytest.param({"iat_slug": "", "client_context": None}, "at least 1 character", id="blank_iat_slug"),
    ],
)
def test_create_session_rejects_invalid_payloads(
    session_client: TestClient,
    payload: dict[str, object],
    expected_fragment: str,
) -> None:
    # Given: one invalid session-creation payload.

    # When: the client creates one session.
    response = session_client.post("/api/sessions", json=payload)

    # Then: request validation rejects the payload.
    assert response.status_code == 422
    assert expected_fragment in str(response.json())


def test_upload_block_returns_not_found_for_unknown_session_key(session_client: TestClient) -> None:
    # Given: one unknown public session key and one block upload payload.

    # When: the client uploads one deterministic block.
    response = session_client.put(
        "/api/sessions/missing-session/blocks/1",
        json={"trials": [{"events": [{"event_type": "right", "elapsed_ms": 350}]}]},
    )

    # Then: the route reports the session as missing.
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


@pytest.mark.parametrize(
    "block_index",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
    ],
)
def test_upload_block_rejects_non_positive_block_index(
    session_client: TestClient,
    block_index: int,
) -> None:
    # Given: one running session and one syntactically valid block payload.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    # When: the client uploads one block using one non-positive block index.
    response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/{block_index}",
        json={"trials": [{"events": [{"event_type": "right", "elapsed_ms": 350}]}]},
    )

    # Then: request validation rejects the invalid path parameter.
    assert response.status_code == 422
    assert "greater than or equal to 1" in str(response.json())


def test_upload_block_rejects_out_of_order_block_index(session_client: TestClient) -> None:
    # Given: one running session whose next uploadable block is the first block.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    # When: the client uploads one later block out of deterministic order.
    response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/2",
        json={"trials": [{"events": [{"event_type": "right", "elapsed_ms": 350}]}]},
    )

    # Then: the route reports the block-order conflict.
    assert response.status_code == 409
    assert response.json() == {"detail": "The block upload could not be committed because the session state is invalid."}


def test_upload_block_rejects_out_of_range_positive_block_index(session_client: TestClient) -> None:
    # Given: one running session and one syntactically valid block payload.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    # When: the client uploads one block index beyond the deterministic run plan.
    response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/999",
        json={"trials": [{"events": [{"event_type": "right", "elapsed_ms": 350}]}]},
    )

    # Then: the route rejects the out-of-range block index as invalid input.
    assert response.status_code == 422
    assert response.json() == {"detail": "The block upload payload is invalid."}


def test_upload_block_returns_no_content_for_successful_upload(session_client: TestClient) -> None:
    # Given: one running session and one complete upload for the first deterministic block.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())
    first_block = created_session.blocks[0]
    first_block_trial_payloads = [
        {
            "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
        }
        for trial in first_block.trials
    ]

    # When: the client uploads every trial in the first block.
    upload_response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/1",
        json={"trials": first_block_trial_payloads},
    )

    # Then: the upload succeeds without a response body.
    assert upload_response.status_code == 204
    assert upload_response.content == b""


def test_upload_block_rejects_partial_block_payload(session_client: TestClient) -> None:
    # Given: one running session and one deterministic first block with multiple trials.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())
    first_block = created_session.blocks[0]
    full_trial_payloads = [
        {
            "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
        }
        for trial in first_block.trials
    ]

    # When: the client uploads only one prefix of the full deterministic block.
    response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/1",
        json={"trials": full_trial_payloads[:1]},
    )

    # Then: the route rejects uploads that do not include the full block.
    assert response.status_code == 422
    assert response.json() == {"detail": "The block upload payload is invalid."}


def test_upload_block_completes_session_after_final_block(session_client: TestClient) -> None:
    # Given: one running session and one deterministic run plan.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    for block_index, block in enumerate(created_session.blocks[:-1], start=1):
        block_trial_payloads = [
            {
                "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
            }
            for trial in block.trials
        ]
        prior_upload_response = session_client.put(
            f"/api/sessions/{created_session.session_key}/blocks/{block_index}",
            json={"trials": block_trial_payloads},
        )
        assert prior_upload_response.status_code == 204

    final_block = created_session.blocks[-1]
    final_block_index = len(created_session.blocks)
    final_block_trial_payloads = [
        {
            "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
        }
        for trial in final_block.trials
    ]

    # When: the client uploads every trial in the final block.
    final_upload_response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/{final_block_index}",
        json={"trials": final_block_trial_payloads},
    )
    follow_up_response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/{final_block_index}",
        json={"trials": final_block_trial_payloads},
    )

    # Then: the final upload succeeds and the session rejects any later uploads as completed.
    assert final_upload_response.status_code == 204
    assert final_upload_response.content == b""
    assert follow_up_response.status_code == 409
    assert follow_up_response.json() == {
        "detail": "The block upload could not be committed because the session state is invalid."
    }


def test_upload_block_rejects_reupload_of_committed_block(session_client: TestClient) -> None:
    # Given: one running session with one already committed first block.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())
    first_block = created_session.blocks[0]
    first_block_trial_payloads = [
        {
            "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
        }
        for trial in first_block.trials
    ]
    first_upload_response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/1",
        json={"trials": first_block_trial_payloads},
    )

    # When: the client reuploads the already committed block.
    response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/1",
        json={"trials": first_block_trial_payloads},
    )

    # Then: committed blocks cannot be uploaded again.
    assert first_upload_response.status_code == 204
    assert response.status_code == 409
    assert response.json() == {"detail": "The block upload could not be committed because the session state is invalid."}


def test_upload_block_rejects_trial_sequence_ending_with_anticipatory_response(session_client: TestClient) -> None:
    # Given: one running session waiting for the first trial in the first deterministic block.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())
    first_block = created_session.blocks[0]
    first_block_trial_payloads = [
        {
            "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
        }
        for trial in first_block.trials
    ]
    first_block_trial_payloads[0] = {
        "events": [{"event_type": "left", "elapsed_ms": 100}],
    }

    # When: one uploaded block contains one trial ending with one anticipatory response instead of one final action.
    upload_response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/1",
        json={"trials": first_block_trial_payloads},
    )

    # Then: the incomplete raw-event sequence is rejected.
    assert upload_response.status_code == 422
    assert upload_response.json() == {"detail": "The block upload payload is invalid."}


def test_upload_block_returns_generic_conflict_for_invalid_stored_session_state(session_client: TestClient) -> None:
    # Given: one running session whose stored event history has been corrupted between requests.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())
    app = session_client.app
    assert isinstance(app, FastAPI)
    runtime = app.state.runtime
    first_block = created_session.blocks[0]
    first_block_trial_payloads = [
        {
            "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350}],
        }
        for trial in first_block.trials
    ]

    with runtime.session_factory() as database_session:
        persisted_session = database_session.scalar(
            select(SessionRecord).where(SessionRecord.session_key == created_session.session_key)
        )

        assert persisted_session is not None

        database_session.add(
            SessionTrialEventRecord(
                session_id=persisted_session.id,
                trial_id=1,
                event_index=1,
                elapsed_ms=350,
                event_type=TrialEventType.LEFT,
            )
        )
        database_session.commit()

    # When: the client uploads the first block against that corrupted stored session state.
    upload_response = session_client.put(
        f"/api/sessions/{created_session.session_key}/blocks/1",
        json={"trials": first_block_trial_payloads},
    )

    # Then: the route returns one generic conflict instead of exposing internal corruption details.
    assert upload_response.status_code == 409
    assert upload_response.json() == {
        "detail": "The block upload could not be committed because the session state is invalid."
    }


@pytest.mark.parametrize(
    ("payload", "expected_fragment"),
    [
        pytest.param({}, "trials", id="missing_trials"),
        pytest.param({"trials": []}, "at least 1 item", id="empty_trials"),
        pytest.param(
            {
                "trials": [
                    {
                        "events": [{"event_type": "invalid", "elapsed_ms": 100}],
                    }
                ]
            },
            "event_type",
            id="invalid_event_type",
        ),
    ],
)
def test_upload_block_rejects_invalid_request_payloads(
    session_client: TestClient,
    payload: dict[str, object],
    expected_fragment: str,
) -> None:
    # Given: one running session and one invalid block-upload payload.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    # When: the client uploads one malformed block payload.
    response = session_client.put(f"/api/sessions/{created_session.session_key}/blocks/1", json=payload)

    # Then: request validation rejects the payload.
    assert response.status_code == 422
    assert expected_fragment in str(response.json())
