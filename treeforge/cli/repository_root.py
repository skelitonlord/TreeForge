from __future__ import annotations

from pathlib import Path

import typer


TREEFORGE_ROOT = Path(__file__).resolve().parents[2]
AOSP_ROOT = TREEFORGE_ROOT / "aosp"


def require_treeforge_repository_root() -> Path:
    """
    Require normal TreeForge CLI execution from the repository root.

    TreeForge-owned relative paths such as ./output are intentionally rooted
    in the repository by this CLI contract rather than depending on an
    arbitrary caller working directory.
    """

    current = Path.cwd().resolve()
    expected = TREEFORGE_ROOT.resolve()

    if current != expected:
        typer.echo(
            (
                "TreeForge commands must be run from the repository root:\n"
                f"  {expected}\n"
                f"Current directory:\n"
                f"  {current}"
            ),
            err=True,
        )

        raise typer.Exit(code=2)

    return expected
