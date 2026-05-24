# Backend

Serves the built participant-facing frontend, published IAT catalog, public stimulus images, and the participant session API.

## Usage

Run the backend server:

```bash
bazel run //apps/backend:main
```

When changing frontend files while developing, rerun the same command so Bazel
rebuilds the bundled frontend assets and restarts the backend with the updated
runfiles.

Run the backend server with an explicit configuration file:

```bash
IAT_RESOURCES_CONFIG_PATH=resources/backend.yaml \
  bazel run //apps/backend:main
```

Useful routes:

- `GET /`: serve the participant-facing single-page frontend shell
- `GET /assets/{path}`: serve built frontend assets such as JavaScript and CSS
- `GET /api/iats`: list published IATs
- `GET /api/iats/{slug}`: fetch one published IAT
- `GET /stimuli/{path}`: serve one published PNG stimulus
- `POST /api/sessions`: create one participant session and return its run plan
- `PUT /api/sessions/{session_key}/blocks/{block_index}`: upload one completed block
- `GET /api/sessions/{session_key}/score`: fetch the computed score for one completed session

## Configuration

By default the backend loads built-in resource paths from the workspace root when run through Bazel.

Set `IAT_RESOURCES_CONFIG_PATH` to load a custom configuration file instead.
