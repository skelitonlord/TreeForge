from __future__ import annotations

from collections import Counter
from pathlib import Path
import logging
import shutil
import sys

import typer

from treeforge.android.application.filesystem_metadata_factory_image import (
    FilesystemMetadataFactoryImageRequest,
    FilesystemMetadataFactoryImageService,
)
from treeforge.android.extraction.model import (
    ExtractionOperation,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.cli.progress import (
    clear_live_progress_block,
    configure_live_progress_logging,
    render_progress,
)
from treeforge.cli.run_logging import (
    StageTerminalCapture,
)
from treeforge.cli.stage_reporting import (
    build_extraction_stage_report_lines,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
    KnowledgeApplicationStage,
)
from treeforge.workspace.workspace import (
    Workspace,
)


app = typer.Typer(
    help=(
        "Run an Android factory image through TreeForge's canonical "
        "Filesystem Metadata boundary."
    )
)


def _build_report(
    *,
    factory_image: Path,
    workspace_root: Path,
    result,
    knowledge_policy: KnowledgeApplicationPolicy,
) -> str:
    inventory = (
        result.filesystem_inventory
    )

    entries = tuple(
        inventory.entries
    )

    direct_partition = []
    cpio = []
    other = []

    for entry in entries:
        artifact = (
            entry.artifact
        )

        if (
            artifact.operation
            is ExtractionOperation.CPIO_EXTRACTION
        ):
            cpio.append(
                entry
            )
            continue

        partition = (
            entry.result.partition
        )

        if (
            partition is not None
            and artifact.parent
            is partition.artifact
        ):
            direct_partition.append(
                entry
            )
            continue

        other.append(
            entry
        )

    filesystem_types = Counter(
        entry.result.metadata.filesystem_type
        for entry
        in entries
    )

    total_metadata_entries = sum(
        len(
            entry.result.metadata.entries
        )
        for entry
        in entries
    )

    exact_identity_integrity = all(
        inventory.entry_for_artifact(
            entry.artifact
        )
        is entry
        for entry
        in entries
    )

    lines = [
        "TreeForge Filesystem Metadata Report",
        "",
        f"Factory image: {factory_image}",
        f"Filesystem Metadata output: {workspace_root}",
        "",
        "Upstream pipeline:",
        "  Discovery: complete",
        "  Partition Layout: complete",
        "  Extraction: complete",
        "  Partition Inventory: complete",
        "  Filesystem Metadata: complete",
        "",
        "Knowledge application:",
        (
            "  Discovery: "
            + (
                "ON"
                if knowledge_policy.enabled_for(
                    KnowledgeApplicationStage.DISCOVERY
                )
                else "OFF"
            )
        ),
        (
            "  Partition Layout: "
            + (
                "ON"
                if knowledge_policy.enabled_for(
                    KnowledgeApplicationStage.PARTITION_LAYOUT
                )
                else "OFF"
            )
        ),
        (
            "  Extraction: "
            + (
                "ON"
                if knowledge_policy.enabled_for(
                    KnowledgeApplicationStage.EXTRACTION
                )
                else "OFF"
            )
        ),
        "",
        "Canonical upstream state:",
        (
            "  Layout partitions: "
            f"{len(result.partition_layout.partitions)}"
        ),
        (
            "  Extraction artifacts: "
            f"{len(result.extraction.artifacts)}"
        ),
        (
            "  Inventory partitions: "
            f"{len(result.partition_inventory.partitions)}"
        ),
        "",
        "Filesystem Metadata:",
        (
            "  Canonical filesystem roots: "
            f"{len(entries)}"
        ),
        (
            "  Direct partition filesystems: "
            f"{len(direct_partition)}"
        ),
        (
            "  CPIO / ramdisk filesystems: "
            f"{len(cpio)}"
        ),
        (
            "  Nested / other filesystems: "
            f"{len(other)}"
        ),
        (
            "  Filesystem metadata entries: "
            f"{total_metadata_entries}"
        ),
        (
            "  Exact Extraction artifact identity: "
            + (
                "PASS"
                if exact_identity_integrity
                else "FAIL"
            )
        ),
        "",
        "Filesystem types:",
    ]

    if filesystem_types:
        for filesystem_type, count in sorted(
            filesystem_types.items()
        ):
            lines.append(
                f"  {filesystem_type}: {count}"
            )
    else:
        lines.append(
            "  none"
        )

    lines.extend(
        (
            "",
            "Canonical filesystem roots:",
        )
    )

    for entry in entries:
        artifact = (
            entry.artifact
        )

        partition = (
            entry.partition_name
        )

        if (
            artifact.operation
            is ExtractionOperation.CPIO_EXTRACTION
        ):
            category = "cpio"
        elif (
            entry.result.partition is not None
            and artifact.parent
            is entry.result.partition.artifact
        ):
            category = "partition"
        else:
            category = "nested/other"

        lines.append(
            (
                f"  [{category}] "
                f"{artifact.path} "
                f"type={entry.result.metadata.filesystem_type} "
                f"entries={len(entry.result.metadata.entries)} "
                f"partition={partition or '-'}"
            )
        )

    lines.append(
        ""
    )

    lines.extend(
        build_extraction_stage_report_lines(
            result.extraction
        )
    )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


@app.callback(
    invoke_without_command=True,
)
def filesystem_metadata(
    ctx: typer.Context,
    factory_image: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Android factory-image ZIP. The source archive is never "
            "modified or moved."
        ),
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Filesystem Metadata artifacts are "
            "preserved under OUTPUT/filesystem-metadata."
        ),
    ),
    device_id: str | None = typer.Option(
        None,
        "--device-id",
        "-d",
    ),
    board_platform: str | None = typer.Option(
        None,
        "--board-platform",
        "-b",
    ),
    android_version: str | None = typer.Option(
        None,
        "--android-version",
        "-a",
    ),
    generic_only: bool = typer.Option(
        False,
        "--generic-only",
        help=(
            "Run generic Discovery without TreeForge Knowledge "
            "resolution or enrichment."
        ),
    ),
    knowledge_discovery: bool = typer.Option(
        False,
        "--knowledge-discovery",
        help=(
            "Allow resolved TreeForge Knowledge during Discovery. "
            "Disabled by default."
        ),
    ),
    knowledge_partition_layout: bool = typer.Option(
        False,
        "--knowledge-partition-layout",
        help=(
            "Allow resolved TreeForge Knowledge during Partition Layout. "
            "Disabled by default."
        ),
    ),
    knowledge_extraction: bool = typer.Option(
        False,
        "--knowledge-extraction",
        help=(
            "Allow resolved TreeForge Knowledge during Extraction. "
            "Disabled by default."
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
    ),
) -> None:
    """
    Run a factory image through canonical Filesystem Metadata and stop.
    """

    metadata_root = (
        output
        / "filesystem-metadata"
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

    if metadata_root.exists():
        if not metadata_root.is_dir():
            typer.echo(
                (
                    "Filesystem Metadata destination exists but "
                    f"is not a directory: {metadata_root}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        try:
            shutil.rmtree(
                metadata_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to replace existing Filesystem Metadata "
                    f"output: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    terminal_capture = (
        StageTerminalCapture(
            metadata_root
        )
    )

    terminal_capture.start()

    ctx.call_on_close(
        terminal_capture.close
    )

    typer.echo(
        "TreeForge Filesystem Metadata"
    )

    enabled_knowledge_stages = set()

    if knowledge_discovery:
        enabled_knowledge_stages.add(
            KnowledgeApplicationStage.DISCOVERY
        )

    if knowledge_partition_layout:
        enabled_knowledge_stages.add(
            KnowledgeApplicationStage.PARTITION_LAYOUT
        )

    if knowledge_extraction:
        enabled_knowledge_stages.add(
            KnowledgeApplicationStage.EXTRACTION
        )

    knowledge_policy = (
        KnowledgeApplicationPolicy(
            enabled_stages=frozenset(
                enabled_knowledge_stages
            )
        )
    )

    workspace = (
        Workspace(
            metadata_root
        )
    )

    typer.echo()
    typer.echo(
        "Running factory image through Filesystem Metadata..."
    )

    try:
        result = (
            FilesystemMetadataFactoryImageService(
                host_tools=AndroidHostTools(),
                knowledge_application_policy=knowledge_policy,
                progress_callback=render_progress,
            )
            .run(
                FilesystemMetadataFactoryImageRequest(
                    factory_image=factory_image,
                    workspace=workspace,
                    device_id=device_id,
                    board_platform=board_platform,
                    android_version=android_version,
                    generic_only=generic_only,
                )
            )
        )

    except Exception as error:
        terminal_capture.log_exception(
            error,
            context="Filesystem Metadata",
        )

        typer.echo(
            (
                "Filesystem Metadata failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    report_text = (
        _build_report(
            factory_image=factory_image,
            workspace_root=metadata_root,
            result=result,
            knowledge_policy=knowledge_policy,
        )
    )

    report_path = (
        metadata_root
        / "filesystem-metadata-report.txt"
    )

    report_path.write_text(
        report_text,
        encoding="utf-8",
    )

    if sys.stdout.isatty():
        clear_live_progress_block()

    typer.echo()
    typer.echo(
        f"Report: {report_path}"
    )
    typer.echo(
        (
            "Terminal log: "
            f"{terminal_capture.terminal_log_path}"
        )
    )
    typer.echo(
        (
            "Verbose log: "
            f"{terminal_capture.verbose_log_path}"
        )
    )

    workspace.prune_empty_managed_directories()
