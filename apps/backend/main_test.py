"""Tests for the backend executable entrypoint behavior."""

from __future__ import annotations

import os
import socket
import threading
import time
import urllib.request
from typing import TYPE_CHECKING

from apps.backend.main import main
from libs.testing.io import write_json

if TYPE_CHECKING:
    from pathlib import Path


def test_main_uses_environment_settings_to_serve_frontend(tmp_path: Path) -> None:
    # Given: one explicit backend config file path and one reserved local port.
    settings_path = tmp_path / "backend-settings.json"
    host, port = _reserve_local_port()
    write_json(
        settings_path,
        {
            "host": host,
            "port": port,
            "debug": False,
            "iats": [],
        },
    )
    previous_settings_path = os.environ.get("IAT_RESOURCES_CONFIG_PATH")

    try:
        os.environ["IAT_RESOURCES_CONFIG_PATH"] = str(settings_path)

        # When: the backend main entrypoint starts in one background thread and one client requests the frontend shell.
        server_thread = threading.Thread(target=main, daemon=True)
        server_thread.start()
        response_text = _wait_for_frontend_shell(host, port)
    finally:
        if previous_settings_path is None:
            os.environ.pop("IAT_RESOURCES_CONFIG_PATH", None)
        else:
            os.environ["IAT_RESOURCES_CONFIG_PATH"] = previous_settings_path

    # Then: the configured backend server starts and serves the bundled frontend shell.
    assert '<div id="app"></div>' in response_text


def _reserve_local_port() -> tuple[str, int]:
    with socket.socket() as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        reserved_host, reserved_port = server_socket.getsockname()
        return str(reserved_host), int(reserved_port)


def _wait_for_frontend_shell(host: str, port: int) -> str:
    deadline = time.monotonic() + 15

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/", timeout=0.5) as response:
                return response.read().decode("utf-8")
        except OSError:
            time.sleep(0.1)

    raise AssertionError("Timed out waiting for backend main.py server to start.")
