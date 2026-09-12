from __future__ import annotations

from pathlib import Path

import typer

from treeforge.android.aosp_preflight import (
    AndroidAospPreflight,
)
from treeforge.cli.repository_root import (
    AOSP_ROOT,
)


app = typer.Typer(
    help=(
        "Validate a frozen TreeForge Device Tree against the "
        "downstream AOSP workspace before starting a full "
        "Soong/Ninja generation."
    )
)


@app.callback(
    invoke_without_command=True,
)
def aosp_preflight(
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. "
            "Defaults to ./output."
        ),
    ),
    aosp_root: Path = typer.Option(
        AOSP_ROOT,
        "--aosp-root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "AOSP workspace to validate. "
            "Defaults to the repository AOSP workspace."
        ),
    ),
    product: str | None = typer.Option(
        None,
        "--product",
        help=(
            "Optional Android product override. "
            "Defaults to aosp_<Device Tree device>."
        ),
    ),
    release: str = typer.Option(
        "trunk_staging",
        "--release",
        help=(
            "Android lunch release name."
        ),
    ),
    variant: str = typer.Option(
        "userdebug",
        "--variant",
        help=(
            "Android build variant."
        ),
    ),
    skip_dumpvars: bool = typer.Option(
        False,
        "--skip-dumpvars",
        help=(
            "Run only TreeForge static AOSP-consumption checks "
            "and skip Android's dumpvars configuration parse."
        ),
    ),
) -> None:
    """
    Run the cheap AOSP-consumption gate before a full Soong generation.
    """

    repository_root = (
        Path.cwd()
        .resolve()
    )

    report_root = (
        output
        / "aosp-preflight"
    )

    report_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        report_root
        / "aosp-preflight-report.txt"
    )

    typer.echo(
        "TreeForge AOSP Preflight"
    )
    typer.echo()

    try:
        result = (
            AndroidAospPreflight()
            .run(
                repository_root=(
                    repository_root
                ),
                output_root=output,
                aosp_root=aosp_root,
                product=product,
                release=release,
                variant=variant,
                run_dumpvars=(
                    not skip_dumpvars
                ),
            )
        )

    except Exception as error:
        report_path.write_text(
            (
                "TreeForge AOSP Preflight\n\n"
                "=== AOSP PREFLIGHT ===\n"
                "Status: FAILED\n\n"
                f"Error: {error}\n"
            ),
            encoding="utf-8",
        )

        typer.echo(
            (
                "AOSP preflight failed: "
                f"{error}"
            ),
            err=True,
        )

        typer.echo(
            f"Report: {report_path}"
        )

        raise typer.Exit(
            code=1
        ) from error

    report = (
        result.render()
    )

    report_path.write_text(
        report,
        encoding="utf-8",
    )

    for check in result.checks:
        typer.echo(
            (
                f"[{check.status.value}] "
                f"{check.check_id}: "
                f"{check.summary}"
            )
        )

        for detail in check.details:
            typer.echo(
                f"  {detail}"
            )

    typer.echo()

    if result.passed:
        typer.echo(
            "AOSP preflight: PASS"
        )
        typer.echo(
            "Safe to proceed to the full Soong generation gate."
        )

    else:
        typer.echo(
            "AOSP preflight: FAIL",
            err=True,
        )
        typer.echo(
            (
                "Do not start the full Soong generation "
                "until these blockers are resolved."
            ),
            err=True,
        )

    typer.echo(
        f"Report: {report_path}"
    )

    if not result.passed:
        raise typer.Exit(
            code=1
        )
