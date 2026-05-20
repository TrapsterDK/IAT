"""Export the backend OpenAPI schema as stable JSON."""

from __future__ import annotations

import json
import sys

from apps.backend.application import create_base_app


def main() -> None:
    """Write the backend OpenAPI schema as stable JSON to stdout."""
    json.dump(create_base_app(debug=False).openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
