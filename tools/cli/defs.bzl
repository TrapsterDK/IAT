"""Macros for generating CLI wrapper binaries."""

load("@bazel_lib//lib:expand_template.bzl", "expand_template")
load("//tools/python:defs.bzl", "py_binary")

def cli_wrapper_binaries(app_lib, commands, visibility = None):
    """Generate one thin Python wrapper per command.

    Args:
      app_lib: The shared CLI application library target.
      commands: Command names to generate wrappers for.
      visibility: Optional visibility for the generated binaries.
    """
    for command in commands:
        entrypoint_name = command + "_entrypoint"

        expand_template(
            name = entrypoint_name,
            out = command + "_main.py",
            substitutions = {
                "{command}": command,
            },
            template = [
                '"""Generated wrapper for `{command}`."""',
                "",
                "import sys",
                "",
                "from tools.cli.app import run_specific_command",
                "",
                'if __name__ == "__main__":',
                '    raise SystemExit(run_specific_command("{command}", sys.argv[1:]))',
            ],
        )

        py_binary(
            name = command,
            srcs = [":" + entrypoint_name],
            main = command + "_main.py",
            visibility = visibility,
            deps = [app_lib],
        )
