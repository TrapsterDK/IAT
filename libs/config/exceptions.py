"""Exceptions shared by config loading helpers."""


class ExtendingConfigError(RuntimeError):
    """Raised when one extending config file cannot be resolved."""


class ExtendingConfigCycleError(ExtendingConfigError):
    """Raised when config inheritance contains a cycle."""


class ExtendingConfigPathError(ExtendingConfigError):
    """Raised when one extended config path cannot be resolved."""
