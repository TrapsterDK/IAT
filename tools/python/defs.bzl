"""Repository Python rule wrappers."""

load(
    "@aspect_rules_py//py:defs.bzl",
    _py_binary = "py_binary",
    _py_library = "py_library",
    _py_test = "py_test",
)

py_binary = _py_binary
py_library = _py_library

def py_test(name, **kwargs):
    """Wrap `py_test` and default tests to Aspect's shared pytest main.

    Args:
      name: Name of the test target.
      **kwargs: Forwarded to the underlying `py_test` rule.
    """

    _py_test(
        name = name,
        pytest_main = True,
        **kwargs
    )
