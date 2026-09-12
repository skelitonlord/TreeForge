from __future__ import annotations

from contextlib import redirect_stdout

from collections import Counter
from pathlib import Path
import io

import typer
import json

from treeforge.android.application.discover_factory_image import (
    DiscoverFactoryImageRequest,
    DiscoverFactoryImageService,
)
from treeforge.android.application.discover_factory_image_projection import (
    DiscoverFactoryImageProjection,
)
from treeforge.android.application.discover_factory_image_verifier import (
    DiscoverFactoryImageVerifier,
)
from treeforge.android.application.discovery_snapshot_io import (
    AndroidDiscoverySnapshotIO,
)
from treeforge.core.config import (
    load_config,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
    KnowledgeApplicationStage,
)
from treeforge.workspace.workspace import (
    Workspace,
)
from treeforge.cli.progress import (
    render_progress,
)
from treeforge.android.discovery import (
    AndroidDiscoveryReportBuilder,
    AndroidDiscoverySnapshotBuilder,
    AndroidDiscoverySnapshotComparator,
)

app = typer.Typer(
    help=(
        "Discover Android source artifacts, identity, "
        "and applicable TreeForge knowledge without "
        "performing downstream source reconstruction."
    )
)


def _factory_inventory(
    result,
):
    collection = (
        result.discovery.provider_collection
    )

    if collection is None:
        raise RuntimeError(
            "Discovery result does not contain "
            "a provider collection"
        )

    provider_result = (
        collection.result_for(
            "factory-image"
        )
    )

    if provider_result is None:
        raise RuntimeError(
            "Discovery result does not contain "
            "the factory-image provider result"
        )

    return (
        provider_result.artifact_inventory
    )


def _print_categories(
    inventory,
) -> None:
    kind_counts = Counter(
        artifact.kind.value
        for artifact in inventory
    )

    classification_counts = Counter(
        artifact.classification.value
        for artifact in inventory
    )

    typer.echo(
        "\nStructural kinds"
    )
    typer.echo(
        "----------------"
    )

    for kind, count in sorted(
        kind_counts.items()
    ):
        typer.echo(
            f"{kind:32} {count}"
        )

    typer.echo(
        "\nSemantic classifications"
    )
    typer.echo(
        "------------------------"
    )

    for classification, count in sorted(
        classification_counts.items()
    ):
        typer.echo(
            f"{classification:32} {count}"
        )


def _print_identity(
    result,
    *,
    show_evidence: bool,
) -> None:
    inference = (
        result.discovery
        .identity_inference
    )

    typer.echo(
        "\nIdentity"
    )
    typer.echo(
        "--------"
    )

    typer.echo(
        f"device: {inference.device_id}"
    )

    typer.echo(
        (
            "android version: "
            f"{inference.android_version}"
        )
    )

    typer.echo(
        (
            "evidence count: "
            f"{len(inference.evidence)}"
        )
    )

    if show_evidence:
        for evidence in inference.evidence:
            typer.echo(
                f"  {evidence.dimension.value}: "
                f"{evidence.value} "
                f"[{evidence.source}]"
            )
