"""Export the backend OpenAPI schema as stable JSON."""

from __future__ import annotations

import json
import sys

from apps.backend.app import create_openapi_app

if __name__ == "__main__":
    json.dump(create_openapi_app().openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
