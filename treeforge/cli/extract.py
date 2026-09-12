from __future__ import annotations

from pathlib import Path
import logging
import shutil
import sys

import typer

from treeforge.android.application.discover_factory_image import (
    DiscoverFactoryImageRequest,
    DiscoverFactoryImageService,
)
from treeforge.android.extraction.pipeline import (
    AndroidExtractionPipeline,
)
from treeforge.android.partition import (
    PartitionLayoutDetector,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.workspace.workspace import (
    Workspace,
)
from treeforge.cli.progress import (
    clear_live_progress_block,
    configure_live_progress_logging,
    render_progress,
)
from treeforge.cli.stage_reporting import (
    build_extraction_origin_report_lines,
    build_extraction_stage_summary_lines,
)
from treeforge.cli.run_logging import (
    StageTerminalCapture,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
    KnowledgeApplicationStage,
)


app = typer.Typer(
    help=(
        "Discover and physically extract an Android factory image "
        "through TreeForge's canonical Extraction phase."
    )
)


def _build_extraction_report(
    *,
    factory_image: Path,
    extraction_root: Path,
    discovery_result,
    partition_layout,
    partition_inventory,
    extraction,
    knowledge_policy: KnowledgeApplicationPolicy,
    detailed_report_paths: dict[
        str | None,
        str,
    ],
) -> str:
    """
    Render canonical Extraction acceptance state.

    Extraction-owned reporting is delegated to the shared stage reporter so
    every later CLI traversing Extraction exposes the same canonical surface.
    """

    artifacts = tuple(
        extraction.artifacts
    )

    layout_partitions = tuple(
        partition_layout.partitions
    )

    inventory_partitions = tuple(
        partition_inventory.partitions
    )

    available = tuple(
        partition
        for partition
        in layout_partitions
        if (
            partition.payload_state.value
            == "available"
        )
    )

    unavailable = tuple(
        partition
        for partition
        in layout_partitions
        if (
            partition.payload_state.value
            == "unavailable"
        )
    )

    unknown = tuple(
        partition
        for partition
        in layout_partitions
        if (
            partition.payload_state.value
            == "unknown"
        )
    )

    layout_names = {
        partition.name
        for partition
        in layout_partitions
    }

    available_names = {
        partition.name
        for partition
        in available
    }

    unavailable_names = {
        partition.name
        for partition
        in unavailable
    }

    inventory_names = {
        partition.name
        for partition
        in inventory_partitions
    }

    available_missing_inventory = (
        available_names
        - inventory_names
    )

    unavailable_in_inventory = (
        unavailable_names
        & inventory_names
    )

    inventory_without_layout = (
        inventory_names
        - layout_names
    )

    topology_only_excluded = (
        unavailable_names
        - inventory_names
    )

    projection_integrity = (
        not available_missing_inventory
        and not unavailable_in_inventory
        and not inventory_without_layout
    )

    lines: list[str] = [
        "TreeForge Factory Image Extraction Report",
        "",
        f"Factory image: {factory_image}",
        f"Extraction output: {extraction_root}",
        "",
        "Upstream pipeline:",
        "  Discovery: complete",
        "  Knowledge application:",
        (
            "    Discovery: "
            + (
                "ON"
                if knowledge_policy.enabled_for(
                    KnowledgeApplicationStage.DISCOVERY
                )
                else "OFF"
            )
        ),
        (
            "    Partition Layout: "
            + (
                "ON"
                if knowledge_policy.enabled_for(
                    KnowledgeApplicationStage.PARTITION_LAYOUT
                )
                else "OFF"
            )
        ),
        (
            "    Extraction: "
            + (
                "ON"
                if knowledge_policy.enabled_for(
                    KnowledgeApplicationStage.EXTRACTION
                )
                else "OFF"
            )
        ),
        "  Partition Layout: complete",
        "  Extraction: complete",
        "",
        "Canonical upstream state:",
        (
            "  Discovery providers: "
            f"{len(discovery_result.discovery.provider_collection)}"
        ),
        (
            "  Active Discovery artifacts: "
            f"{sum(len(result.artifact_inventory) for result in discovery_result.context.provider_collection.results)}"
        ),
        (
            "  Layout partitions: "
            f"{len(partition_layout.partitions)}"
        ),
        (
            "  Extraction artifacts: "
            f"{len(artifacts)}"
        ),
        "",
        "Partition projection:",
        (
            "  Layout partitions: "
            f"{len(layout_partitions)}"
        ),
        (
            "  Payload available: "
            f"{len(available)}"
        ),
        (
            "  Payload unavailable: "
            f"{len(unavailable)}"
        ),
        (
            "  Payload unknown: "
            f"{len(unknown)}"
        ),
        (
            "  Dynamic groups: "
            f"{len(partition_layout.groups)}"
        ),
        "",
        "Partition Inventory:",
        (
            "  Accessible partitions: "
            f"{len(inventory_partitions)}"
        ),
        (
            "  Topology-only partitions excluded: "
            f"{len(topology_only_excluded)}"
        ),
        (
            "  Available partitions missing from Inventory: "
            f"{len(available_missing_inventory)}"
        ),
        (
            "  Unavailable partitions present in Inventory: "
            f"{len(unavailable_in_inventory)}"
        ),
        (
            "  Inventory partitions absent from Layout: "
            f"{len(inventory_without_layout)}"
        ),
        (
            "  Layout / Inventory integrity: "
            + (
                "PASS"
                if projection_integrity
                else "FAIL"
            )
        ),
        "",
    ]

    lines.extend(
        build_extraction_stage_summary_lines(
            extraction,
            detailed_report_paths=(
                detailed_report_paths
            ),
        )
    )

    lines.append("")

    return "\n".join(
        lines
    )


@app.callback(
    invoke_without_command=True,
)
def extract(
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
            "TreeForge output root. Extraction artifacts are preserved "
            "under OUTPUT/extraction. Defaults to ./output."
        ),
    ),
    device_id: str | None = typer.Option(
        None,
        "--device-id",
        "-d",
        help=(
            "Optional explicit Android device identifier used during "
            "knowledge resolution. When omitted, Discovery may infer it."
        ),
    ),
    board_platform: str | None = typer.Option(
        None,
        "--board-platform",
        "-b",
        help=(
            "Optional explicit Android board platform or SoC identifier "
            "used during knowledge resolution. When omitted, Discovery "
            "may infer it."
        ),
    ),
    android_version: str | None = typer.Option(
        None,
        "--android-version",
        "-a",
        help=(
            "Optional explicit Android version used during knowledge "
            "resolution. When omitted, Discovery may infer it."
        ),
    ),
    knowledge_discovery: bool = typer.Option(
        False,
        "--knowledge-discovery",
        help=(
            "Allow resolved TreeForge Knowledge to contribute "
            "Discovery semantic enrichment. Disabled by default."
        ),
    ),
    knowledge_partition_layout: bool = typer.Option(
        False,
        "--knowledge-partition-layout",
        help=(
            "Allow resolved TreeForge Knowledge to contribute "
            "during Partition Layout. Disabled by default."
        ),
    ),
    knowledge_extraction: bool = typer.Option(
        False,
        "--knowledge-extraction",
        help=(
            "Allow resolved TreeForge Knowledge to contribute "
            "during Extraction. Disabled by default."
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help=(
            "Show additional TreeForge diagnostic logging. Canonical "
            "Extraction progress is shown by default."
        ),
    ),
) -> None:
    """
    Extract a factory image through the canonical Extraction boundary.
    """

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
            "Additional diagnostic logging enabled."
        )

    extraction_root = (
        output
        / "extraction"
    )

    if extraction_root.exists():
        if not extraction_root.is_dir():
            typer.echo(
                (
                    "Extraction destination exists but is not "
                    f"a directory: {extraction_root}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        try:
            shutil.rmtree(
                extraction_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to replace existing Extraction "
                    f"output: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    terminal_capture = (
        StageTerminalCapture(
            extraction_root
        )
    )

    terminal_capture.start()

    ctx.call_on_close(
        terminal_capture.close
    )

    typer.echo(
        "TreeForge Factory Image Extraction"
    )

    workspace = Workspace(
        extraction_root
    )

    host_tools = AndroidHostTools()

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

    typer.echo()
    typer.echo(
        "Knowledge application:"
    )
    typer.echo(
        "  Discovery: "
        f"{'ON' if knowledge_discovery else 'OFF'}"
    )
    typer.echo(
        "  Partition Layout: "
        f"{'ON' if knowledge_partition_layout else 'OFF'}"
    )
    typer.echo(
        "  Extraction: "
        f"{'ON' if knowledge_extraction else 'OFF'}"
    )

    typer.echo()
    typer.echo(
        "Discovering factory image..."
    )

    try:
        discovery_result = (
            DiscoverFactoryImageService(
                progress_callback=render_progress,
                knowledge_application_policy=(
                    knowledge_policy
                ),
            )
            .discover(
                DiscoverFactoryImageRequest(
                    factory_image=factory_image,
                    workspace=workspace,
                    device_id=device_id,
                    board_platform=board_platform,
                    android_version=android_version,
                )
            )
        )
    except Exception as error:
        terminal_capture.log_exception(
            error,
            context="Factory-image Discovery",
        )

        typer.echo(
            (
                "Factory-image Discovery failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    context = (
        discovery_result.context
    )

    provider_collection = (
        context.provider_collection
    )

    if provider_collection is None:
        typer.echo(
            "Discovery did not provide a provider collection.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    typer.echo(
        (
            "Discovery downstream handoff: "
            f"{len(provider_collection.artifacts)} discovered, "
            "0 removed, "
            f"{len(provider_collection.artifacts)} forwarded"
        )
    )

    extraction_pipeline = (
        AndroidExtractionPipeline(
            host_tools=host_tools,
            progress_callback=render_progress,
        )
    )

    typer.echo(
        "Materializing discovered image sources..."
    )

    try:
        extraction_pipeline.materialize_sources(
            context
        )

    except Exception as error:
        terminal_capture.log_exception(
            error,
            context="Factory-image source materialization",
        )

        typer.echo(
            (
                "Factory-image source materialization failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo(
        "Building partition layout..."
    )

    try:
        partition_layout = (
            PartitionLayoutDetector()
            .detect(
                context
            )
        )

        context.partition_layout = (
            partition_layout
        )

    except Exception as error:
        terminal_capture.log_exception(
            error,
            context="Partition Layout",
        )

        typer.echo(
            (
                "Partition Layout failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo(
        "Running canonical post-layout Extraction phase..."
    )

    try:
        extraction_pipeline.continue_after_layout(
            context
        )

    except Exception as error:
        terminal_capture.log_exception(
            error,
            context="Factory-image Extraction",
        )

        typer.echo(
            (
                "Factory-image Extraction failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    extraction = (
        context.android_extraction
    )

    partition_inventory = (
        context.partition_inventory
    )

    if extraction is None:
        typer.echo(
            "Extraction completed without canonical Extraction state.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if partition_inventory is None:
        typer.echo(
            (
                "Extraction completed without canonical "
                "PartitionInventory state."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    reports_root = (
        extraction_root
        / "reports"
    )

    reports_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    origin_images = sorted(
        {
            artifact.origin_image
            for artifact
            in extraction.artifacts
            if artifact.origin_image is not None
        }
    )

    detailed_report_paths: dict[
        str | None,
        str,
    ] = {}

    for origin_image in origin_images:
        safe_name = (
            origin_image
            .replace(
                "/",
                "__",
            )
            .replace(
                "\\",
                "__",
            )
        )

        detail_path = (
            reports_root
            / f"{safe_name}.txt"
        )

        detail_path.write_text(
            "\n".join(
                build_extraction_origin_report_lines(
                    extraction,
                    origin_image,
                )
            )
            + "\n",
            encoding="utf-8",
        )

        detailed_report_paths[
            origin_image
        ] = str(
            detail_path.relative_to(
                output
            )
        )

    if any(
        artifact.origin_image is None
        for artifact
        in extraction.artifacts
    ):
        detail_path = (
            reports_root
            / "no-factory-origin.txt"
        )

        detail_path.write_text(
            "\n".join(
                build_extraction_origin_report_lines(
                    extraction,
                    None,
                )
            )
            + "\n",
            encoding="utf-8",
        )

        detailed_report_paths[
            None
        ] = str(
            detail_path.relative_to(
                output
            )
        )

    report_text = _build_extraction_report(
        factory_image=factory_image,
        extraction_root=extraction_root,
        discovery_result=discovery_result,
        partition_layout=partition_layout,
        partition_inventory=partition_inventory,
        extraction=extraction,
        knowledge_policy=knowledge_policy,
        detailed_report_paths=(
            detailed_report_paths
        ),
    )

    report_path = (
        extraction_root
        / "extraction-report.txt"
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
        f"Detailed reports: {reports_root}"
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