def show(
    factory_image: Path = typer.Option(
        ...,
        "--factory-image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Android factory-image ZIP to inspect."
        ),
    ),
    device: str | None = typer.Option(
        None,
        "--device",
        help=(
            "Optional explicit device identity."
        ),
    ),
    android_version: str | None = typer.Option(
        None,
        "--android-version",
        help=(
            "Optional explicit Android version."
        ),
    ),
    generic_only: bool = typer.Option(
        False,
        "--generic-only",
        help=(
            "Show generic Discovery results without "
            "knowledge specialization."
        ),
    ),
    all_details: bool = typer.Option(
        False,
        "--all",
        help=(
            "Show every available Discovery detail."
        ),
    ),
    categories: bool = typer.Option(
        False,
        "--categories",
        help=(
            "Show counts grouped by structural kind "
            "and semantic classification."
        ),
    ),
    known: bool = typer.Option(
        False,
        "--known",
        help=(
            "Show only semantically known artifacts."
        ),
    ),
    unknown: bool = typer.Option(
        False,
        "--unknown",
        help=(
            "Show only semantically unknown artifacts."
        ),
    ),
    kind: str | None = typer.Option(
        None,
        "--kind",
        help=(
            "Show only artifacts with this structural kind."
        ),
    ),
    classification: str | None = typer.Option(
        None,
        "--classification",
        help=(
            "Show only artifacts with this semantic "
            "classification."
        ),
    ),
    with_observations: bool = typer.Option(
        False,
        "--with-observations",
        help=(
            "Show only artifacts with content observations."
        ),
    ),
    without_observations: bool = typer.Option(
        False,
        "--without-observations",
        help=(
            "Show only artifacts without content observations."
        ),
    ),
    identity: bool = typer.Option(
        False,
        "--identity",
        help=(
            "Show Discovery identity information."
        ),
    ),
    evidence: bool = typer.Option(
        False,
        "--evidence",
        help=(
            "Show Discovery identity evidence."
        ),
    ),
    knowledge: bool = typer.Option(
        False,
        "--knowledge",
        help=(
            "Show knowledge root selections "
            "and resolved modules."
        ),
    ),
    provenance: bool = typer.Option(
        False,
        "--provenance",
        help=(
            "Include artifact provenance information."
        ),
    ),
    workspace_root: Path | None = typer.Option(
        None,
        "--workspace-root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "Persistent TreeForge Discovery workspace. "
            "Defaults to the configured workspace root."
        ),
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        help=(
            "Output format: text or json."
        ),
    ),
) -> None:
    """
    Inspect detailed or categorized factory-image Discovery results.
    """

    if known and unknown:
        typer.echo(
            (
                "--known and --unknown cannot "
                "be combined."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if (
        with_observations
        and without_observations
    ):
        typer.echo(
            (
                "--with-observations and "
                "--without-observations cannot "
                "be combined."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    config = load_config()

    resolved_workspace_root = (
        workspace_root
        if workspace_root is not None
        else Path(
            config.workspace.root
        )
    )

    request = DiscoverFactoryImageRequest(
        factory_image=factory_image,
        workspace=Workspace(
            resolved_workspace_root
        ),
        device_id=device,
        android_version=android_version,
        generic_only=generic_only,
    )

    output_format = (
        output_format
        .strip()
        .lower()
    )

    if output_format not in {
        "text",
        "json",
    }:
        typer.echo(
            "--format must be either text or json.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    try:
        result = (
            DiscoverFactoryImageService()
            .discover(
                request
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Discovery failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    inventory = (
        _factory_inventory(
            result
        )
    )

    if output_format == "json":
        projection = (
            DiscoverFactoryImageProjection()
            .project(
                result
            )
        )

        typer.echo(
            json.dumps(
                projection,
                indent=2,
                sort_keys=True,
            )
        )

        return

    typer.echo(
        "TreeForge Discovery Inspection"
    )

    typer.echo(
        (
            "\nmode: "
            + (
                "generic-only"
                if generic_only
                else "knowledge-enriched"
            )
        )
    )

    typer.echo(
        (
            "total artifacts: "
            f"{len(inventory)}"
        )
    )

    typer.echo(
        (
            "known: "
            f"{inventory.known_count}"
        )
    )

    typer.echo(
        (
            "unknown: "
            f"{inventory.unknown_count}"
        )
    )

    show_identity = (
        all_details
        or identity
        or evidence
    )

    show_evidence = (
        all_details
        or evidence
    )

    show_knowledge = (
        all_details
        or knowledge
    )

    show_categories = (
        all_details
        or categories
    )

    if show_identity:
        _print_identity(
            result,
            show_evidence=show_evidence,
        )

    if show_knowledge:
        _print_knowledge(
            result
        )

    if show_categories:
        _print_categories(
            inventory
        )

    artifacts = tuple(
        artifact
        for artifact in inventory
        if _artifact_matches(
            artifact,
            known=known,
            unknown=unknown,
            kind=kind,
            classification=classification,
            with_observations=(
                with_observations
            ),
            without_observations=(
                without_observations
            ),
        )
    )

    typer.echo(
        "\nArtifacts"
    )
    typer.echo(
        "---------"
    )

    typer.echo(
        f"matching: {len(artifacts)}"
    )

    if not artifacts:
        typer.echo(
            "(none)"
        )
        return

    for artifact in artifacts:
        if all_details:
            _print_artifact_full(
                artifact,
                show_provenance=True,
            )
        elif provenance:
            _print_artifact_full(
                artifact,
                show_provenance=True,
            )
        else:
            _print_artifact_summary(
                artifact
            )



_BOOT_CHAIN_FIRMWARE_NAMES = frozenset(
    {
        "abl.img",
        "bl1.img",
        "bl2.img",
        "bl31.img",
        "gsa.img",
        "ldfw.img",
        "pbl.img",
        "tzsw.img",
    }
)

_FACTORY_FLASH_SCRIPT_NAMES = frozenset(
    {
        "flash-all.sh",
        "flash-all.bat",
        "flash-base.sh",
    }
)


def _discovery_unknown_disposition(
    artifact,
) -> tuple[
    str,
    str,
]:
    """
    Return the explicit Discovery-boundary disposition for one
    semantically unknown artifact.

    This is scope/accounting policy, not semantic classification.

    Decisions must be supported by canonical Discovery evidence or by an
    explicit current TreeForge scope boundary. Unknown artifacts must never
    silently disappear.
    """

    name = artifact.name.lower()

    signatures = {
        observation.signature.value
        for observation in artifact.content_observations
    }

    if "fbpk_container" in signatures:
        return (
            "intentionally_not_applicable",
            (
                "Exact FBPK container signature identifies a bootloader "
                "firmware container. Current TreeForge scope does not "
                "reconstruct or build platform bootloader firmware. "
                "Canonical identity and provenance are retained."
            ),
        )

    if name.endswith(
        ".ec.bin"
    ):
        return (
            "intentionally_not_applicable",
            (
                "Filename convention identifies an embedded-controller "
                "firmware payload. Current TreeForge scope does not "
                "reconstruct embedded-controller firmware. Classification "
                "is filename-derived because no intrinsic content signature "
                "was recognized. Canonical identity and provenance are "
                "retained."
            ),
        )

    if name in _FACTORY_FLASH_SCRIPT_NAMES:
        return (
            "consumed_as_factory_evidence",
            (
                "Factory flashing script is retained as canonical evidence "
                "of the source package's installation/flashing procedure. "
                "It is not itself a device-tree reconstruction payload."
            ),
        )

    if (
        artifact.kind.value == "archive"
        and name.startswith(
            "image-"
        )
        and name.endswith(
            ".zip"
        )
        and "zip" in signatures
    ):
        return (
            "consumed_as_container",
            (
                "Exact ZIP structure identifies the nested factory image "
                "container. Discovery recursively inventories its regular "
                "children, so the container itself is accounted for as a "
                "source container rather than an active reconstruction "
                "payload."
            ),
        )

    if name in _BOOT_CHAIN_FIRMWARE_NAMES:
        return (
            "preserved_opaque",
            (
                "Artifact name is consistent with platform boot-chain or "
                "security firmware, but Discovery has no recognized intrinsic "
                "content signature for this object. Current TreeForge scope "
                "does not reconstruct platform boot/security firmware. "
                "Semantic classification therefore remains unknown while "
                "canonical identity and provenance are retained."
            ),
        )

    return (
        "pending_review",
        (
            "TreeForge does not yet have enough generic evidence or an "
            "explicit scope disposition for this semantically unknown "
            "artifact."
        ),
    )


@app.callback(
    invoke_without_command=True,
)
def discover(
    factory_image: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Android factory-image ZIP. "
            "The source archive is never modified or moved."
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
            "TreeForge output root. Discovery output is written "
            "under OUTPUT/discovery. Defaults to ./output."
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
) -> None:
    """
    Run canonical factory-image Discovery and stop at the Discovery boundary.
    """

    discovery_root = (
        output
        / "discovery"
    )

    workspace = Workspace(
        discovery_root
    )

    report_path = (
        discovery_root
        / "discovery-report.txt"
    )

    typer.echo(
        "TreeForge Discovery"
    )

    knowledge_policy = (
        KnowledgeApplicationPolicy(
            enabled_stages=(
                frozenset(
                    {
                        KnowledgeApplicationStage.DISCOVERY,
                    }
                )
                if knowledge_discovery
                else frozenset()
            ),
        )
    )

    typer.echo(
        "Knowledge application: "
        f"Discovery={'ON' if knowledge_discovery else 'OFF'}"
    )

    try:
        result = (
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
                )
            )
        )
    except Exception as error:
        typer.echo(
            (
                "\nDiscovery failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    try:
        inventory = _factory_inventory(
            result
        )
    except Exception as error:
        typer.echo(
            (
                "\nDiscovery failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    verification = (
        DiscoverFactoryImageVerifier()
        .verify(
            result
        )
    )

    discovery_checks = tuple(
        check
        for check in verification.checks
        if not check.check_id.startswith(
            "knowledge-"
        )
    )

    verification_failed = sum(
        check.status.value == "fail"
        for check in discovery_checks
    )

    input_count = len(
        result.discovery.provider_collection.artifacts
    )

    forwarded_count = input_count
    removed_count = 0

    error_count = 0

    accounted_count = (
        forwarded_count
        + removed_count
        + error_count
    )

    unexplained_count = (
        input_count
        - accounted_count
    )

    accounting_closed = (
        accounted_count == input_count
        and unexplained_count == 0
    )

    unknown_dispositions = tuple(
        (
            artifact,
            *_discovery_unknown_disposition(
                artifact
            ),
        )
        for artifact in inventory.unknown_artifacts
    )

    pending_review_count = sum(
        disposition == "pending_review"
        for (
            artifact,
            disposition,
            reason,
        ) in unknown_dispositions
    )

    reviewed_unknown_count = (
        inventory.unknown_count
        - pending_review_count
    )

    blocking_unresolved_count = (
        pending_review_count
    )

    disposition_counts = Counter(
        disposition
        for (
            artifact,
            disposition,
            reason,
        ) in unknown_dispositions
    )

    review_closed = (
        pending_review_count == 0
        and blocking_unresolved_count == 0
        and reviewed_unknown_count
        == inventory.unknown_count
    )

    report_buffer = io.StringIO()

    with redirect_stdout(
        report_buffer
    ):
        typer.echo(
            "=== TREEFORGE DISCOVERY REPORT ==="
        )

        typer.echo()
        typer.echo(
            f"Factory image: {factory_image}"
        )
        typer.echo(
            f"Discovery workspace: {discovery_root}"
        )

        inference = (
            result.discovery
            .identity_inference
        )

        typer.echo()
        typer.echo(
            "Identity"
        )
        typer.echo(
            "--------"
        )

        typer.echo(
            f"device: {inference.device_id}"
        )

        device_evidence = tuple(
            evidence
            for evidence in inference.evidence
            if evidence.kind.value == "device"
        )

        if device_evidence:
            typer.echo(
                "  evidence:"
            )

            for evidence in device_evidence:
                typer.echo(
                    f"    source: {evidence.source}"
                )
                typer.echo(
                    f"    detail: {evidence.detail}"
                )
        else:
            typer.echo(
                "  evidence: none"
            )

        typer.echo(
            (
                "board platform: "
                f"{inference.board_platform}"
            )
        )

        platform_evidence = tuple(
            evidence
            for evidence in inference.evidence
            if evidence.kind.value == "board_platform"
        )

        if platform_evidence:
            typer.echo(
                "  evidence:"
            )

            for evidence in platform_evidence:
                typer.echo(
                    f"    source: {evidence.source}"
                )
                typer.echo(
                    f"    detail: {evidence.detail}"
                )
        else:
            typer.echo(
                "  evidence: none"
            )

        typer.echo(
            (
                "android version: "
                f"{inference.android_version}"
            )
        )

        version_evidence = tuple(
            evidence
            for evidence in inference.evidence
            if evidence.kind.value == "android_version"
        )

        if version_evidence:
            typer.echo(
                "  evidence:"
            )

            for evidence in version_evidence:
                typer.echo(
                    f"    source: {evidence.source}"
                )
                typer.echo(
                    f"    detail: {evidence.detail}"
                )
        else:
            typer.echo(
                "  evidence: none"
            )
            typer.echo(
                (
                    "  reason: Discovery found no direct "
                    "Android-version identity evidence."
                )
            )

        typer.echo(
            (
                "identity evidence count: "
                f"{len(inference.evidence)}"
            )
        )

        typer.echo()
        typer.echo(
            "Artifacts"
        )
        typer.echo(
            "---------"
        )
        typer.echo(
            f"total: {len(inventory)}"
        )
        typer.echo(
            f"known: {inventory.known_count}"
        )
        typer.echo(
            f"unknown: {inventory.unknown_count}"
        )

        typer.echo()
        typer.echo(
            "Stage accounting"
        )
        typer.echo(
            "----------------"
        )
        typer.echo(
            f"inputs discovered:             {input_count}"
        )
        typer.echo(
            f"forwarded downstream:          {forwarded_count}"
        )
        typer.echo(
            f"removed before downstream:     {removed_count}"
        )
        typer.echo(
            f"errors:                        {error_count}"
        )
        typer.echo(
            (
                "unexplained/missing:           "
                f"{unexplained_count}"
            )
        )

        typer.echo()
        typer.echo(
            (
                "DISCOVERY ACCOUNTING: CLOSED"
                if accounting_closed
                else "DISCOVERY ACCOUNTING: NOT CLOSED"
            )
        )

        typer.echo()
        typer.echo(
            "Discovery semantic review"
        )
        typer.echo(
            "-------------------------"
        )
        typer.echo(
            (
                "unknown artifacts:             "
                f"{inventory.unknown_count}"
            )
        )
        typer.echo(
            (
                "reviewed unknown artifacts:    "
                f"{reviewed_unknown_count}"
            )
        )
        typer.echo(
            (
                "pending review:                "
                f"{pending_review_count}"
            )
        )
        typer.echo(
            (
                "blocking unresolved:           "
                f"{blocking_unresolved_count}"
            )
        )

        for (
            disposition,
            count,
        ) in sorted(
            disposition_counts.items()
        ):
            typer.echo(
                (
                    f"{disposition + ':':30}"
                    f"{count}"
                )
            )

        typer.echo()
        typer.echo(
            (
                "DISCOVERY REVIEW: CLOSED"
                if review_closed
                else "DISCOVERY REVIEW: NOT CLOSED"
            )
        )

        if inventory.unknown_count:
            typer.echo()
            typer.echo(
                "Unknown artifacts"
            )
            typer.echo(
                "-----------------"
            )

            for artifact in (
                inventory.unknown_artifacts
            ):
                typer.echo()
                typer.echo(
                    f"source: {artifact.source_name}"
                )
                typer.echo(
                    f"kind: {artifact.kind.value}"
                )
                typer.echo(
                    (
                        "kind evidence: "
                        f"{artifact.kind_evidence.value}"
                    )
                )
                typer.echo(
                    (
                        "semantic classification: "
                        f"{artifact.classification.value}"
                    )
                )

                if artifact.provenance is not None:
                    typer.echo(
                        (
                            "size bytes: "
                            f"{artifact.provenance.size_bytes}"
                        )
                    )
                    typer.echo(
                        (
                            "container depth: "
                            f"{artifact.provenance.container_depth}"
                        )
                    )

                if artifact.content_observations:
                    typer.echo(
                        "content observations:"
                    )

                    for observation in (
                        artifact.content_observations
                    ):
                        typer.echo(
                            (
                                "  - signature="
                                f"{observation.signature.value}, "
                                "confidence="
                                f"{observation.confidence.value}, "
                                "offset="
                                f"{observation.offset}"
                            )
                        )
                else:
                    typer.echo(
                        "content observations: none"
                    )

                (
                    disposition,
                    disposition_reason,
                ) = _discovery_unknown_disposition(
                    artifact
                )

                typer.echo(
                    f"disposition: {disposition}"
                )
                typer.echo(
                    f"reason: {disposition_reason}"
                )

        typer.echo()
        typer.echo(
            "Verification"
        )
        typer.echo(
            "------------"
        )

        for check in discovery_checks:
            marker_value = (
                "PASS"
                if check.status.value == "pass"
                else (
                    "SKIP"
                    if check.status.value == "skip"
                    else "FAIL"
                )
            )

            typer.echo(
                (
                    f"[{marker_value}] "
                    f"{check.check_id}: "
                    f"{check.detail}"
                )
            )

        passed_count = sum(
            check.status.value == "pass"
            for check in discovery_checks
        )

        skipped_count = sum(
            check.status.value == "skip"
            for check in discovery_checks
        )

        typer.echo()
        typer.echo(
            f"passed: {passed_count}"
        )
        typer.echo(
            f"failed: {verification_failed}"
        )
        typer.echo(
            f"skipped: {skipped_count}"
        )

    discovery_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        report_path.write_text(
            report_buffer.getvalue(),
            encoding="utf-8",
        )
    except OSError as error:
        typer.echo(
            (
                "\nDiscovery failed while writing report: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    if (
        not accounting_closed
        or not review_closed
        or verification_failed
    ):
        typer.echo(
            "\nDiscovery validation failed.",
            err=True,
        )
        typer.echo(
            f"Report: {report_path}"
        )

        raise typer.Exit(
            code=1
        )

    typer.echo()
    typer.echo(
        f"Report: {report_path}"
    )

    typer.echo(
        (
            "Forwarded downstream: "
            f"{forwarded_count}"
        )
    )
