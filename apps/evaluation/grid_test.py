"""Tests for Selenium Grid worker discovery."""

from __future__ import annotations

import pytest

from apps.evaluation.grid import _parse_grid_workers


def test_parse_grid_workers_returns_one_unique_worker_per_worker_capability() -> None:
    # Given: one Selenium Grid GraphQL payload with two unique worker identities and one duplicate stereotype.
    graphql_payload = {
        "nodesInfo": {
            "nodes": [
                {
                    "id": "node-a",
                    "status": "UP",
                    "stereotypes": (
                        '[{"stereotype":{"browserName":"chrome","iat:workerId":"worker-a"},"slots":1},'
                        '{"stereotype":{"browserName":"chrome","iat:workerId":"worker-a"},"slots":1}]'
                    ),
                    "uri": "http://node-a:5555",
                },
                {
                    "id": "node-b",
                    "status": "UP",
                    "stereotypes": (
                        '[{"stereotype":{"browserName":"firefox","iat:workerId":"worker-b"},"slots":1},'
                        '{"stereotype":{"browserName":"firefox"},"slots":1}]'
                    ),
                    "uri": "http://node-b:5555",
                },
                {
                    "id": "node-c",
                    "status": "DRAINING",
                    "stereotypes": '[{"stereotype":{"browserName":"safari","iat:workerId":"worker-c"},"slots":1}]',
                    "uri": "http://node-c:5555",
                },
            ]
        }
    }

    # When: workers are extracted from the Grid GraphQL payload.
    workers = _parse_grid_workers(graphql_payload)

    # Then: one worker is returned for each unique worker identity on one ready node.
    assert [(worker.worker_id, worker.browser_name) for worker in workers] == [
        ("worker-a", "chrome"),
        ("worker-b", "firefox"),
    ]


def test_parse_grid_workers_rejects_duplicate_worker_ids_on_different_nodes() -> None:
    # Given: one Selenium Grid GraphQL payload that exposes the same worker identity on two nodes.
    graphql_payload = {
        "nodesInfo": {
            "nodes": [
                {
                    "id": "node-a",
                    "status": "UP",
                    "stereotypes": '[{"stereotype":{"browserName":"chrome","iat:workerId":"worker-a"},"slots":1}]',
                    "uri": "http://node-a:5555",
                },
                {
                    "id": "node-b",
                    "status": "UP",
                    "stereotypes": '[{"stereotype":{"browserName":"firefox","iat:workerId":"worker-a"},"slots":1}]',
                    "uri": "http://node-b:5555",
                },
            ]
        }
    }

    # When: workers are extracted from the Grid GraphQL payload.
    # Then: discovery rejects the ambiguous worker identity.
    with pytest.raises(ValueError, match="duplicate evaluation worker id"):
        _parse_grid_workers(graphql_payload)


def test_parse_grid_workers_keeps_first_duplicate_worker_id_when_browser_matches() -> None:
    # Given: one Selenium Grid GraphQL payload that exposes the same worker identity twice with the same browser.
    graphql_payload = {
        "nodesInfo": {
            "nodes": [
                {
                    "id": "node-a",
                    "status": "UP",
                    "stereotypes": '[{"stereotype":{"browserName":"chrome","iat:workerId":"worker-a"},"slots":1}]',
                    "uri": "http://node-a:5555",
                },
                {
                    "id": "node-b",
                    "status": "UP",
                    "stereotypes": '[{"stereotype":{"browserName":"chrome","iat:workerId":"worker-a"},"slots":1}]',
                    "uri": "http://node-b:5555",
                },
            ]
        }
    }

    # When: workers are extracted from the Grid GraphQL payload.
    workers = _parse_grid_workers(graphql_payload)

    # Then: discovery keeps the first matching worker entry and ignores the duplicate.
    assert [(worker.worker_id, worker.browser_name) for worker in workers] == [("worker-a", "chrome")]


def test_parse_grid_workers_ignores_worker_stereotypes_without_browser_name() -> None:
    # Given: one Selenium Grid GraphQL payload with one routed worker id but no browser name.
    graphql_payload = {
        "nodesInfo": {
            "nodes": [
                {
                    "id": "node-a",
                    "status": "UP",
                    "stereotypes": '[{"stereotype":{"iat:workerId":"worker-a"}}]',
                    "uri": "http://node-a:5555",
                }
            ]
        }
    }

    # When: workers are extracted from the Grid GraphQL payload.
    workers = _parse_grid_workers(graphql_payload)

    # Then: discovery ignores the incomplete routed worker stereotype.
    assert workers == []
