"""Helpers for reading Bazel Build Event Protocol JSON output.

References:
    https://bazel.build/docs/build-event-protocol
    https://github.com/bazelbuild/bazel/blob/master/src/main/java/com/google/devtools/build/lib/buildeventstream/proto/build_event_stream.proto
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote, urlparse

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@dataclass(frozen=True)
class FileArtifact:
    """A file referenced by Bazel build events."""

    logical_name: str
    path: Path


def _path_from_uri(uri: str) -> Path:
    """Return one local filesystem path from a file URI.

    Args:
        uri: The file URI to decode.

    Returns:
        The decoded local filesystem path.

    Raises:
        ValueError: The URI is not file-backed.
    """
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
    return Path(unquote(parsed.path))


def _artifact_from_entry(entry: object) -> FileArtifact | None:
    """Extract a file-backed artifact from a BEP `File` JSON object.

    Args:
        entry: The decoded BEP `File` object.

    The BEP `File` message is a oneof of `uri`, inline `contents`, or
    `symlink_target_path`. Our CLI consumers only need local file-backed
    artifacts from `--build_event_json_file`, so non-`uri` entries are ignored.

    Returns:
        The extracted artifact, or `None` when the entry is not URI-backed.
    """
    if not isinstance(entry, dict):
        return None

    data = cast("dict[str, object]", entry)
    uri = data.get("uri")
    if not isinstance(uri, str):
        return None

    path = _path_from_uri(uri)
    name = data.get("name")
    return FileArtifact(
        logical_name=name if isinstance(name, str) else path.name,
        path=path,
    )


def load_events(path: Path) -> list[dict[str, object]]:
    """Load newline-delimited BEP JSON events.

    Args:
        path: The BEP JSON file to read.

    Returns:
        The decoded event objects.
    """
    events: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped:
                continue
            event = json.loads(stripped)
            if isinstance(event, dict):
                events.append(event)
    return events


def iter_named_set_files(events: Sequence[dict[str, object]]) -> Iterator[FileArtifact]:
    """Yield files referenced by named-set events.

    Args:
        events: The decoded BEP events to inspect.

    Yields:
        File artifacts referenced by named-set events.

    Notes:
        Bazel's JSON BEP output emits named-set payloads under the top-level
        `namedSetOfFiles` key, matching the proto's `BuildEvent.named_set_of_files`
        field once converted to lowerCamelCase JSON.
    """
    seen: set[Path] = set()
    for event in events:
        named_set = event.get("namedSetOfFiles")
        if not isinstance(named_set, dict):
            continue

        named_set_data = cast("dict[str, object]", named_set)

        entries = named_set_data.get("files")
        if not isinstance(entries, list):
            continue

        for entry in entries:
            artifact = _artifact_from_entry(entry)
            if artifact is None or artifact.path in seen:
                continue
            seen.add(artifact.path)
            yield artifact
