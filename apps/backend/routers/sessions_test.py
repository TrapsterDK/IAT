"""Tests for backend session routes."""

from __future__ import annotations

from statistics import stdev
from typing import TYPE_CHECKING

import pytest

from apps.backend.schemas.session import SessionBootstrapResponse, SessionScoreResponse

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx import Response


def _validation_error_details(response: Response) -> list[dict[str, object]]:
    return response.json()["detail"]


def _assert_has_validation_error(
    response: Response,
    expected_loc: tuple[str | int, ...],
    expected_type: str,
) -> None:
    validation_errors = _validation_error_details(response)
    assert any(
        validation_error["loc"] == list(expected_loc) and validation_error["type"] == expected_type
        for validation_error in validation_errors
    )


def _upload_completed_sample_session(session_client: TestClient) -> SessionBootstrapResponse:
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    for block_index, block in enumerate(created_session.blocks, start=1):
        block_trial_payloads = [
            {
                "events": [{"event_type": trial.correct_response_side.value, "elapsed_ms": 350 + block_index * 50}],
            }
            for trial in block.trials
        ]
        upload_response = session_client.put(
            f"/api/sessions/{created_session.session_key}/blocks/{block_index}",
            json={"trials": block_trial_payloads},
        )
        assert upload_response.status_code == 204

    return created_session


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
    ("payload", "expected_loc", "expected_type"),
    [
        pytest.param({}, ("body", "iat_slug"), "missing", id="missing_iat_slug"),
        pytest.param(
            {"iat_slug": "", "client_context": None},
            ("body", "iat_slug"),
            "string_too_short",
            id="blank_iat_slug",
        ),
    ],
)
def test_create_session_rejects_invalid_payloads(
    session_client: TestClient,
    payload: dict[str, object],
    expected_loc: tuple[str, ...],
    expected_type: str,
) -> None:
    # Given: one invalid session-creation payload.

    # When: the client creates one session.
    response = session_client.post("/api/sessions", json=payload)

    # Then: request validation rejects the payload.
    assert response.status_code == 422
    _assert_has_validation_error(response, expected_loc, expected_type)


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


def test_get_score_returns_not_found_for_unknown_session_key(session_client: TestClient) -> None:
    # Given: one unknown public session key.

    # When: the client requests one completed-session score.
    response = session_client.get("/api/sessions/missing-session/score")

    # Then: the route reports the session as missing.
    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_get_score_returns_conflict_for_running_session(session_client: TestClient) -> None:
    # Given: one running participant session with no completed uploads yet.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    # When: the client requests one score before the session is completed.
    response = session_client.get(f"/api/sessions/{created_session.session_key}/score")

    # Then: the route reports the score as unavailable.
    assert response.status_code == 409
    assert response.json() == {"detail": "The session score is unavailable."}


def test_get_score_returns_completed_session_score(session_client: TestClient) -> None:
    # Given: one completed participant session with every deterministic block uploaded.
    created_session = _upload_completed_sample_session(session_client)

    # When: the client requests the completed-session score.
    response = session_client.get(f"/api/sessions/{created_session.session_key}/score")

    # Then: the route returns the computed D-score and public headline.
    assert response.status_code == 200
    score_response = SessionScoreResponse.model_validate(response.json())
    assert score_response.d_score == pytest.approx(150.0 / stdev([500.0] * 4 + [650.0] * 4))
    assert score_response.headline == "Strong automatic association of Alpha with Gamma."


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
    _assert_has_validation_error(response, ("path", "block_index"), "greater_than_equal")


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
    assert response.json() == {
        "detail": "The block upload could not be committed because the session state is invalid."
    }


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
    assert response.json() == {
        "detail": "The block upload could not be committed because the session state is invalid."
    }


@pytest.mark.parametrize(
    ("payload", "expected_loc", "expected_type"),
    [
        pytest.param({}, ("body", "trials"), "missing", id="missing_trials"),
        pytest.param(
            {"trials": []},
            ("body", "trials"),
            "too_short",
            id="empty_trials",
        ),
        pytest.param(
            {
                "trials": [
                    {
                        "events": [{"event_type": "invalid", "elapsed_ms": 100}],
                    }
                ]
            },
            ("body", "trials", 0, "events", 0, "event_type"),
            "enum",
            id="invalid_event_type",
        ),
    ],
)
def test_upload_block_rejects_invalid_request_payloads(
    session_client: TestClient,
    payload: dict[str, object],
    expected_loc: tuple[str | int, ...],
    expected_type: str,
) -> None:
    # Given: one running session and one invalid block-upload payload.
    created_response = session_client.post("/api/sessions", json={"iat_slug": "sample-iat"})
    assert created_response.status_code == 201
    created_session = SessionBootstrapResponse.model_validate(created_response.json())

    # When: the client uploads one malformed block payload.
    response = session_client.put(f"/api/sessions/{created_session.session_key}/blocks/1", json=payload)

    # Then: request validation rejects the payload.
    assert response.status_code == 422
    _assert_has_validation_error(response, expected_loc, expected_type)
