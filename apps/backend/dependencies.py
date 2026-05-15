"""Shared FastAPI dependencies for the backend API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request  # noqa: TC002

if TYPE_CHECKING:
    from apps.backend.services.iat import IatService


@dataclass(slots=True)
class BackendServices:
    """Application services stored on FastAPI application state."""

    iat_service: IatService


def get_services(request: Request) -> BackendServices:
    """Return the configured backend services from application state.

    Args:
        request: Current request used to access application state.

    Returns:
        The configured backend services.

    Raises:
        RuntimeError: Backend application services have not been configured.
        TypeError: The configured backend services have one unexpected type.
    """
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("Backend services are not configured.")

    if not isinstance(services, BackendServices):
        raise TypeError("Backend services have one unexpected type.")

    return services


def get_iat_service(request: Request) -> IatService:
    """Return the configured backend IAT service from application state.

    Args:
        request: Current request used to access application state.

    Returns:
        The configured backend IAT service.

    Raises:
        RuntimeError: Backend application services have not been configured.
        TypeError: The configured backend services have one unexpected type.
    """
    return get_services(request).iat_service
