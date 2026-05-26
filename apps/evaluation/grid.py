"""Selenium Grid worker discovery for pooled evaluation runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from pydantic import BaseModel, ConfigDict, Field, Json

if TYPE_CHECKING:
    from yarl import URL

DISCOVERY_TIMEOUT_SECONDS = 10.0
WORKER_ID_CAPABILITY_NAME = "iat:workerId"
_NODE_DISCOVERY_QUERY = gql(
    """
    query DiscoverGridNodes {
      nodesInfo {
        nodes {
          id
          status
          stereotypes
        }
      }
    }
    """
)


@dataclass(frozen=True, slots=True)
class GridWorker:
    """One addressable Selenium Grid worker discovered from one node stereotype."""

    worker_id: str
    browser_name: str


class _GraphqlWorkerStereotype(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, str_strip_whitespace=True)

    worker_id: str | None = Field(default=None, alias=WORKER_ID_CAPABILITY_NAME)
    browser_name: str | None = Field(default=None, alias="browserName")


class _GraphqlStereotypeEntry(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    stereotype: _GraphqlWorkerStereotype


class _GraphqlNode(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, str_strip_whitespace=True)

    id: str = Field(min_length=1)
    status: str
    stereotypes: Json[tuple[_GraphqlStereotypeEntry, ...]]


class _GraphqlNodesInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    nodes: tuple[_GraphqlNode, ...]


class _GraphqlResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    nodes_info: _GraphqlNodesInfo = Field(alias="nodesInfo")


def _parse_grid_workers(graphql_payload: object) -> list[GridWorker]:
    """Parse one Selenium Grid GraphQL payload into evaluation workers.

    Args:
        graphql_payload: Raw GraphQL response payload from the Grid router.

    Returns:
        The discovered workers in first-seen discovery order.
    """
    payload = _GraphqlResponse.model_validate(graphql_payload)
    workers_by_id: dict[str, tuple[GridWorker, str]] = {}
    for node in payload.nodes_info.nodes:
        if node.status != "UP":
            continue

        for stereotype_entry in node.stereotypes:
            stereotype = stereotype_entry.stereotype
            if not stereotype.worker_id or not stereotype.browser_name:
                continue

            resolved_worker = GridWorker(
                worker_id=stereotype.worker_id,
                browser_name=stereotype.browser_name,
            )

            existing_entry = workers_by_id.setdefault(resolved_worker.worker_id, (resolved_worker, node.id))
            if existing_entry[0] != resolved_worker:
                raise ValueError(
                    f"Discovered duplicate evaluation worker id '{resolved_worker.worker_id}'. "
                    f"Each worker must expose one unique '{WORKER_ID_CAPABILITY_NAME}' capability."
                )

    return [worker for worker, _ in workers_by_id.values()]


def discover_grid_workers(grid_url: URL) -> list[GridWorker]:
    """Discover all configured evaluation workers from one Selenium Grid.

    Args:
        grid_url: Selenium Grid router URL.

    Returns:
        The discovered workers in first-seen discovery order.
    """
    client = Client(
        transport=RequestsHTTPTransport(
            url=str(grid_url / "graphql"),
            headers={"Accept": "application/json"},
            timeout=int(DISCOVERY_TIMEOUT_SECONDS),
        ),
        fetch_schema_from_transport=False,
    )

    return _parse_grid_workers(client.execute(_NODE_DISCOVERY_QUERY))
