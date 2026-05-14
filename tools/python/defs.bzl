"""Repository Python rule wrappers."""

load(
    "@aspect_rules_py//py:defs.bzl",
    _py_binary = "py_binary",
    _py_library = "py_library",
    _py_test = "py_test",
)

py_binary = _py_binary
py_library = _py_library

_PYTEST_LABEL = Label("@pip//pytest")
_PYTEST_LABEL_STRING = "@pip//pytest"

def py_test(name, deps = [], args = [], **kwargs):
    """Wrap `py_test` and default tests to Aspect's shared pytest main.

    Args:
      name: Name of the test target.
      deps: Additional dependencies for the test target.
      args: Extra pytest arguments.
      **kwargs: Forwarded to the underlying `py_test` rule.
    """
    deps = list(deps)
    if _PYTEST_LABEL not in deps and _PYTEST_LABEL_STRING not in deps:
        deps.append(_PYTEST_LABEL)

    _py_test(
        name = name,
        args = args + ["--import-mode=importlib"],
        deps = deps,
        pytest_main = True,
        **kwargs
    )
