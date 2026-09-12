from __future__ import annotations

from treeforge.android.universe.init.import_resolution import android_init_inapplicable_source_paths

from collections import Counter
from pathlib import Path, PurePosixPath
import sys
import os
import logging
import shutil
import io
from contextlib import redirect_stdout

import typer

from treeforge.cli.device_universe_report import build_device_universe_report
from treeforge.cli.runtime_linking_report import (
    write_runtime_linking_report,
)

from treeforge.android.application.build_device_universe import (
    BuildAndroidDeviceUniverseRequest,
    BuildAndroidDeviceUniverseService,
)
from treeforge.android.runtime_linking.stage import (
    AndroidRuntimeLinkingStage,
)
from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
    parsing_snapshot_path,
)
from treeforge.android.universe.bootloader import (
    AndroidUniverseBootloaderRequirementFamily,
)
from treeforge.android.universe.relationships import (
    AndroidUniverseArtifactFulfillmentStatus,
    AndroidUniverseInitExecutableArtifactRelationship,
    AndroidUniverseInitOnRestartPropertyCommandRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
)
from treeforge.android.universe.properties.conclusion import (
    AndroidUniverseConclusionStatus,
)
from treeforge.workspace.workspace import (
    Workspace,
)
from treeforge.cli.progress import (
    clear_live_progress_block,
    configure_live_progress_logging,
    render_progress,
)


app = typer.Typer(
    help=(
        "Build Runtime Linking from TreeForge's canonical Parsing "
        "handoff through Android Device Universe. A factory image is "
        "optional and is required only when reparsing is requested."
    )
)


