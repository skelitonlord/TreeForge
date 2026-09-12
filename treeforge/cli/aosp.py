from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess

import typer

from treeforge.cli.repository_root import (
    AOSP_ROOT,
)


app = typer.Typer(
    help=(
        "Build AOSP products generated and deployed by TreeForge."
    ),
)


_LUNCH_VARIANTS = {
    "eng",
    "user",
    "userdebug",
}


def _resolved_aosp_root(
    value: Path,
) -> Path:
    root = (
        value
        .expanduser()
        .resolve()
    )

    if not root.is_dir():
        raise typer.BadParameter(
            f"AOSP root does not exist: {root}"
        )

    envsetup = (
        root
        / "build"
        / "envsetup.sh"
    )

    if not envsetup.is_file():
        raise typer.BadParameter(
            "AOSP root does not contain "
            f"build/envsetup.sh: {root}"
        )

    return root


def _android_products_files(
    *,
    aosp_root: Path,
) -> tuple[Path, ...]:
    treeforge_device_root = (
        aosp_root
        / "device"
        / "treeforge"
    )

    if not treeforge_device_root.is_dir():
        return ()

    return tuple(
        sorted(
            (
                path
                for path
                in treeforge_device_root.glob(
                    "*/AndroidProducts.mk"
                )
                if path.is_file()
            ),
            key=lambda item: (
                item.as_posix()
            ),
        )
    )


def _strip_make_comment(
    line: str,
) -> str:
    #
    # AndroidProducts.mk lunch declarations should not need escaped
    # literal '#'. Keep this intentionally simple and deterministic.
    #
    return line.split(
        "#",
        1,
    )[0]


def _lunch_choices_from_file(
    path: Path,
) -> tuple[str, ...]:
    text = path.read_text(
        encoding="utf-8",
    )

    lines = text.splitlines()

    values: list[str] = []

    collecting = False

    for raw_line in lines:
        line = _strip_make_comment(
            raw_line
        ).strip()

        if not line:
            if collecting:
                collecting = False

            continue

        if not collecting:
            match = re.match(
                r"^COMMON_LUNCH_CHOICES\s*"
                r"(?::=|\+=|=)\s*(.*)$",
                line,
            )

            if match is None:
                continue

            remainder = (
                match
                .group(1)
                .strip()
            )

            collecting = True

        else:
            remainder = line

        continued = (
            remainder.endswith("\\")
        )

        if continued:
            remainder = (
                remainder[:-1]
                .strip()
            )

        if remainder:
            values.extend(
                remainder.split()
            )

        if not continued:
            collecting = False

    accepted = []

    for value in values:
        if value.startswith("$("):
            continue

        parts = value.rsplit(
            "-",
            2,
        )

        if len(parts) != 3:
            continue

        product, release, variant = (
            parts
        )

        if not product.startswith(
            "treeforge_"
        ):
            continue

        if not release:
            continue

        if variant not in _LUNCH_VARIANTS:
            continue

        accepted.append(
            value
        )

    return tuple(
        sorted(
            set(
                accepted
            )
        )
    )


def _discover_lunch_choices(
    *,
    aosp_root: Path,
) -> tuple[str, ...]:
    choices = []

    for path in _android_products_files(
        aosp_root=aosp_root,
    ):
        choices.extend(
            _lunch_choices_from_file(
                path
            )
        )

    return tuple(
        sorted(
            set(
                choices
            )
        )
    )


def _choose_lunch_target(
    *,
    discovered: tuple[str, ...],
    requested: str | None,
) -> str:
    if not discovered:
        typer.echo(
            "No TreeForge AOSP products are deployed."
        )
        typer.echo("")
        typer.echo(
            "Expected products beneath:"
        )
        typer.echo(
            "  device/treeforge/*/AndroidProducts.mk"
        )

        raise typer.Exit(
            code=2
        )

    if requested is not None:
        if requested not in discovered:
            typer.echo(
                "Requested lunch target is not a "
                "TreeForge-generated product:"
            )
            typer.echo(
                f"  {requested}"
            )
            typer.echo("")
            typer.echo(
                "Available TreeForge lunch targets:"
            )

            for choice in discovered:
                typer.echo(
                    f"  {choice}"
                )

            raise typer.Exit(
                code=2
            )

        return requested

    if len(discovered) == 1:
        selected = discovered[0]

        typer.echo(
            "Detected TreeForge AOSP product:"
        )
        typer.echo(
            f"  {selected}"
        )

        return selected

    typer.echo(
        "Available TreeForge AOSP products:"
    )
    typer.echo("")

    for index, choice in enumerate(
        discovered,
        start=1,
    ):
        typer.echo(
            f"  {index}. {choice}"
        )

    typer.echo("")

    while True:
        selected_index = typer.prompt(
            "Select product",
            type=int,
        )

        if (
            selected_index >= 1
            and selected_index
            <= len(discovered)
        ):
            return discovered[
                selected_index - 1
            ]

        typer.echo(
            "Invalid selection."
        )


