"""Session runtime exceptions."""

from __future__ import annotations

INVALID_SESSION_STATE_MESSAGE = "The block upload could not be committed because the session state is invalid."


class SessionError(Exception):
    """Base exception for session runtime failures."""


class IatNotFoundError(SessionError):
    """Raised when one requested published IAT does not exist."""


class SessionNotFoundError(SessionError):
    """Raised when one persisted session cannot be found."""


class SessionConflictError(SessionError):
    """Raised when one session read or write conflicts with stored state."""


class SessionUnscoreableError(SessionError):
    """Raised when one completed session cannot produce one valid score."""


class SessionInputError(SessionError):
    """Raised when one session request payload violates runtime rules."""


class SessionConfigurationError(SessionError):
    """Raised when one IAT or session configuration is invalid."""
