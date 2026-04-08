"""FastAPI API routes for tests and completed attempts."""

from __future__ import annotations

from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from backend.app.database import create_db_session
from backend.app.models import (
    Attempt,
    Category,
    Experiment,
    ExperimentVariant,
    Phase,
    ResponseSide,
    Showing,
    ShowingInput,
    ShowingInputSource,
    Stimulus,
)
from backend.app.schemas import (
    ApiErrorResponse,
    AttemptCompletionRequest,
    AttemptCompletionResponse,
    CompletionSummary,
    ShowingInputPayload,
    ShowingPayload,
    TestListItem,
    TestListResponse,
    TestPayload,
)
from backend.app.services import assign_variant, build_test_payload, score_attempt
from backend.app.services.runs import RunTokenPayload, dump_run_token, load_run_token

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as DBSession


api_router = APIRouter(prefix="/api")


def _json_error(message: str, status_code: HTTPStatus) -> JSONResponse:
    return JSONResponse(content={"error": message}, status_code=status_code)


def _load_test_or_404(session: DBSession, slug: str) -> Experiment:
    statement = (
        select(Experiment)
        .options(
            selectinload(Experiment.variants),
            selectinload(Experiment.categories).selectinload(Category.stimuli),
            selectinload(Experiment.phases),
        )
        .where(Experiment.slug == slug)
    )
    test = session.execute(statement).scalar_one_or_none()
    if test is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Test not found.")
    return test


def _test_stimuli(test: Experiment) -> list[Stimulus]:
    return [stimulus for category in test.categories for stimulus in category.stimuli]


def _phase_category_ids(phase: Phase) -> set[int]:
    category_ids = {phase.left_primary_category_id, phase.right_primary_category_id}
    if phase.left_secondary_category_id is not None:
        category_ids.add(phase.left_secondary_category_id)
    if phase.right_secondary_category_id is not None:
        category_ids.add(phase.right_secondary_category_id)
    return category_ids


def _phase_stimulus_ids(phase: Phase) -> set[int]:
    category_ids = _phase_category_ids(phase)
    return {stimulus.id for stimulus in _test_stimuli(phase.test) if stimulus.category_id in category_ids}


def _expected_showing_count(phase: Phase) -> int:
    return phase.showings_per_category * len(_phase_category_ids(phase))


def _validate_showing_set(payload: AttemptCompletionRequest, phases_by_id: dict[int, Phase]) -> str | None:
    showings_by_phase: dict[int, list[ShowingPayload]] = defaultdict(list)
    for showing_payload in payload.showings:
        showings_by_phase[showing_payload.phase_id].append(showing_payload)

    expected_phase_ids = set(phases_by_id)
    submitted_phase_ids = set(showings_by_phase)

    if submitted_phase_ids - expected_phase_ids:
        return "Showing references an unknown phase or stimulus."
    if expected_phase_ids - submitted_phase_ids:
        return "Attempt completion must include showings for every configured phase."

    for phase_id, phase in phases_by_id.items():
        phase_showings = showings_by_phase[phase_id]
        expected_count = _expected_showing_count(phase)
        if len(phase_showings) != expected_count:
            return "Attempt completion must include every planned showing exactly once."

        showing_indices = sorted(showing_payload.showing_index for showing_payload in phase_showings)
        if showing_indices != list(range(expected_count)):
            return "Attempt completion must include every planned showing exactly once."

    return None


def _validate_showing_inputs(showing_payload: ShowingPayload, inputs: list[ShowingInputPayload]) -> str | None:
    if not inputs:
        return "Every showing must include at least one recorded input."

    input_indices = sorted(input_payload.input_index for input_payload in inputs)
    if input_indices != list(range(len(inputs))):
        return "Showing inputs must be ordered consecutively starting at zero."

    if any(input_payload.handler_timestamp_ms < showing_payload.stimulus_onset_ms for input_payload in inputs):
        return "Showing input timestamps must not precede showing onset."

    return None


def _attempt_is_completed(attempt: Attempt) -> bool:
    return bool(attempt.showings)


def _load_persisted_attempt(session: DBSession, public_id: str) -> Attempt | None:
    return session.execute(
        select(Attempt)
        .options(
            joinedload(Attempt.variant)
            .joinedload(ExperimentVariant.test)
            .selectinload(Experiment.categories)
            .selectinload(Category.stimuli),
            joinedload(Attempt.variant).joinedload(ExperimentVariant.test).selectinload(Experiment.phases),
            selectinload(Attempt.showings).selectinload(Showing.inputs),
            selectinload(Attempt.showings).joinedload(Showing.stimulus),
            selectinload(Attempt.showings).joinedload(Showing.phase),
        )
        .where(Attempt.public_id == public_id)
    ).scalar_one_or_none()


