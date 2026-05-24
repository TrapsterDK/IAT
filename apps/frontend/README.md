# Frontend

Participant-facing single-page frontend for browsing published IATs and completing sessions.

The backend serves the built frontend shell and bundled assets.

## Usage

Run the backend server while developing the frontend:

```bash
bazel run //apps/backend:main
```

When changing frontend files while developing, rerun the same command so Bazel
rebuilds the bundled frontend assets and restarts the backend with the updated
runfiles.

## Build output

The frontend bundle target is `//apps/frontend:dist`.

It produces `index.html` plus bundled assets under `assets/`, which the backend
serves at `GET /` and `GET /assets/{path}`.
