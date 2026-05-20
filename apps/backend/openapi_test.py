"""Tests for backend OpenAPI export behavior."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO

from apps.backend.openapi import main


def test_openapi_main_writes_public_contract_json() -> None:
    # Given: one in-memory stdout capture.
    output = StringIO()

    # When: the OpenAPI entrypoint writes the schema.
    with redirect_stdout(output):
        main()

    # Then: one deterministic public OpenAPI document is written to stdout.
    openapi_document = json.loads(output.getvalue())
    assert output.getvalue().endswith("\n")
    assert "/iats" in openapi_document["paths"]
    assert "/api/sessions" in openapi_document["paths"]
    assert openapi_document["paths"]["/api/sessions"]["post"]["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/CreateSessionRequest"}
    assert openapi_document["paths"]["/api/sessions"]["post"]["responses"]["201"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SessionBootstrapResponse"}
