"""Run token helpers for stateless experiment bootstrap."""

from __future__ import annotations

import hashlib
import hmac
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from json import dumps, loads
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.config import Settings


@dataclass(frozen=True)
class RunTokenPayload:
    """Signed run bootstrap data returned to the browser."""

    public_id: str
    experiment_id: int
    variant_id: int


def _sign(settings: Settings, encoded_payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _encode_payload(payload: RunTokenPayload) -> str:
    serialized_payload = dumps(
        {
            "public_id": payload.public_id,
            "experiment_id": payload.experiment_id,
            "variant_id": payload.variant_id,
        },
        separators=(",", ":"),
    )
    return urlsafe_b64encode(serialized_payload.encode("utf-8")).decode("ascii")


def _decode_payload(encoded_payload: str) -> dict[str, object]:
    padded = encoded_payload + ("=" * (-len(encoded_payload) % 4))
    decoded = urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    loaded = loads(decoded)
    if not isinstance(loaded, dict):
        msg = "Invalid run token."
        raise TypeError(msg)
    return loaded


def dump_run_token(settings: Settings, payload: RunTokenPayload) -> str:
    """Serialize signed run bootstrap data for the browser."""
    encoded_payload = _encode_payload(payload)
    signature = _sign(settings, encoded_payload)
    return f"{encoded_payload}.{signature}"


def load_run_token(settings: Settings, token: str) -> RunTokenPayload:
    """Load signed run bootstrap data from the browser token."""
    try:
        encoded_payload, signature = token.split(".", maxsplit=1)
    except ValueError as error:
        msg = "Invalid run token."
        raise ValueError(msg) from error

    expected_signature = _sign(settings, encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        msg = "Invalid run token."
        raise ValueError(msg)

    try:
        decoded_payload = _decode_payload(encoded_payload)
    except TypeError as error:
        msg = "Invalid run token."
        raise ValueError(msg) from error

    public_id = decoded_payload.get("public_id")
    experiment_id = decoded_payload.get("experiment_id")
    variant_id = decoded_payload.get("variant_id")
    if not isinstance(public_id, str) or not isinstance(experiment_id, int) or not isinstance(variant_id, int):
        msg = "Invalid run token."
        raise TypeError(msg)

    return RunTokenPayload(
        public_id=public_id,
        experiment_id=experiment_id,
        variant_id=variant_id,
    )
