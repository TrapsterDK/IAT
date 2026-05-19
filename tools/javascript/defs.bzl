"""Repository-local JavaScript and TypeScript rule wrappers."""

load("@aspect_rules_swc//swc:defs.bzl", "swc")
load("@aspect_rules_ts//ts:defs.bzl", _ts_project = "ts_project")
load("@bazel_skylib//lib:partial.bzl", "partial")

_DEFAULT_TRANSPILER = partial.make(
    swc,
    swcrc = "//:.swcrc",
)

def ts_project(name, **kwargs):
    if "transpiler" not in kwargs and not kwargs.get("emit_declaration_only", False) and not kwargs.get("no_emit", False):
        kwargs["transpiler"] = _DEFAULT_TRANSPILER

    _ts_project(name = name, **kwargs)
