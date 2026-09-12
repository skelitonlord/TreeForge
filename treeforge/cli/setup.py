from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import typer

from treeforge.setup.mode import (
    InstallationMode,
    installation_mode_file,
    parse_installation_mode,
    read_installation_mode,
    supports_bringup,
    supports_maintenance,
    write_installation_mode,
)


app = typer.Typer(
    help=(
        "Inspect, change, or repair the TreeForge "
        "installation environment."
    )
)


def _repository_root() -> Path:
    """
    Return the active TreeForge repository root.

    The top-level TreeForge callback already enforces repository-root
    execution before setup commands are dispatched.
    """

    return Path.cwd().resolve()


def _setup_ci_script(
    repository_root: Path,
) -> Path:
    script = (
        repository_root
        / "setup-ci.sh"
    )

    if not script.is_file():
        typer.echo(
            "TreeForge setup-ci.sh was not found at:"
        )
        typer.echo(
            f"  {script}"
        )

        raise typer.Exit(
            code=1
        )

    return script


def _reconcile_mode(
    mode: InstallationMode,
) -> None:
    repository_root = _repository_root()
    script = _setup_ci_script(
        repository_root
    )

    typer.echo(
        f"Reconciling TreeForge {mode.display_name} "
        "mode dependencies..."
    )
    typer.echo("")

    command = [
        str(script),
        "--install-dir",
        str(repository_root),
        "--python",
        sys.executable,
        "--mode",
        mode.value,
        "--skip-update",
    ]

    try:
        subprocess.run(
            command,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        typer.echo("")
        typer.echo(
            "TreeForge environment reconciliation failed."
        )

        raise typer.Exit(
            code=exc.returncode or 1
        ) from exc


def _echo_mode_status(
    mode: InstallationMode,
) -> None:
    typer.echo(
        f"Installation mode: {mode.display_name}"
    )
    typer.echo("")

    typer.echo("Capabilities:")
    typer.echo(
        "  Existing supported trees: yes"
    )
    typer.echo(
        "  Downstream/user features: yes"
    )
    typer.echo(
        "  New-device bring-up: "
        + (
            "yes"
            if supports_bringup(mode)
            else "no"
        )
    )
    typer.echo(
        "  TreeForge source-development tooling: "
        + (
            "yes"
            if supports_maintenance(mode)
            else "no"
        )
    )


@app.command(
    name="status",
)
def status() -> None:
    """Show the active TreeForge installation mode."""

    repository_root = _repository_root()

    mode = read_installation_mode(
        repository_root=repository_root,
    )

    _echo_mode_status(
        mode
    )

    typer.echo("")
    typer.echo(
        "Mode file:"
    )
    typer.echo(
        f"  {installation_mode_file()}"
    )


@app.command(
    name="mode",
)
def mode(
    requested_mode: str | None = typer.Argument(
        None,
        metavar="[user|maintainer|developer]",
        help=(
            "New installation mode. Omit to show "
            "the current mode."
        ),
    ),
) -> None:
    """
    Show or change the TreeForge installation capability mode.

    Upgrades reconcile newly required dependencies before persisting the
    mode. Downgrades never uninstall previously installed packages.
    """

    repository_root = _repository_root()

    current = read_installation_mode(
        repository_root=repository_root,
    )

    if requested_mode is None:
        _echo_mode_status(
            current
        )
        return

    try:
        target = parse_installation_mode(
            requested_mode
        )
    except ValueError as exc:
        typer.echo(
            str(exc)
        )

        raise typer.Exit(
            code=2
        ) from exc

    if target == current:
        typer.echo(
            f"TreeForge is already in "
            f"{target.display_name} mode."
        )
        typer.echo(
            "Use 'treeforge setup repair' to "
            "reconcile its dependencies."
        )
        return

    if target.rank > current.rank:
        typer.echo(
            f"Changing TreeForge mode: "
            f"{current.display_name} -> "
            f"{target.display_name}"
        )
        typer.echo("")

        _reconcile_mode(
            target
        )
    else:
        typer.echo(
            f"Changing TreeForge mode: "
            f"{current.display_name} -> "
            f"{target.display_name}"
        )
        typer.echo("")
        typer.echo(
            "Previously installed higher-tier packages "
            "will be left installed."
        )

    mode_file = write_installation_mode(
        target
    )

    typer.echo("")
    typer.echo(
        f"TreeForge installation mode is now "
        f"{target.display_name}."
    )
    typer.echo(
        f"Mode recorded in: {mode_file}"
    )


@app.command(
    name="repair",
)
def repair() -> None:
    """
    Reconcile dependencies for the active installation mode.
    """

    repository_root = _repository_root()

    current = read_installation_mode(
        repository_root=repository_root,
    )

    typer.echo(
        f"Repairing TreeForge "
        f"{current.display_name} mode."
    )
    typer.echo("")

    _reconcile_mode(
        current
    )

    mode_file = write_installation_mode(
        current
    )

    typer.echo("")
    typer.echo(
        "TreeForge environment repair completed."
    )
    typer.echo(
        f"Mode recorded in: {mode_file}"
    )
