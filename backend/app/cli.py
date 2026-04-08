"""CLI commands for app setup and local maintenance tasks."""

from __future__ import annotations

import shutil
from typing import Annotated

import typer

from backend.app import create_app
from backend.app.config import get_config
from backend.app.project_implicit_assets import (
    AssetDownloadError,
    UnknownAssetSourcesError,
    download_assets,
)
from backend.app.services import sync_app_definitions

cli = typer.Typer(no_args_is_help=True)


@cli.command("sync-definitions")
def sync_definitions_command() -> None:
    """Sync IAT configs into the database."""
    sync_app_definitions(create_app(get_config()))


@cli.command("download-assets")
def download_assets_command(
    source_slugs: Annotated[
        list[str] | None,
        typer.Option(
            "--source",
            help="Download only the given source slug. Repeat to include multiple sources.",
        ),
    ] = None,
    reset_existing: Annotated[
        bool,
        typer.Option(
            "--reset",
            help="Delete the existing local Project Implicit asset tree before downloading.",
        ),
    ] = False,
) -> None:
    """Download Project Implicit assets into the local assets tree."""
    settings = get_config()
    if reset_existing and settings.PROJECT_IMPLICIT_ASSETS_DIR.exists():
        shutil.rmtree(settings.PROJECT_IMPLICIT_ASSETS_DIR)

    try:
        download_assets(settings, source_slugs=set(source_slugs or []))
    except UnknownAssetSourcesError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    except AssetDownloadError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    cli()
