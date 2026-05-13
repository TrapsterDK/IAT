"""Repository lint aspect definitions."""

load("@aspect_rules_lint//lint:buildifier.bzl", "lint_buildifier_aspect")
load("@aspect_rules_lint//lint:eslint.bzl", "lint_eslint_aspect")
load("@aspect_rules_lint//lint:pydoclint.bzl", "lint_pydoclint_aspect")
load("@aspect_rules_lint//lint:ruff.bzl", "lint_ruff_aspect")
load("@aspect_rules_lint//lint:ty.bzl", "lint_ty_aspect")
load("@aspect_rules_lint//lint:vale.bzl", "lint_vale_aspect")
load("@aspect_rules_lint//lint:yamllint.bzl", "lint_yamllint_aspect")

ruff = lint_ruff_aspect(
    binary = Label("@aspect_rules_lint//lint:ruff_bin"),
    configs = [Label("//:.ruff.toml")],
)

eslint = lint_eslint_aspect(
    binary = Label("//tools/lint:eslint"),
    configs = [Label("//:eslintrc")],
)

pydoclint = lint_pydoclint_aspect(
    binary = Label("//tools/lint:pydoclint"),
    config = Label("//:.pydoclint.toml"),
)

ty = lint_ty_aspect(
    binary = Label("@aspect_rules_lint//lint:ty_bin"),
    config = Label("//:.ty.toml"),
)

yamllint = lint_yamllint_aspect(
    binary = Label("//tools/lint:yamllint"),
    config = Label("//:.yamllint"),
    filegroup_tags = ["yaml", "lint-with-yamllint"],
    extra_args = ["--strict"],
)

vale = lint_vale_aspect(
    binary = Label("//tools/lint:vale"),
    config = Label("//:.vale.ini"),
    styles = Label("//tools/lint:vale_styles"),
    template = Label("//.vale:vale.tmpl"),
)

buildifier = lint_buildifier_aspect(
    binary = Label("@buildifier_prebuilt//:buildifier"),
)
