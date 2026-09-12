from importlib.metadata import (
    PackageNotFoundError,
    version as package_version,
)

import typer


app = typer.Typer()


def _treeforge_version() -> str:
    try:
        return package_version(
            "treeforge"
        )
    except PackageNotFoundError:
        return "unknown"


@app.callback(
    invoke_without_command=True,
)
def version() -> None:
    """Show the installed TreeForge version."""

    typer.echo(
        f"TreeForge v{_treeforge_version()}"
    )