def _load_test_for_completion(session: DBSession, test_id: int) -> Experiment | None:
    return session.execute(
        select(Experiment)
        .options(
            selectinload(Experiment.variants),
            selectinload(Experiment.categories).selectinload(Category.stimuli),
            selectinload(Experiment.phases),
        )
        .where(Experiment.id == test_id)
    ).scalar_one_or_none()


def _create_attempt_from_token(session: DBSession, token_payload: RunTokenPayload) -> Attempt | JSONResponse:
    test = _load_test_for_completion(session, token_payload.experiment_id)
    if test is None:
        return _json_error("Test not found.", HTTPStatus.NOT_FOUND)

    variant = next((candidate for candidate in test.variants if candidate.id == token_payload.variant_id), None)
    if variant is None:
        return _json_error("Variant not found.", HTTPStatus.NOT_FOUND)

    attempt = Attempt(
        public_id=token_payload.public_id,
        variant_id=variant.id,
        visibility_interruptions=0,
    )
    session.add(attempt)
    session.flush()
    return attempt


def _completion_error(message: str, status_code: HTTPStatus, db_session: DBSession) -> JSONResponse:
    db_session.rollback()
    return _json_error(message, status_code)


def _store_showing(
    db_session: DBSession,
    attempt: Attempt,
    showing_payload: ShowingPayload,
    phases_by_id: dict[int, Phase],
    stimuli_by_id: dict[int, Stimulus],
    allowed_stimulus_ids_by_phase: dict[int, set[int]],
    category_counts_by_phase: dict[int, dict[int, int]],
) -> JSONResponse | None:
    phase = phases_by_id.get(showing_payload.phase_id)
    if phase is None or showing_payload.stimulus_id not in allowed_stimulus_ids_by_phase.get(phase.id, set()):
        return _completion_error("Showing references an unknown phase or stimulus.", HTTPStatus.BAD_REQUEST, db_session)

    if _validate_showing_inputs(showing_payload, showing_payload.inputs) is not None:
        return _completion_error(
            _validate_showing_inputs(showing_payload, showing_payload.inputs) or "Invalid showing inputs.",
            HTTPStatus.BAD_REQUEST,
            db_session,
        )

    category_counts_by_phase[phase.id][stimuli_by_id[showing_payload.stimulus_id].category_id] += 1
    showing = Showing(
        attempt=attempt,
        phase_id=showing_payload.phase_id,
        stimulus_id=showing_payload.stimulus_id,
        showing_index=showing_payload.showing_index,
        stimulus_onset_ms=showing_payload.stimulus_onset_ms,
    )
    db_session.add(showing)
    db_session.flush()

    for input_payload in showing_payload.inputs:
        db_session.add(
            ShowingInput(
                showing_id=showing.id,
                input_index=input_payload.input_index,
                side=ResponseSide(input_payload.side),
                input_source=ShowingInputSource(input_payload.input_source),
                event_timestamp_ms=input_payload.event_timestamp_ms,
                handler_timestamp_ms=input_payload.handler_timestamp_ms,
            )
        )

    return None


def _validate_category_counts(
    db_session: DBSession,
    phases: list[Phase],
    category_counts_by_phase: dict[int, dict[int, int]],
) -> JSONResponse | None:
    for phase in phases:
        counts = category_counts_by_phase[phase.id]
        if any(count != phase.showings_per_category for count in counts.values()):
            return _completion_error(
                "Attempt completion must include the configured number of showings for every category.",
                HTTPStatus.BAD_REQUEST,
                db_session,
            )
    return None


def _store_attempt_completion(
    db_session: DBSession,
    attempt: Attempt,
    payload: AttemptCompletionRequest,
) -> JSONResponse | None:
    test = attempt.variant.test
    test_phases = list(test.phases)
    phases_by_id = {phase.id: phase for phase in test_phases}
    stimuli_by_id = {stimulus.id: stimulus for stimulus in _test_stimuli(test)}
    showing_set_error = _validate_showing_set(payload, phases_by_id)
    if showing_set_error is not None:
        return _completion_error(showing_set_error, HTTPStatus.BAD_REQUEST, db_session)

    allowed_stimulus_ids_by_phase = {phase.id: _phase_stimulus_ids(phase) for phase in test_phases}

    attempt.user_agent = payload.environment.user_agent
    attempt.platform = payload.environment.platform
    attempt.browser_language = payload.environment.language
    attempt.viewport_width = payload.environment.viewport_width
    attempt.viewport_height = payload.environment.viewport_height
    attempt.device_pixel_ratio = payload.environment.device_pixel_ratio
    attempt.visibility_interruptions = payload.environment.visibility_interruptions

    category_counts_by_phase = {phase.id: dict.fromkeys(_phase_category_ids(phase), 0) for phase in test_phases}

    for showing_payload in payload.showings:
        error_response = _store_showing(
            db_session,
            attempt,
            showing_payload,
            phases_by_id,
            stimuli_by_id,
            allowed_stimulus_ids_by_phase,
            category_counts_by_phase,
        )
        if error_response is not None:
            return error_response

    category_count_error = _validate_category_counts(db_session, test_phases, category_counts_by_phase)
    if category_count_error is not None:
        return category_count_error

    db_session.commit()
    return None


