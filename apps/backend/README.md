# Backend

Serves the published IAT catalog, public stimulus images, and the participant session API.

## Usage

Run the backend server:

```bash
bazel run //apps/backend:main
```

Run the backend server with an explicit configuration file:

```bash
IAT_RESOURCES_CONFIG_PATH=resources/backend.yaml \
  bazel run //apps/backend:main
```

Useful routes:

- `GET /`: serve the participant-facing single-page frontend shell
- `GET /assets/{path}`: serve built frontend assets such as JavaScript and CSS
- `GET /iats`: list published IATs
- `GET /iats/{slug}`: fetch one published IAT
- `GET /stimuli/{path}`: serve one published PNG stimulus
- `POST /api/sessions`: create one participant session and return its run plan
- `PUT /api/sessions/{session_key}/blocks/{block_index}`: upload one completed block
- `GET /api/sessions/{session_key}/score`: fetch the computed score for one completed session

## Configuration

By default the backend loads built-in resource paths from the workspace root when run through Bazel.

Set `IAT_RESOURCES_CONFIG_PATH` to load a custom configuration file instead.
