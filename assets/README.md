# Assets

The app serves stimulus files through the `/assets` URL mount.

## What Is Tracked

- downloader code
- download manifests
- documentation

Downloaded source material under `resources/project-implicit/` is local-only and ignored by git.

## Handling Rules

Project Implicit study materials must not be committed to this repository.

Some stimulus labels come from published source material and may contain dated or sensitive language. They are preserved here as source data, not as project-authored copy.

## Download Workflow

The tracked manifest is `resources/downloads/project-implicit.yaml`.

It only includes the source folders referenced by the current image-based IAT definitions.

Download all configured sources locally with:

```bash
npm run setup
```

Download only selected sources with:

```bash
uv run python -m backend.app.cli download-assets --source age-faces --source race-attitudes
```

Start fresh and redownload with:

```bash
uv run python -m backend.app.cli download-assets --reset
```

## Source Provenance

- Source page: `https://www.projectimplicit.net/resources/study-materials/`
- Downloader manifest: `resources/downloads/project-implicit.yaml`
- Local per-download manifest: `resources/project-implicit/README.local.md`

The source page includes its own research-use and citation guidance.