@app.callback(
    invoke_without_command=True,
)
def runtime_linking(
    factory_image: Path | None = typer.Option(
        None,
        "--factory-image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Optional Android factory-image ZIP. Required only when "
            "reparsing instead of using a canonical Parsing snapshot."
        ),
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Device Universe artifacts remain "
            "under OUTPUT/universe and Runtime Linking artifacts are "
            "preserved under OUTPUT/runtime-linking. Defaults to ./output."
        ),
    ),
    device_id: str | None = typer.Option(
        None,
        "--device-id",
        help=(
            "Optional explicit Android device identifier used during "
            "knowledge resolution. When omitted, Discovery may infer it."
        ),
    ),
    board_platform: str | None = typer.Option(
        None,
        "--board-platform",
        help=(
            "Optional explicit Android board platform or SoC identifier "
            "used during knowledge resolution. When omitted, Discovery "
            "may infer it."
        ),
    ),
    android_version: str | None = typer.Option(
        None,
        "--android-version",
        help=(
            "Optional explicit Android version used during knowledge "
            "resolution. When omitted, Discovery may infer it."
        ),
    ),
    generic_only: bool = typer.Option(
        False,
        "--generic-only",
        help=(
            "Use generic Discovery only and skip TreeForge Knowledge "
            "enrichment before Device Universe."
        ),
    ),
    parsing_snapshot: Path | None = typer.Option(
        None,
        "--parsing-snapshot",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Reuse a persisted canonical Android Parsing snapshot "
            "instead of rerunning Discovery through Parsing."
        ),
    ),
    preflight: bool = typer.Option(
        False,
        "--preflight",
        help=(
            "Parse the factory image once and exercise all reachable "
            "Android Device Universe runtime contracts. Independent "
            "failures are collected instead of stopping at the first "
            "Universe error."
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help=(
            "Show additional TreeForge diagnostic logging. Canonical "
            "pipeline progress is shown by default."
        ),
    ),
) -> None:
    """
    Run a factory image through TreeForge and stop after Runtime Linking.
    """

    typer.echo(
        "TreeForge Android Runtime Linking"
    )

    if verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="[TreeForge] %(message)s",
        )

        if sys.stdout.isatty():
            configure_live_progress_logging()
        else:
            logging.getLogger(
                "treeforge"
            ).setLevel(
                logging.INFO
            )

        typer.echo(
            "Verbose progress enabled."
        )

    if (
        generic_only
        and (
            device_id is not None
            or board_platform is not None
            or android_version is not None
        )
    ):
        typer.echo(
            (
                "--generic-only cannot be combined with "
                "--device-id, --board-platform, or --android-version."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    universe_root = (
        output
        / "universe"
    )

    runtime_linking_root = (
        output
        / "runtime-linking"
    )

    if runtime_linking_root.exists():
        if not runtime_linking_root.is_dir():
            typer.echo(
                (
                    "Runtime Linking workspace exists but is not "
                    f"a directory: {runtime_linking_root}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        try:
            shutil.rmtree(
                runtime_linking_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to reset Runtime Linking "
                    f"workspace: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    if universe_root.exists():
        if not universe_root.is_dir():
            typer.echo(
                (
                    "Device Universe workspace exists but is not "
                    f"a directory: {universe_root}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        try:
            shutil.rmtree(
                universe_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to reset Device Universe "
                    f"workspace: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    workspace = Workspace(
        universe_root
    )

    parsing_workspace = Workspace(
        output
        / "parsing"
    )

    canonical_parsing_snapshot = (
        parsing_snapshot_path(
            parsing_workspace
        )
    )

    restored_snapshot = None
    reparse = False

    if parsing_snapshot is not None:
        try:
            restored_snapshot = (
                AndroidParsingSnapshotStore()
                .load(
                    parsing_snapshot
                )
            )
        except Exception as error:
            typer.echo(
                (
                    "Unable to restore Parsing snapshot: "
                    f"{error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

        typer.echo()
        typer.echo(
            "Using canonical Parsing snapshot:"
        )
        typer.echo(
            str(
                parsing_snapshot
            )
        )

    elif canonical_parsing_snapshot.is_file():
        typer.echo()
        typer.echo(
            "Existing Parsing snapshot found:"
        )
        typer.echo(
            str(
                canonical_parsing_snapshot
            )
        )
        typer.echo()
        typer.echo(
            "  1. Use existing Parsing snapshot"
        )
        typer.echo(
            "  2. Reparse factory image"
        )
        typer.echo()

        selection = typer.prompt(
            "Select an option",
            default="1",
        ).strip()

        if selection == "1":
            try:
                restored_snapshot = (
                    AndroidParsingSnapshotStore()
                    .load(
                        canonical_parsing_snapshot
                    )
                )
            except Exception as error:
                typer.echo(
                    (
                        "Unable to restore Parsing snapshot: "
                        f"{error}"
                    ),
                    err=True,
                )

                raise typer.Exit(
                    code=1
                ) from error

            typer.echo()
            typer.echo(
                "Using canonical Parsing snapshot:"
            )
            typer.echo(
                str(
                    canonical_parsing_snapshot
                )
            )

        elif selection == "2":
            reparse = True

            if factory_image is None:
                entered_factory_image = typer.prompt(
                    "Factory-image ZIP"
                ).strip()

                if not entered_factory_image:
                    typer.echo(
                        "Factory-image ZIP path cannot be empty.",
                        err=True,
                    )

                    raise typer.Exit(
                        code=1
                    )

                factory_image = Path(
                    entered_factory_image
                ).expanduser().resolve()

                if not factory_image.exists():
                    typer.echo(
                        (
                            "Factory-image ZIP does not exist: "
                            f"{factory_image}"
                        ),
                        err=True,
                    )

                    raise typer.Exit(
                        code=1
                    )

                if not factory_image.is_file():
                    typer.echo(
                        (
                            "Factory-image ZIP is not a file: "
                            f"{factory_image}"
                        ),
                        err=True,
                    )

                    raise typer.Exit(
                        code=1
                    )

                if not factory_image.stat().st_size:
                    typer.echo(
                        (
                            "Factory-image ZIP is empty: "
                            f"{factory_image}"
                        ),
                        err=True,
                    )

                    raise typer.Exit(
                        code=1
                    )

                typer.echo()
                typer.echo(
                    "Using factory image:"
                )
                typer.echo(
                    str(
                        factory_image
                    )
                )

        else:
            typer.echo(
                "Invalid selection. Choose 1 or 2.",
                err=True,
            )

            raise typer.Exit(
                code=1
            )

    if (
        restored_snapshot is None
        and not reparse
        and not canonical_parsing_snapshot.is_file()
        and factory_image is None
    ):
        typer.echo(
            (
                "No canonical Parsing snapshot was found and "
                "no factory image was supplied."
            ),
            err=True,
        )
        typer.echo(
            (
                "Run `treeforge parse <factory-image>` first "
                "or supply --factory-image."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if (
        reparse
        and parsing_workspace.root.exists()
    ):
        try:
            shutil.rmtree(
                parsing_workspace.root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to reset Parsing "
                    f"workspace: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    typer.echo()
    typer.echo(
        (
            "Building Device Universe from canonical Parsing snapshot..."
            if restored_snapshot is not None
            else "Running factory image through TreeForge..."
        )
    )

    if preflight:
        try:
            preflight_result = (
                BuildAndroidDeviceUniverseService(
                    progress_callback=render_progress,
                )
                .preflight(
                    BuildAndroidDeviceUniverseRequest(
                        factory_image=factory_image,
                        workspace=workspace,
                        parsing_workspace=parsing_workspace,
                        device_id=device_id,
                        board_platform=board_platform,
                        android_version=android_version,
                        generic_only=generic_only,
                        parsing_snapshot=restored_snapshot,
                    )
                )
            )
        except Exception as error:
            typer.echo(
                (
                    "Factory-image Device Universe "
                    "preflight failed before diagnostic "
                    f"execution completed: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

        preflight_report = (
            preflight_result.report
        )

        typer.echo()
        typer.echo(
            "Android Device Universe runtime preflight:"
        )

        for operation in preflight_report.operations:
            status = (
                operation.status.value.upper()
            )

            typer.echo(
                (
                    f"  {status:<4} "
                    f"{operation.step:>2}/30 "
                    f"{operation.name}"
                )
            )

            if operation.error_type is not None:
                typer.echo(
                    (
                        "       "
                        f"{operation.error_type}: "
                        f"{operation.message}"
                    )
                )

            elif (
                operation.status.value == "skip"
                and operation.message
            ):
                typer.echo(
                    (
                        "       "
                        f"{operation.message}"
                    )
                )

        typer.echo()
        typer.echo(
            (
                "  Passed: "
                f"{len(preflight_report.passed)}"
            )
        )
        typer.echo(
            (
                "  Failed: "
                f"{len(preflight_report.failed)}"
            )
        )
        typer.echo(
            (
                "  Skipped: "
                f"{len(preflight_report.skipped)}"
            )
        )

        typer.echo()

        if preflight_report.failed:
            typer.echo(
                "Universe runtime preflight: FAIL"
            )

            raise typer.Exit(
                code=1
            )

        if preflight_result.result is None:
            typer.echo(
                (
                    "Universe runtime preflight passed "
                    "without producing the canonical "
                    "Universe result."
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        typer.echo(
            "Universe runtime preflight: PASS"
        )
        typer.echo(
            (
                "Continuing with validated canonical "
                "Universe result."
            )
        )

        result = preflight_result.result

    else:
        try:
            result = (
                BuildAndroidDeviceUniverseService(
                    progress_callback=render_progress,
                )
                .build(
                    BuildAndroidDeviceUniverseRequest(
                        factory_image=factory_image,
                        workspace=workspace,
                        parsing_workspace=parsing_workspace,
                        device_id=device_id,
                        board_platform=board_platform,
                        android_version=android_version,
                        generic_only=generic_only,
                        parsing_snapshot=restored_snapshot,
                    )
                )
            )
        except Exception as error:
            typer.echo(
                (
                    "Factory-image Device Universe failed: "
                    f"{error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    universe_result = result.universe

    report_text = build_device_universe_report(
        result=result,
        factory_image=(
            factory_image
            if factory_image is not None
            else Path(".")
        ),
        universe_root=universe_root,
        generic_only=generic_only,
    )

    universe_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        universe_root
        / "universe-report.txt"
    )

    report_path.write_text(
        report_text,
        encoding="utf-8",
    )

    typer.echo()
    typer.echo(
        "Advancing Android Device Universe into Runtime Linking..."
    )

    try:
        runtime_linking_result = (
            AndroidRuntimeLinkingStage(
                progress_callback=render_progress,
            )
            .run(
                universe_result,
                semantic_version=(
                    result.android_semantic_version
                ),
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Android Runtime Linking failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    if (
        runtime_linking_result.universe
        is not universe_result
    ):
        raise RuntimeError(
            "Runtime Linking must preserve exact "
            "AndroidDeviceUniverse identity"
        )

    runtime_linking_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    runtime_linking_report_path = (
        runtime_linking_root
        / "runtime-linking-report.txt"
    )

    write_runtime_linking_report(
        runtime_linking_result=runtime_linking_result,
        universe_result=universe_result,
        runtime_linking_report_path=(
            runtime_linking_report_path
        ),
    )

    # Ensure no unfinished live activity block remains before ordinary
    # completion/prompt output.
    if sys.stdout.isatty():
        clear_live_progress_block()

    typer.echo()
    typer.echo(
        "Android Runtime Linking completed successfully."
    )
    typer.echo(
        f"Report: {runtime_linking_report_path}"
    )
    typer.echo(
        f"Universe report preserved: {report_path}"
    )