@app.command("list")
def list_products(
    aosp_root: Path = typer.Option(
        AOSP_ROOT,
        "--aosp-root",
        help=(
            "AOSP checkout root. Defaults to "
            "TreeForge's configured AOSP checkout."
        ),
    ),
) -> None:
    """
    List AOSP lunch targets generated and deployed by TreeForge.
    """

    resolved_root = _resolved_aosp_root(
        aosp_root
    )

    products = _discover_lunch_choices(
        aosp_root=resolved_root,
    )

    if not products:
        typer.echo(
            "No TreeForge AOSP products are deployed."
        )
        typer.echo(
            "Expected under:"
        )
        typer.echo(
            f"  {resolved_root / 'device' / 'treeforge'}"
        )

        raise typer.Exit(
            code=1
        )

    typer.echo(
        "TreeForge AOSP lunch targets:"
    )

    for product in products:
        typer.echo(
            f"  {product}"
        )


@app.command("build")
def build(
    lunch_target: str | None = typer.Argument(
        None,
        help=(
            "TreeForge lunch target. "
            "Automatically selected when only one "
            "TreeForge product is deployed."
        ),
    ),
    aosp_root: Path = typer.Option(
        AOSP_ROOT,
        "--aosp-root",
        help=(
            "AOSP checkout root. Defaults to "
            "TreeForge's configured AOSP checkout."
        ),
    ),
    out_dir: Path | None = typer.Option(
        None,
        "--out-dir",
        help=(
            "AOSP OUT_DIR override. Defaults to "
            "<AOSP_ROOT>/out-treeforge."
        ),
    ),
) -> None:
    """
    Run a full AOSP build for a TreeForge-generated product.

    The AOSP shell runs in the foreground with its working directory
    set to the AOSP root before build/envsetup.sh is sourced. Standard
    input, output, and error remain attached to the current terminal.
    """

    resolved_root = _resolved_aosp_root(
        aosp_root
    )

    discovered = _discover_lunch_choices(
        aosp_root=resolved_root,
    )

    selected = _choose_lunch_target(
        discovered=discovered,
        requested=lunch_target,
    )

    if out_dir is None:
        resolved_out = (
            resolved_root
            / "out-treeforge"
        )
    else:
        expanded_out = (
            out_dir
            .expanduser()
        )

        if expanded_out.is_absolute():
            resolved_out = (
                expanded_out.resolve()
            )
        else:
            resolved_out = (
                resolved_root
                / expanded_out
            ).resolve()

    #
    # Deliberately inherit stdin/stdout/stderr. Do not pipe, capture,
    # tee, or otherwise hide AOSP's native terminal UI.
    #
    env = os.environ.copy()

    env["OUT_DIR"] = str(
        resolved_out
    )

    typer.echo("")
    typer.echo(
        "TreeForge AOSP build"
    )
    typer.echo(
        f"  AOSP root: {resolved_root}"
    )
    typer.echo(
        f"  Lunch:     {selected}"
    )
    typer.echo(
        f"  OUT_DIR:   {resolved_out}"
    )
    typer.echo("")
    typer.echo(
        "Starting AOSP build in the current terminal..."
    )
    typer.echo("")

    #
    # cwd=resolved_root is intentional and happens before Bash executes.
    # Therefore `source build/envsetup.sh` is run from the AOSP root,
    # matching normal interactive AOSP usage.
    #
    command = (
        'source build/envsetup.sh && '
        'lunch "$1" && '
        'm'
    )

    try:
        completed = subprocess.run(
            [
                "/bin/bash",
                "-c",
                command,
                "treeforge-aosp-build",
                selected,
            ],
            cwd=resolved_root,
            env=env,
            check=False,
        )

    except KeyboardInterrupt:
        raise typer.Exit(
            code=130
        ) from None

    return_code = (
        completed.returncode
    )

    if return_code == 0:
        typer.echo("")
        typer.echo(
            "AOSP build completed successfully."
        )
        typer.echo(
            f"Output: {resolved_out}"
        )
        return

    if return_code < 0:
        return_code = (
            128
            + abs(
                return_code
            )
        )

    typer.echo("")
    typer.echo(
        "AOSP build failed."
    )
    typer.echo(
        f"Exit code: {return_code}"
    )

    raise typer.Exit(
        code=return_code
    )