def _completion_response(attempt: Attempt) -> AttemptCompletionResponse:
    summary_data = score_attempt(attempt)
    return AttemptCompletionResponse(
        attemptId=attempt.public_id,
        variant=attempt.variant.key_event_mode.value,
        summary=CompletionSummary(
            showingCount=summary_data.showing_count,
            accuracy=summary_data.accuracy,
            meanInitialReactionTimeMs=summary_data.mean_initial_reaction_time_ms,
            meanCompletedReactionTimeMs=summary_data.mean_completed_reaction_time_ms,
        ),
    )


@api_router.get("/tests", response_model=TestListResponse)
def list_tests(request: Request) -> TestListResponse:
    """Return configured tests for the SPA landing page."""
    session = create_db_session(request.app)
    try:
        tests = session.execute(select(Experiment).order_by(Experiment.title)).scalars()
        payload = [
            TestListItem(
                id=test.id,
                slug=test.slug,
                title=test.title,
                description=test.description,
            )
            for test in tests
        ]
        return TestListResponse(tests=payload)
    finally:
        session.close()


@api_router.post(
    "/tests/{slug}/attempts",
    status_code=status.HTTP_201_CREATED,
    response_model=TestPayload,
    responses={HTTPStatus.NOT_FOUND: {"model": ApiErrorResponse}},
)
def create_attempt(request: Request, slug: str) -> TestPayload:
    """Create an attempt bootstrap payload without persisting a row yet."""
    session = create_db_session(request.app)
    try:
        test = _load_test_or_404(session, slug)
        public_id = str(uuid4())
        variant = assign_variant(test.variants, public_id)
        attempt_token = dump_run_token(
            request.app.state.settings,
            RunTokenPayload(
                public_id=public_id,
                experiment_id=test.id,
                variant_id=variant.id,
            ),
        )
        return build_test_payload(test, variant, public_id, attempt_token)
    finally:
        session.close()


@api_router.post(
    "/attempts/{public_id}/complete",
    response_model=AttemptCompletionResponse,
    responses={
        HTTPStatus.BAD_REQUEST: {"model": ApiErrorResponse},
        HTTPStatus.CONFLICT: {"model": ApiErrorResponse},
        HTTPStatus.NOT_FOUND: {"model": ApiErrorResponse},
    },
)
def complete_attempt(
    request: Request,
    public_id: str,
    payload: AttemptCompletionRequest,
) -> AttemptCompletionResponse | JSONResponse:
    """Persist submitted showings and return a summary payload."""
    session = create_db_session(request.app)
    try:
        error_response: JSONResponse | None = None
        try:
            token_payload = load_run_token(request.app.state.settings, payload.attempt_token)
        except ValueError:
            error_response = _json_error("Invalid attempt token.", HTTPStatus.BAD_REQUEST)
        else:
            if token_payload.public_id != public_id:
                error_response = _json_error(
                    "Attempt token does not match the requested attempt.", HTTPStatus.BAD_REQUEST
                )

        if error_response is not None:
            return error_response

        attempt = _load_persisted_attempt(session, public_id)
        if attempt is not None:
            if _attempt_is_completed(attempt):
                return _completion_response(attempt)
        else:
            created_attempt = _create_attempt_from_token(session, token_payload)
            if isinstance(created_attempt, JSONResponse):
                return created_attempt
            attempt = created_attempt

        try:
            error_response = _store_attempt_completion(session, attempt, payload)
        except IntegrityError:
            session.rollback()
            persisted_attempt = _load_persisted_attempt(session, public_id)
            if persisted_attempt is not None and _attempt_is_completed(persisted_attempt):
                return _completion_response(persisted_attempt)
            error_response = _json_error("Attempt showings conflict with existing stored rows.", HTTPStatus.CONFLICT)

        if error_response is not None:
            return error_response

        return _completion_response(attempt)
    finally:
        session.close()
