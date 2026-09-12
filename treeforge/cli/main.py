import typer

from treeforge.cli.lazy_group import (
    TreeForgeLazyGroup,
)

from treeforge.cli import discover
from treeforge.cli import doctor
from treeforge.cli import extract
from treeforge.cli import filesystem_metadata
from treeforge.cli import parse
from treeforge.cli import boot_image
from treeforge.cli import bootstrap
from treeforge.cli import recovery
from treeforge.cli import version
from treeforge.cli import setup
from treeforge.cli import aosp_preflight
from treeforge.cli import aosp


from treeforge.cli import build as build_cli

app = typer.Typer(
    help="TreeForge - Android Device Bring-up Framework",
    cls=TreeForgeLazyGroup,
)


_BRINGUP_COMMANDS = frozenset(
    {
        "discover",
        "extract",
        "filesystem-metadata",
        "parse",
        "boot-image",
        "bootstrap",
        "universe",
        "runtime-linking",
        "reconstruction",
        "device-tree",
        "install",
        "repartition",
        "aosp",
    }
)


@app.callback()
def main(
    ctx: typer.Context,
) -> None:
    """
    Enforce repository-root and installation-capability CLI contracts.
    """

    from pathlib import Path

    from treeforge.cli.repository_root import (
        require_treeforge_repository_root,
    )
    from treeforge.setup.mode import (
        InstallationCapabilityError,
        require_bringup_mode,
    )

    require_treeforge_repository_root()

    if ctx.invoked_subcommand not in _BRINGUP_COMMANDS:
        return

    try:
        require_bringup_mode(
            repository_root=Path.cwd().resolve(),
        )
    except InstallationCapabilityError as exc:
        typer.echo(
            "This command requires TreeForge "
            "Maintainer mode or higher."
        )
        typer.echo("")
        typer.echo(
            f"Current installation mode: "
            f"{exc.current_mode.display_name}"
        )
        typer.echo("")
        typer.echo(
            "Maintainer mode enables factory-image analysis, "
            "reconstruction, and new-device bring-up."
        )
        typer.echo("")
        typer.echo("Run:")
        typer.echo(
            "  treeforge setup mode maintainer"
        )

        raise typer.Exit(
            code=2
        ) from exc


app.add_typer(
    version.app,
    name="version",
)

app.add_typer(
    doctor.app,
    name="doctor",
)


app.add_typer(
    setup.app,
    name="setup",
)

app.add_typer(
    discover.app,
    name="discover",
)

app.add_typer(
    extract.app,
    name="extract",
)

app.add_typer(
    filesystem_metadata.app,
    name="filesystem-metadata",
)

app.add_typer(
    parse.app,
    name="parse",
)


app.add_typer(
    boot_image.app,
    name="boot-image",
)


app.add_typer(
    bootstrap.app,
    name="bootstrap",
)


app.add_typer(
    recovery.app,
    name="recovery",
)

app.add_typer(
    aosp_preflight.app,
    name="aosp-preflight",
)

app.add_typer(
    aosp.app,
    name="aosp",
)

app.add_typer(
    build_cli.app,
    name="build",
)
