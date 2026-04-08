# IAT

An Implicit Association Test app with a FastAPI backend, a Vite/TypeScript frontend, YAML-backed experiment definitions, and locally downloaded stimulus assets.

## Layout

- `backend/` FastAPI app, ORM models, services, and tests
- `frontend/` single-page runner
- `resources/iats/` experiment definitions
- `resources/downloads/` tracked download manifests
- `resources/project-implicit/` local downloaded stimulus files

## Requirements

- Python 3.12+
- Node.js 20+
- `uv`

## Install

```bash
uv sync --group dev
npm ci
```

## Configure

Set these in the environment or a local `.env` file:

- `SECRET_KEY`
- `DATABASE_URL`
- `ASSETS_DIR` optional, defaults to `resources/`
- `DEFINITIONS_DIR` optional, defaults to `resources/iats/`
- `LOG_STDOUT` optional, defaults to `true`
- `LOG_DIR` optional, defaults to `logs/`
- `LOG_LEVEL` optional, defaults to `INFO`
- `UVICORN_HOST` optional, defaults to `127.0.0.1`
- `UVICORN_PORT` optional, defaults to `8000`
- `UVICORN_RELOAD` optional, defaults to `false`
- `CORS_ALLOWED_ORIGINS` optional, defaults to `http://127.0.0.1:5173` and `http://localhost:5173`

Example:

```env
SECRET_KEY=dev-secret
DATABASE_URL=sqlite:///instance/app.sqlite3
```

## Run

Start the backend:

```bash
uv run python -m backend.app.main
```

For auto-reload during development:

```bash
npm run dev:backend
```

Start the frontend:

```bash
npm run dev
```

Default URLs:

- API: `http://127.0.0.1:8000/api`
- Assets: `http://127.0.0.1:8000/assets`
- Frontend: Vite dev server on `http://127.0.0.1:5173`

The frontend can also use `window.IAT_API_BASE_URL` if you need to point it at a different backend.

## Session Behavior

- Trials are planned client-side from a deterministic seed.
- The default keyboard shortcuts are `E` for left and `I` for right.
- The backend creates tables and syncs YAML definitions on startup.

## Asset Download

Project Implicit source materials are not stored in git.

Download everything listed in `resources/downloads/project-implicit.yaml`:

```bash
npm run setup
```

Only the asset sources referenced by the current image-based IAT definitions are tracked.

Download only selected sources:

```bash
uv run python -m backend.app.cli download-assets --source age-faces --source race-attitudes
```

Start over and redownload:

```bash
uv run python -m backend.app.cli download-assets --reset
```

The downloader writes a local manifest to `resources/project-implicit/README.local.md`.

## Definitions

Experiment definitions live in `resources/iats/`.

Each file defines:

- experiment metadata
- two category axes
- text or image stimuli for each split

The backend derives blocks, category pairings, and runnable session payloads from those definitions.

Image-backed definitions must resolve to existing local files beneath `resources/`.

If a definition's structure changes after sessions have already been recorded, the sync step refuses to rewrite that experiment automatically.

## Commands

```bash
uv run python -m backend.app.cli sync-definitions
npm run format
npm run lint
npm run test
npm run build
```

## Notes

- `assets/README.md` documents the asset workflow and provenance rules.
- `resources/downloads/project-implicit.yaml` is the tracked source list.
- `docs/` contains supporting reference material.
