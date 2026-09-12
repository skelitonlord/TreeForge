from __future__ import annotations

from treeforge.android.universe.init.import_resolution import android_init_inapplicable_source_paths

from collections import Counter
from pathlib import Path, PurePosixPath, PurePosixPath
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

from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
)

from treeforge.android.universe.relationships.model import (
    AndroidUniverseInitExecutableArtifactRelationship,
    AndroidUniverseInitExecutableSelinuxRelationship,
    AndroidUniverseInitInterfaceVintfRelationship,
    AndroidUniverseInitSeclabelSelinuxRelationship,
)
from treeforge.android.application.build_device_universe import (
    BuildAndroidDeviceUniverseRequest,
    BuildAndroidDeviceUniverseService,
)
from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
    parsing_snapshot_path,
)
from treeforge.android.universe.relationships import (
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
        "Run an Android factory image through TreeForge's canonical "
        "pipeline and stop after Android Device Universe."
    )
)


@app.callback(
    invoke_without_command=True,
)
def reconstruction(
    factory_image: Path | None = typer.Option(
        None,
        "--factory-image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Optional factory-image override for rebuilding the upstream "
            "Android Device Universe. Normally Reconstruction continues "
            "through the canonical Universe pipeline."
        ),
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Device Universe workspace artifacts "
            "are preserved under OUTPUT/universe. Defaults to ./output."
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
            "Optional explicit canonical Parsing snapshot override for "
            "upstream Universe orchestration."
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
    show_report_paths: bool = typer.Option(
        True,
        hidden=True,
    ),
) -> AndroidReconstructionResult:
    """
    Run the canonical TreeForge pipeline through Android Device Universe
    and continue into Reconstruction Planning.
        """

    typer.echo(
        "TreeForge Android Reconstruction"
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

        typer.echo()
        typer.echo(
            "Replacing existing Device Universe workspace:"
        )
        typer.echo(
            str(
                universe_root
            )
        )
        typer.echo()

        try:
            shutil.rmtree(
                universe_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to replace existing Device Universe "
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

    reconstruction_root = (
        output
        / "reconstruction"
    )

    if reconstruction_root.exists():
        if not reconstruction_root.is_dir():
            typer.echo(
                (
                    "Reconstruction workspace exists but is not "
                    f"a directory: {reconstruction_root}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        typer.echo()
        typer.echo(
            "Replacing existing Reconstruction workspace:"
        )
        typer.echo(
            str(
                reconstruction_root
            )
        )
        typer.echo()

        try:
            shutil.rmtree(
                reconstruction_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to replace existing Reconstruction "
                    f"workspace: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    reconstruction_workspace = Workspace(
        reconstruction_root
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

        else:
            typer.echo(
                "Invalid selection. Choose 1 or 2.",
                err=True,
            )

            raise typer.Exit(
                code=1
            )


    elif parsing_workspace.root.exists():
        typer.echo()
        typer.echo(
            "Existing Parsing output was found:"
        )
        typer.echo(
            str(
                parsing_workspace.root
            )
        )
        typer.echo()
        typer.echo(
            "No reusable Parsing snapshot was found."
        )
        typer.echo(
            "The existing Parsing output cannot be restored as "
            "canonical Parsing state."
        )
        typer.echo()
        typer.echo(
            "  1. Reparse factory image"
        )
        typer.echo(
            "  2. Preserve existing output and cancel"
        )
        typer.echo()

        selection = typer.prompt(
            "Select an option",
            default="1",
        ).strip()

        if selection == "1":
            reparse = True

        elif selection == "2":
            typer.echo()
            typer.echo(
                "Reconstruction cancelled. Existing Parsing "
                "output was preserved."
            )

            raise typer.Exit(
                code=0
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
        "Running factory image through TreeForge..."
    )

    if preflight:
        try:
            preflight_result = (
                BuildAndroidDeviceUniverseService(
                    progress_callback=render_progress,
                )
                .preflight(
                    BuildAndroidDeviceUniverseRequest(
                        factory_image=(
                            factory_image
                            if factory_image is not None
                            else Path(".")
                        ),
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
                        factory_image=(
                            factory_image
                            if factory_image is not None
                            else Path(".")
                        ),
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

    # Ensure no unfinished live activity block remains before ordinary
    # completion/prompt output.
    if sys.stdout.isatty():
        clear_live_progress_block()

    typer.echo()
    typer.echo(
        "Android Device Universe completed successfully."
    )
    if show_report_paths:
        typer.echo(
            f"Report: {report_path}"
        )


    typer.echo()
    typer.echo(
        "=== RUNTIME LINKING ==="
    )

    try:
        from treeforge.android.runtime_linking.stage import (
            AndroidRuntimeLinkingStage,
        )

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
                "Runtime Linking failed: "
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

    runtime_linking_root = (
        output
        / "runtime-linking"
    )

    runtime_linking_report_path = (
        runtime_linking_root
        / "runtime-linking-report.txt"
    )

    write_runtime_linking_report(
        runtime_linking_result=(
            runtime_linking_result
        ),
        universe_result=(
            universe_result
        ),
        runtime_linking_report_path=(
            runtime_linking_report_path
        ),
    )

    if sys.stdout.isatty():
        clear_live_progress_block()

    typer.echo(
        "Runtime Linking completed successfully."
    )
    if show_report_paths:
        typer.echo(
            f"Report: {runtime_linking_report_path}"
        )

    #
    # Reconstruction Ownership
    #
    typer.echo()
    typer.echo(
        "=== RECONSTRUCTION OWNERSHIP ==="
    )

    try:
        from treeforge.android.reconstruction_ownership.stage import (
            AndroidReconstructionOwnershipStage,
        )

        ownership_result = (
            AndroidReconstructionOwnershipStage()
            .resolve(
                universe_result,
                runtime_linking=(
                    runtime_linking_result
                ),
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Reconstruction Ownership failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    ownership_root = (
        output
        / "reconstruction-ownership"
    )

    ownership_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    ownership_report_path = (
        ownership_root
        / "reconstruction-ownership-report.txt"
    )

    ownership_domain_counts = {}

    for decision in ownership_result.decisions:
        domain = decision.domain.value

        ownership_domain_counts[domain] = (
            ownership_domain_counts.get(
                domain,
                0,
            )
            + 1
        )

    artifact_decisions = tuple(
        decision
        for decision in ownership_result.decisions
        if decision.requirement_kind == "artifact"
    )

    artifact_evidence = (
        ownership_result.artifact_evidence
    )

    if artifact_evidence is None:
        raise RuntimeError(
            "Reconstruction Ownership did not produce "
            "canonical artifact evidence"
        )

    canonical_artifact_evidence = (
        artifact_evidence.evidence
    )

    unclassified_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if (
            item.artifact.disposition.value
            == "unclassified"
        )
    )

    elf_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_elf_evidence
    )

    kernel_module_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_kernel_module_evidence
    )

    unclassified_elf_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_elf_evidence
    )

    unclassified_kernel_module_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_kernel_module_evidence
    )

    init_executable_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_init_executable_evidence
    )

    unclassified_init_executable_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_init_executable_evidence
    )

    unclassified_init_only_new_coverage = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            item.has_init_executable_evidence
            and not item.has_elf_evidence
            and not item.has_kernel_module_evidence
        )
    )

    classpath_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_classpath_evidence
    )

    unclassified_classpath_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_classpath_evidence
    )

    unclassified_classpath_new_coverage = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            item.has_classpath_evidence
            and not item.has_elf_evidence
            and not item.has_kernel_module_evidence
            and not item.has_init_executable_evidence
        )
    )

    java_archive_backed_artifact_evidence = tuple(
        item
        for item
        in canonical_artifact_evidence
        if item.has_java_archive_evidence
    )

    unclassified_java_archive_backed = tuple(
        item
        for item
        in unclassified_artifact_evidence
        if item.has_java_archive_evidence
    )

    shell_script_backed_artifact_evidence = tuple(
        item
        for item
        in canonical_artifact_evidence
        if item.has_shell_script_evidence
    )

    unclassified_shell_script_backed = tuple(
        item
        for item
        in unclassified_artifact_evidence
        if item.has_shell_script_evidence
    )

    shell_classpath_reference_artifact_evidence = tuple(
        item
        for item
        in canonical_artifact_evidence
        if item.has_shell_classpath_reference_evidence
    )

    shell_reconciliation = (
        runtime_linking_result
        .universe
        .shell_script_reconciliation
    )

    shell_app_process_wrapper_count = sum(
        1
        for association
        in shell_reconciliation.associations
        if association.app_process_execs
    )

    shell_classpath_resolution_count = sum(
        len(
            association.classpath_resolutions
        )
        for association
        in shell_reconciliation.associations
    )

    shell_classpath_status_counts = {}

    for association in shell_reconciliation.associations:
        for resolution in (
            association.classpath_resolutions
        ):
            key = resolution.status.value

            shell_classpath_status_counts[key] = (
                shell_classpath_status_counts.get(
                    key,
                    0,
                )
                + 1
            )

    apk_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_apk_evidence
    )

    apk_package_evidence_entries = tuple(
        requirement
        for item in apk_backed_artifact_evidence
        for requirement in item.apk_package_requirements
    )

    unclassified_apk_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_apk_evidence
    )

    unclassified_apk_new_coverage = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            item.has_apk_evidence
            and not item.has_elf_evidence
            and not item.has_kernel_module_evidence
            and not item.has_init_executable_evidence
            and not item.has_classpath_evidence
        )
    )

    apex_membership_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_apex_membership_evidence
    )

    unclassified_apex_membership_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_apex_membership_evidence
    )

    unclassified_apex_new_coverage = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            item.has_apex_membership_evidence
            and not item.has_elf_evidence
            and not item.has_kernel_module_evidence
            and not item.has_init_executable_evidence
            and not item.has_classpath_evidence
            and not item.has_apk_evidence
        )
    )

    runtime_linking_backed_artifact_evidence = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_runtime_linking_evidence
    )

    runtime_linking_candidate_artifacts = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_runtime_linking_candidate_evidence
    )

    runtime_linking_root_artifacts = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_runtime_linking_root_evidence
    )

    runtime_linking_consumer_artifacts = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_runtime_linking_consumer_evidence
    )

    runtime_linking_provider_artifacts = tuple(
        item
        for item in canonical_artifact_evidence
        if item.has_runtime_linking_provider_evidence
    )

    unclassified_runtime_linking_backed = tuple(
        item
        for item in unclassified_artifact_evidence
        if item.has_runtime_linking_evidence
    )

    unclassified_runtime_linking_new_coverage = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            item.has_runtime_linking_evidence
            and not item.has_elf_evidence
            and not item.has_kernel_module_evidence
            and not item.has_init_executable_evidence
            and not item.has_classpath_evidence
            and not item.has_apk_evidence
            and not item.has_apex_membership_evidence
        )
    )

    unclassified_without_elf_or_kernel = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            not item.has_elf_evidence
            and not item.has_kernel_module_evidence
        )
    )

    unclassified_without_current_evidence = tuple(
        item
        for item in unclassified_artifact_evidence
        if (
            not item.has_elf_evidence
            and not item.has_kernel_module_evidence
            and not item.has_init_executable_evidence
            and not item.has_classpath_evidence
            and not item.has_java_archive_evidence
            and not item.has_shell_script_evidence
            and not item.has_shell_classpath_reference_evidence
            and not item.has_apk_evidence
            and not item.has_apex_membership_evidence
        )
    )

    residual_kind_counts = {}
    residual_deployment_role_counts = {}
    residual_suffix_counts = {}
    residual_top_level_path_counts = {}

    for item in unclassified_without_current_evidence:
        artifact = item.artifact

        for kind in artifact.kinds:
            residual_kind_counts[kind.value] = (
                residual_kind_counts.get(
                    kind.value,
                    0,
                )
                + 1
            )

        role = artifact.deployment_role.value
        residual_deployment_role_counts[role] = (
            residual_deployment_role_counts.get(
                role,
                0,
            )
            + 1
        )

        android_path = artifact.metadata_entry.path
        path = PurePosixPath(android_path)

        suffix = path.suffix.lower()
        if not suffix:
            suffix = "<none>"

        residual_suffix_counts[suffix] = (
            residual_suffix_counts.get(
                suffix,
                0,
            )
            + 1
        )

        parts = tuple(
            part
            for part in path.parts
            if part != "/"
        )

        top_level = (
            f"/{parts[0]}"
            if parts
            else "/"
        )

        residual_top_level_path_counts[top_level] = (
            residual_top_level_path_counts.get(
                top_level,
                0,
            )
            + 1
        )

    elf_artifact_association_evidence_entries = sum(
        len(
            item.elf_artifact_associations
        )
        for item
        in canonical_artifact_evidence
    )

    kernel_module_elf_association_evidence_entries = sum(
        len(
            item.kernel_module_elf_associations
        )
        for item
        in canonical_artifact_evidence
    )

    artifact_runtime_candidate_count = sum(
        len(
            item.runtime_linking_candidates
        )
        for item
        in canonical_artifact_evidence
    )

    artifact_runtime_root_traversal_count = sum(
        len(
            item.runtime_linking_root_traversals
        )
        for item
        in canonical_artifact_evidence
    )

    artifact_runtime_parent_dependency_count = sum(
        len(
            item.runtime_linking_parent_dependencies
        )
        for item
        in canonical_artifact_evidence
    )

    artifact_runtime_provider_dependency_count = sum(
        len(
            item.runtime_linking_provider_dependencies
        )
        for item
        in canonical_artifact_evidence
    )

    runtime_candidate_status_counts = {}
    runtime_candidate_reason_counts = {}

    for candidate in (
        runtime_linking_result
        .linker_elf_runtime_candidates
    ):
        status = candidate.status.value

        runtime_candidate_status_counts[
            status
        ] = (
            runtime_candidate_status_counts.get(
                status,
                0,
            )
            + 1
        )

        if candidate.reason is not None:
            runtime_candidate_reason_counts[
                candidate.reason
            ] = (
                runtime_candidate_reason_counts.get(
                    candidate.reason,
                    0,
                )
                + 1
            )

    runtime_traversal_status_counts = {}
    runtime_traversal_reason_counts = {}

    for traversal in (
        runtime_linking_result
        .linker_elf_dependency_traversals
    ):
        status = traversal.status.value

        runtime_traversal_status_counts[
            status
        ] = (
            runtime_traversal_status_counts.get(
                status,
                0,
            )
            + 1
        )

        if traversal.reason is not None:
            runtime_traversal_reason_counts[
                traversal.reason
            ] = (
                runtime_traversal_reason_counts.get(
                    traversal.reason,
                    0,
                )
                + 1
            )

    runtime_linking_continuity_lines = [
        (
            "Runtime-Linking upstream candidate conclusions: "
            f"{len(runtime_linking_result.linker_elf_runtime_candidates)}"
        ),
        (
            "Runtime-Linking candidate conclusions attached to "
            "canonical filesystem artifacts: "
            f"{artifact_runtime_candidate_count}"
        ),
        (
            "Runtime-Linking candidate conclusions outside canonical "
            "filesystem artifact evidence: "
            f"{len(runtime_linking_result.linker_elf_runtime_candidates) - artifact_runtime_candidate_count}"
        ),
        "Runtime-Linking candidate status continuity:",
    ]

    for status, count in sorted(
        runtime_candidate_status_counts.items()
    ):
        runtime_linking_continuity_lines.append(
            f"  {status}: {count}"
        )

    runtime_linking_continuity_lines.append(
        "Runtime-Linking candidate non-active reason continuity:"
    )

    if runtime_candidate_reason_counts:
        for reason, count in sorted(
            runtime_candidate_reason_counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        ):
            runtime_linking_continuity_lines.append(
                f"  {count}: {reason}"
            )
    else:
        runtime_linking_continuity_lines.append(
            "  (none)"
        )

    runtime_linking_continuity_lines.extend(
        [
            (
                "Runtime-Linking upstream loading-context traversals: "
                f"{len(runtime_linking_result.linker_elf_dependency_traversals)}"
            ),
            (
                "Runtime-Linking exact root traversals attached to "
                "canonical artifacts: "
                f"{artifact_runtime_root_traversal_count}"
            ),
            (
                "Runtime-Linking dependency-consumer resolution evidence "
                "entries attached to canonical artifacts: "
                f"{artifact_runtime_parent_dependency_count}"
            ),
            (
                "Runtime-Linking dependency-provider resolution evidence "
                "entries attached to canonical artifacts: "
                f"{artifact_runtime_provider_dependency_count}"
            ),
            "Runtime-Linking traversal status continuity:",
        ]
    )

    for status, count in sorted(
        runtime_traversal_status_counts.items()
    ):
        runtime_linking_continuity_lines.append(
            f"  {status}: {count}"
        )

    runtime_linking_continuity_lines.append(
        "Runtime-Linking non-resolved traversal reason continuity:"
    )

    if runtime_traversal_reason_counts:
        for reason, count in sorted(
            runtime_traversal_reason_counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        ):
            runtime_linking_continuity_lines.append(
                f"  {count}: {reason}"
            )
    else:
        runtime_linking_continuity_lines.append(
            "  (none)"
        )

    ownership_report_lines = [
        "TreeForge Android Reconstruction Ownership",
        "",
        "=== RECONSTRUCTION OWNERSHIP ===",
        "Status: SUCCESS",
        "",
        (
            "Decisions: "
            f"{len(ownership_result.decisions)}"
        ),
        (
            "Artifact decisions: "
            f"{len(artifact_decisions)}"
        ),
        (
            "Unresolved: "
            f"{len(ownership_result.unresolved)}"
        ),
        "",
        "=== ARTIFACT EVIDENCE COVERAGE ===",
        (
            "Canonical artifacts: "
            f"{len(canonical_artifact_evidence)}"
        ),
        (
            "Unclassified artifacts: "
            f"{len(unclassified_artifact_evidence)}"
        ),
        (
            "ELF-backed artifacts: "
            f"{len(elf_backed_artifact_evidence)}"
        ),
        (
            "Kernel-module-backed artifacts: "
            f"{len(kernel_module_backed_artifact_evidence)}"
        ),
        (
            "Unclassified ELF-backed artifacts: "
            f"{len(unclassified_elf_backed)}"
        ),
        (
            "Unclassified kernel-module-backed artifacts: "
            f"{len(unclassified_kernel_module_backed)}"
        ),
        (
            "INIT-executable-backed artifacts: "
            f"{len(init_executable_backed_artifact_evidence)}"
        ),
        (
            "Unclassified INIT-executable-backed artifacts: "
            f"{len(unclassified_init_executable_backed)}"
        ),
        (
            "Unclassified newly covered by INIT: "
            f"{len(unclassified_init_only_new_coverage)}"
        ),
        (
            "Classpath-backed artifacts: "
            f"{len(classpath_backed_artifact_evidence)}"
        ),
        (
            "Unclassified Classpath-backed artifacts: "
            f"{len(unclassified_classpath_backed)}"
        ),
        (
            "Unclassified newly covered by Classpath: "
            f"{len(unclassified_classpath_new_coverage)}"
        ),
        (
            "Java-archive-backed artifacts: "
            f"{len(java_archive_backed_artifact_evidence)}"
        ),
        (
            "Unclassified Java-archive-backed artifacts: "
            f"{len(unclassified_java_archive_backed)}"
        ),
        (
            "Shell-script-backed artifacts: "
            f"{len(shell_script_backed_artifact_evidence)}"
        ),
        (
            "Unclassified Shell-script-backed artifacts: "
            f"{len(unclassified_shell_script_backed)}"
        ),
        (
            "Shell CLASSPATH-reference-backed artifacts: "
            f"{len(shell_classpath_reference_artifact_evidence)}"
        ),
        (
            "Canonical Universe shell scripts: "
            f"{len(shell_reconciliation.associations)}"
        ),
        (
            "Canonical app_process shell wrappers: "
            f"{shell_app_process_wrapper_count}"
        ),
        (
            "Canonical shell CLASSPATH resolutions: "
            f"{shell_classpath_resolution_count}"
        ),
        (
            "Shell CLASSPATH status continuity: "
            + ", ".join(
                f"{status}={count}"
                for status, count
                in sorted(
                    shell_classpath_status_counts.items()
                )
            )
        ),
        (
            "APK-backed artifacts: "
            f"{len(apk_backed_artifact_evidence)}"
        ),
        (
            "APK package evidence entries: "
            f"{len(apk_package_evidence_entries)}"
        ),
        (
            "Unclassified APK-backed artifacts: "
            f"{len(unclassified_apk_backed)}"
        ),
        (
            "Unclassified newly covered by APK: "
            f"{len(unclassified_apk_new_coverage)}"
        ),
        (
            "APEX-member artifacts: "
            f"{len(apex_membership_backed_artifact_evidence)}"
        ),
        (
            "Unclassified APEX-member artifacts: "
            f"{len(unclassified_apex_membership_backed)}"
        ),
        (
            "Unclassified newly covered by APEX membership: "
            f"{len(unclassified_apex_new_coverage)}"
        ),
        (
            "Canonical Universe ELF/artifact associations: "
            f"{len(runtime_linking_result.universe.elf_artifact_associations)}"
        ),
        (
            "ELF/artifact association evidence attached to "
            "filesystem artifacts: "
            f"{elf_artifact_association_evidence_entries}"
        ),
        (
            "Canonical Universe kernel-module/ELF associations: "
            f"{len(runtime_linking_result.universe.kernel_module_elf_associations)}"
        ),
        (
            "Kernel-module/ELF association evidence attached to "
            "filesystem artifacts: "
            f"{kernel_module_elf_association_evidence_entries}"
        ),
        *runtime_linking_continuity_lines,
        (
            "Runtime-Linking-backed artifacts: "
            f"{len(runtime_linking_backed_artifact_evidence)}"
        ),
        (
            "Runtime-Linking candidate artifacts: "
            f"{len(runtime_linking_candidate_artifacts)}"
        ),
        (
            "Runtime-Linking root-context artifacts: "
            f"{len(runtime_linking_root_artifacts)}"
        ),
        (
            "Runtime-Linking dependency-consumer artifacts: "
            f"{len(runtime_linking_consumer_artifacts)}"
        ),
        (
            "Runtime-Linking dependency-provider artifacts: "
            f"{len(runtime_linking_provider_artifacts)}"
        ),
        (
            "Unclassified Runtime-Linking-backed artifacts: "
            f"{len(unclassified_runtime_linking_backed)}"
        ),
        (
            "Unclassified newly covered by Runtime Linking: "
            f"{len(unclassified_runtime_linking_new_coverage)}"
        ),
        (
            "Unclassified without ELF/kernel evidence: "
            f"{len(unclassified_without_elf_or_kernel)}"
        ),
        (
            "Unclassified without ELF/kernel/INIT evidence: "
            f"{sum(
                1
                for item
                in unclassified_artifact_evidence
                if (
                    not item.has_elf_evidence
                    and not item.has_kernel_module_evidence
                    and not item.has_init_executable_evidence
                )
            )}"
        ),
        (
            "Unclassified without ELF/kernel/INIT/Classpath evidence: "
            f"{sum(
                1
                for item
                in unclassified_artifact_evidence
                if (
                    not item.has_elf_evidence
                    and not item.has_kernel_module_evidence
                    and not item.has_init_executable_evidence
                    and not item.has_classpath_evidence
                )
            )}"
        ),
        (
            "Unclassified without ELF/kernel/INIT/Classpath/APK evidence: "
            f"{sum(
                1
                for item
                in unclassified_artifact_evidence
                if (
                    not item.has_elf_evidence
                    and not item.has_kernel_module_evidence
                    and not item.has_init_executable_evidence
                    and not item.has_classpath_evidence
                    and not item.has_apk_evidence
                )
            )}"
        ),
        (
            "Unclassified without ELF/kernel/INIT/Classpath/APK/APEX evidence: "
            f"{sum(
                1
                for item
                in unclassified_artifact_evidence
                if (
                    not item.has_elf_evidence
                    and not item.has_kernel_module_evidence
                    and not item.has_init_executable_evidence
                    and not item.has_classpath_evidence
                    and not item.has_apk_evidence
                    and not item.has_apex_membership_evidence
                )
            )}"
        ),
        "",
        "=== UNCLASSIFIED ARTIFACT RESIDUAL COMPOSITION ===",
        (
            "Residual artifacts: "
            f"{len(unclassified_without_current_evidence)}"
        ),
        "",
        "By artifact kind:",
    ]

    for kind, count in sorted(
        residual_kind_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        ownership_report_lines.append(
            f"  {kind}: {count}"
        )

    ownership_report_lines.extend(
        [
            "",
            "By deployment role:",
        ]
    )

    for role, count in sorted(
        residual_deployment_role_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        ownership_report_lines.append(
            f"  {role}: {count}"
        )

    ownership_report_lines.extend(
        [
            "",
            "By suffix:",
        ]
    )

    for suffix, count in sorted(
        residual_suffix_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        ownership_report_lines.append(
            f"  {suffix}: {count}"
        )

    ownership_report_lines.extend(
        [
            "",
            "By top-level Android path:",
        ]
    )

    for prefix, count in sorted(
        residual_top_level_path_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        ownership_report_lines.append(
            f"  {prefix}: {count}"
        )

    ownership_report_lines.extend(
        [
            "",
            "Residual artifact identities:",
        ]
    )

    for item in sorted(
        unclassified_without_current_evidence,
        key=lambda value: (
            value.artifact.android_path
        ),
    ):
        artifact = item.artifact

        ownership_report_lines.append(
            f"  {artifact.android_path}"
        )

    ownership_report_lines.extend(
        [
            "",
            "=== ARTIFACT EVIDENCE IDENTITY INTEGRITY ===",
            (
                "Unmatched filesystem ELF requirements: "
                f"{len(artifact_evidence.unmatched_filesystem_elf_requirements)}"
            ),
            (
                "Unmatched kernel-module requirements: "
                f"{len(artifact_evidence.unmatched_kernel_module_requirements)}"
            ),
            "",
            "=== OWNERSHIP DOMAINS ===",
        ]
    )

    for domain in sorted(
        ownership_domain_counts
    ):
        ownership_report_lines.append(
            (
                f"{domain}: "
                f"{ownership_domain_counts[domain]}"
            )
        )

    ownership_report_lines.extend(
        [
            "",
            "=== ARTIFACT OWNERSHIP ===",
        ]
    )

    for decision in artifact_decisions:
        ownership_report_lines.extend(
            [
                (
                    f"{decision.source_identity}"
                ),
                (
                    "  Domain: "
                    f"{decision.domain.value}"
                ),
                (
                    "  Reason: "
                    f"{decision.reason}"
                ),
            ]
        )

    ownership_report_path.write_text(
        "\n".join(
            ownership_report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    typer.echo(
        "Reconstruction Ownership completed successfully."
    )
    if show_report_paths:
        typer.echo(
            f"Report: {ownership_report_path}"
        )

    typer.echo()
    typer.echo(
        "=== RECONSTRUCTION PLANNING ==="
    )

    planning_report_lines = [
        "TreeForge Android Reconstruction Planning",
        "",
        "=== RECONSTRUCTION PLANNING ===",
    ]

    try:
        from treeforge.android.reconstruction_planning.stage import (
            AndroidReconstructionPlanningStage,
        )

        plan = (
            AndroidReconstructionPlanningStage()
            .plan(
                universe_result,
                ownership=ownership_result,
            )
        )
    except Exception as error:
        planning_report_lines.extend(
            [
                "Status: FAILED",
                "",
                f"Error: {error}",
            ]
        )

        reconstruction_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        reconstruction_planning_report_path = (
            reconstruction_root
            / "reconstruction-planning-report.txt"
        )

        reconstruction_planning_report_path.write_text(
            "\n".join(
                planning_report_lines
            )
            + "\n",
            encoding="utf-8",
        )

        typer.echo(
            (
                "Reconstruction Planning failed: "
                f"{error}"
            ),
            err=True,
        )
        typer.echo(
            f"Report: {reconstruction_planning_report_path}"
        )

        raise typer.Exit(
            code=1
        ) from error

    planning_report_lines.extend(
        [
            "Status: SUCCESS",
            "",
            f"Obligations: {len(plan.obligations)}",
            (
                "Ownership unresolved: "
                f"{len(ownership_result.unresolved)}"
            ),
        ]
    )

    if plan.completeness is not None:
        coverage = plan.completeness.coverage

        planning_report_lines.extend(
            [
                "",
                "=== PLANNING COVERAGE ===",
                f"Required: {coverage.required}",
                f"Planned: {coverage.planned}",
                f"Preserved: {coverage.preserved}",
                f"Not applicable: {coverage.not_applicable}",
                f"Unresolved: {coverage.unresolved}",
                f"Conflicting: {coverage.conflicting}",
                (
                    "Blocking unresolved: "
                    f"{plan.completeness.blocking_unresolved_count}"
                ),
                (
                    "Blocking conflicts: "
                    f"{plan.completeness.blocking_conflict_count}"
                ),
                f"Complete: {plan.completeness.complete}",
            ]
        )

    family_disposition_counts = {}

    for outcome in plan.outcomes:
        if outcome.obligation is None:
            raise RuntimeError(
                "Reconstruction Planning outcome is missing "
                "its canonical obligation"
            )

        requirement_kind = (
            outcome.obligation.requirement_kind
        )

        family_disposition_counts.setdefault(
            requirement_kind,
            Counter(),
        )[
            outcome.disposition.value
        ] += 1

    planning_report_lines.extend(
        [
            "",
            "=== PLANNING COVERAGE BY FAMILY ===",
        ]
    )

    for requirement_kind, _ in (
        AndroidReconstructionPlanningStage()._REQUIREMENT_FIELDS
    ):
        disposition_counts = (
            family_disposition_counts.get(
                requirement_kind,
                Counter(),
            )
        )

        required = sum(
            disposition_counts.values()
        )

        planning_report_lines.extend(
            [
                "",
                requirement_kind,
                f"  Required: {required}",
                (
                    "  Planned: "
                    f"{disposition_counts.get('planned', 0)}"
                ),
                (
                    "  Preserved: "
                    f"{disposition_counts.get('preserved', 0)}"
                ),
                (
                    "  Not applicable: "
                    f"{disposition_counts.get('not_applicable', 0)}"
                ),
                (
                    "  Unresolved: "
                    f"{disposition_counts.get('unresolved', 0)}"
                ),
                (
                    "  Conflicting: "
                    f"{disposition_counts.get('conflicting', 0)}"
                ),
            ]
        )

    unresolved_outcomes = tuple(
        outcome
        for outcome in plan.outcomes
        if (
            outcome.disposition
            is AndroidReconstructionPlanningDisposition.UNRESOLVED
        )
    )


    known_unresolved_outcomes = tuple(
        outcome
        for outcome in unresolved_outcomes
        if outcome.known_unresolved
    )

    unclassified_unresolved_outcomes = tuple(
        outcome
        for outcome in unresolved_outcomes
        if not outcome.known_unresolved
    )

    unresolved_outcomes = tuple(
        sorted(
            unresolved_outcomes,
            key=lambda outcome: (
                (
                    outcome.obligation.requirement_kind
                    if outcome.obligation is not None
                    else ""
                ),
                (
                    outcome.obligation.source_identity
                    if outcome.obligation is not None
                    else ""
                ),
                outcome.obligation_id,
            ),
        )
    )

    planning_report_lines.extend(
        [
            "",
            "=== UNRESOLVED PLANNING OBLIGATIONS ===",
            f"Count: {len(unresolved_outcomes)}",
            (
                "Known unresolved: "
                f"{len(known_unresolved_outcomes)}"
            ),
            (
                "Unclassified unresolved: "
                f"{len(unclassified_unresolved_outcomes)}"
            ),
        ]
    )

    for outcome in unresolved_outcomes:
        if outcome.obligation is None:
            raise RuntimeError(
                "Unresolved Reconstruction Planning outcome is missing "
                "its canonical obligation"
            )

        planning_report_lines.extend(
            [
                "",
                outcome.obligation.requirement_kind,
                f"  Obligation: {outcome.obligation_id}",
                f"  Source: {outcome.obligation.source_identity}",
                f"  Reason: {outcome.reason}",
            ]
        )

    init_source_disposition_counts = Counter(
        group.disposition.value
        for group in plan.init_source_groups
    )

    planning_report_lines.extend(
        [
            "",
            "=== INIT PLANNING SOURCES ===",
            (
                "Source groups: "
                f"{len(plan.init_source_groups)}"
            ),
            (
                "Required: "
                f"{init_source_disposition_counts.get('required', 0)}"
            ),
            (
                "Alternative: "
                f"{init_source_disposition_counts.get('alternative', 0)}"
            ),
            (
                "Unresolved: "
                f"{init_source_disposition_counts.get('unresolved', 0)}"
            ),
        ]
    )

    reconstruction_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    reconstruction_planning_report_path = (
        reconstruction_root
        / "reconstruction-planning-report.txt"
    )

    reconstruction_planning_report_path.write_text(
        "\n".join(
            planning_report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    typer.echo(
        "Status: SUCCESS"
    )
    if show_report_paths:
        typer.echo(
            f"Report: {reconstruction_planning_report_path}"
        )

    typer.echo()
    typer.echo(
        "=== RECONSTRUCTION ==="
    )

    #
    # Reconstruction intake
    #
    reconstruction_report_lines = [
        "TreeForge Android Reconstruction",
    ]

    # Planning remains authoritative for obligation disposition. This handoff
    # admits only the work established by the canonical plan and does not
    # perform family reconstruction, choose source-tree destinations, infer
    # ownership, render files, or materialize Device Tree output.
    #
    try:
        from treeforge.android.reconstruction.stage import (
            AndroidReconstructionStage,
        )
        from treeforge.android.reconstruction.build_system.dependency import (
            AndroidReconstructionBuildDependencyValidator,
        )

        reconstruction_input = (
            AndroidReconstructionStage()
            .prepare(
                plan,
                runtime_linking=(
                    runtime_linking_result
                ),
                partition_layout=(
                    result.parsing_snapshot.partition_layout
                ),
            )
        )
        exact_runtime_linking_identity = (
            reconstruction_input.runtime_linking
            is runtime_linking_result
        )

        exact_universe_identity = (
            reconstruction_input
            .runtime_linking
            .universe
            is runtime_linking_result.universe
        )

        if not exact_runtime_linking_identity:
            raise ValueError(
                "Reconstruction input changed exact Runtime Linking "
                "result identity"
            )

        if not exact_universe_identity:
            raise ValueError(
                "Reconstruction input does not preserve the exact "
                "canonical Universe owned by Runtime Linking"
            )

    except Exception as error:
        reconstruction_report_lines.extend(
            [
                "",
                "=== RECONSTRUCTION INTAKE ===",
                "Status: FAILED",
                "",
                f"Error: {error}",
            ]
        )

        reconstruction_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        reconstruction_report_path = (
            reconstruction_root
            / "reconstruction-report.txt"
        )

        reconstruction_report_path.write_text(
            "\n".join(
                reconstruction_report_lines
            )
            + "\n",
            encoding="utf-8",
        )

        typer.echo(
            (
                "Reconstruction intake failed: "
                f"{error}"
            ),
            err=True,
        )
        typer.echo(
            f"Report: {reconstruction_report_path}"
        )

        raise typer.Exit(
            code=1
        ) from error

    reconstruction_coverage = (
        reconstruction_input.coverage
    )

    reconstruction_report_lines.extend(
        [
            "",
            "=== RECONSTRUCTION INTAKE ===",
            "Status: SUCCESS",
            "Canonical input identity:",
            "  Runtime Linking: preserved",
            (
                "  Exact Runtime Linking identity: "
                f"{exact_runtime_linking_identity}"
            ),
            (
                "  Android Device Universe: "
                "preserved through Runtime Linking"
            ),
            (
                "  Exact Universe identity: "
                f"{exact_universe_identity}"
            ),
            (
                "Required: "
                f"{reconstruction_coverage.required}"
            ),
            (
                "Reconstruction work: "
                f"{reconstruction_coverage.reconstruction_work}"
            ),
            (
                "Preservation work: "
                f"{reconstruction_coverage.preservation_work}"
            ),
            (
                "Not applicable: "
                f"{reconstruction_coverage.not_applicable}"
            ),
            (
                "Known unresolved: "
                f"{reconstruction_coverage.known_unresolved}"
            ),
            (
                "Accounted: "
                f"{reconstruction_coverage.accounted}"
            ),
            (
                "Ready: "
                f"{reconstruction_coverage.ready}"
            ),
        ]
    )

    try:
        reconstruction_result = (
            AndroidReconstructionStage()
            .reconstruct(
                reconstruction_input
            )
        )
    except Exception as error:
        reconstruction_report_lines.extend(
            [
                "",
                "=== RECONSTRUCTION ===",
                "Status: FAILED",
                "",
                f"Error: {error}",
            ]
        )

        reconstruction_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        reconstruction_report_path = (
            reconstruction_root
            / "reconstruction-report.txt"
        )

        reconstruction_report_path.write_text(
            "\n".join(
                reconstruction_report_lines
            )
            + "\n",
            encoding="utf-8",
        )

        typer.echo(
            (
                "Reconstruction failed: "
                f"{error}"
            ),
            err=True,
        )

        typer.echo(
            f"Report: {reconstruction_report_path}"
        )

        raise typer.Exit(
            code=1
        ) from error

    reconstruction_status_counts = Counter(
        outcome.status.value
        for outcome
        in reconstruction_result.outcomes
    )

    artifact_build_representations = (
        reconstruction_result
        .artifact_build_representations
    )

    elf_build_semantics = (
        reconstruction_result
        .elf_build_semantics
    )

    elf_build_status_counts = Counter(
        semantics.status.value
        for semantics
        in elf_build_semantics
    )

    elf_build_role_counts = Counter(
        semantics.requirement.role.value
        for semantics
        in elf_build_semantics
    )

    elf_build_attached_count = sum(
        semantics.target_build_representation_id
        is not None
        for semantics
        in elf_build_semantics
    )

    elf_build_unattached_count = (
        len(elf_build_semantics)
        - elf_build_attached_count
    )

    elf_build_with_dependencies_count = sum(
        bool(semantics.dependency_names)
        for semantics
        in elf_build_semantics
    )

    elf_build_without_dependencies_count = (
        len(elf_build_semantics)
        - elf_build_with_dependencies_count
    )

    elf_build_dependency_name_count = sum(
        len(semantics.dependency_names)
        for semantics
        in elf_build_semantics
    )

    elf_build_resolved_dependency_count = sum(
        len(semantics.resolved_dependency_ids)
        for semantics
        in elf_build_semantics
    )

    build_representation_by_id = {
        representation.representation_id: representation
        for representation
        in artifact_build_representations
    }

    if len(
        build_representation_by_id
    ) != len(
        artifact_build_representations
    ):
        raise ValueError(
            "Build-System representation identities must be unique"
        )

    elf_representation_id_by_requirement_id = {
        semantics.requirement.requirement_id: (
            semantics.target_build_representation_id
        )
        for semantics
        in elf_build_semantics
        if semantics.target_build_representation_id is not None
    }

    if len(
        elf_representation_id_by_requirement_id
    ) != elf_build_attached_count:
        raise ValueError(
            "attached ELF semantics must preserve unique canonical "
            "ELF requirement identities"
        )

    elf_physical_build_representation_ids = set(
        elf_representation_id_by_requirement_id.values()
    )

    elf_physical_build_representation_count = len(
        elf_physical_build_representation_ids
    )

    elf_build_representations_with_dependencies_count = sum(
        bool(
            build_representation_by_id[
                representation_id
            ].dependency_ids
        )
        for representation_id
        in elf_physical_build_representation_ids
    )

    elf_physical_dependency_edges = {
        (
            representation_id,
            dependency_id,
        )
        for representation_id
        in elf_physical_build_representation_ids
        for dependency_id
        in (
            build_representation_by_id[
                representation_id
            ].dependency_ids
        )
    }

    elf_physical_dependency_edge_count = len(
        elf_physical_dependency_edges
    )

    elf_expected_physical_dependency_edges = set()

    elf_resolved_provider_with_physical_target_count = 0
    elf_resolved_provider_without_physical_target_count = 0
    elf_resolved_provider_self_dependency_count = 0

    for semantics in elf_build_semantics:
        parent_representation_id = (
            semantics.target_build_representation_id
        )

        if parent_representation_id is None:
            continue

        for provider_requirement_id in (
            semantics.resolved_dependency_ids
        ):
            provider_representation_id = (
                elf_representation_id_by_requirement_id.get(
                    provider_requirement_id
                )
            )

            if provider_representation_id is None:
                elf_resolved_provider_without_physical_target_count += 1
                continue

            elf_resolved_provider_with_physical_target_count += 1

            if (
                provider_representation_id
                == parent_representation_id
            ):
                elf_resolved_provider_self_dependency_count += 1
                continue

            elf_expected_physical_dependency_edges.add(
                (
                    parent_representation_id,
                    provider_representation_id,
                )
            )

    elf_missing_physical_dependency_edges = (
        elf_expected_physical_dependency_edges
        - elf_physical_dependency_edges
    )

    elf_missing_physical_dependency_edge_count = len(
        elf_missing_physical_dependency_edges
    )

    build_representation_ids = set(
        build_representation_by_id
    )

    elf_invalid_dependency_target_count = sum(
        1
        for (
            _,
            dependency_id,
        )
        in elf_physical_dependency_edges
        if dependency_id not in build_representation_ids
    )

    elf_dependency_projection_match = (
        elf_missing_physical_dependency_edge_count == 0
        and elf_invalid_dependency_target_count == 0
    )

    apex_requirements = (
        runtime_linking_result
        .universe
        .apex_requirements
    )

    apex_requirement_ids = {
        requirement.requirement_id
        for requirement
        in apex_requirements
    }

    apex_build_representations = tuple(
        representation
        for representation
        in artifact_build_representations
        if (
            representation.canonical_requirement_id
            in apex_requirement_ids
        )
    )

    apex_build_representation_by_requirement_id = {
        representation.canonical_requirement_id: representation
        for representation
        in apex_build_representations
    }

    apex_requirement_backed_count = sum(
        1
        for representation
        in apex_build_representations
        if representation.canonical_requirement_id is not None
    )

    apex_preserved_backed_count = sum(
        1
        for representation
        in apex_build_representations
        if representation.preserved_artifact_id is not None
    )

    apex_role_count = sum(
        representation.kind.value == "apex"
        for representation
        in apex_build_representations
    )

    apex_with_partition_count = sum(
        representation.installed_partition is not None
        for representation
        in apex_build_representations
    )

    apex_with_android_path_count = sum(
        representation.installed_android_path is not None
        for representation
        in apex_build_representations
    )

    apex_package_coverage_match = (
        len(apex_build_representations)
        == len(apex_requirements)
        and len(
            apex_build_representation_by_requirement_id
        )
        == len(apex_requirements)
        and set(
            apex_build_representation_by_requirement_id
        )
        == apex_requirement_ids
        and apex_role_count
        == len(apex_requirements)
        and apex_requirement_backed_count
        == len(apex_requirements)
        and apex_preserved_backed_count == 0
    )

    kernel_module_requirement = (
        runtime_linking_result
        .universe
        .kernel_module_requirement
    )

    kernel_module_count = 0
    kernel_module_physical_representation_count = 0
    kernel_module_hard_dependency_count = 0
    kernel_module_expected_dependency_edges = set()
    kernel_module_physical_dependency_edges = set()
    kernel_module_missing_dependency_edge_count = 0
    kernel_module_invalid_dependency_target_count = 0
    kernel_module_build_coverage_match = True
    kernel_module_dependency_projection_match = True

    if kernel_module_requirement is not None:
        artifact_requirements = (
            runtime_linking_result
            .universe
            .artifact_requirements
            .requirements
        )

        artifact_by_identity = {
            requirement.identity_key: requirement
            for requirement
            in artifact_requirements
        }

        artifact_requirement_by_id = {
            requirement.requirement_id: requirement
            for requirement
            in artifact_requirements
        }

        build_representation_by_id = {
            representation.representation_id: representation
            for representation
            in artifact_build_representations
        }

        build_representation_id_by_artifact_requirement_id = {}

        for representation in artifact_build_representations:
            artifact_requirement_id = (
                representation.preserved_artifact_id
                or representation.canonical_requirement_id
            )

            if (
                artifact_requirement_id
                not in artifact_requirement_by_id
            ):
                continue

            existing = (
                build_representation_id_by_artifact_requirement_id.get(
                    artifact_requirement_id
                )
            )

            if (
                existing is not None
                and existing != representation.representation_id
            ):
                raise ValueError(
                    "one canonical Artifact is represented by multiple "
                    "Build-System representations"
                )

            build_representation_id_by_artifact_requirement_id[
                artifact_requirement_id
            ] = representation.representation_id

        build_representation_id_by_module_object_id = {}

        for module in (
            kernel_module_requirement.module_requirements
        ):
            source = (
                module.source
                .elf
                .source
            )

            filesystem_source = (
                source.filesystem_source
            )

            if (
                filesystem_source is None
                or source.metadata_entry is None
            ):
                raise ValueError(
                    "canonical kernel module lost exact filesystem identity"
                )

            identity_key = (
                id(filesystem_source.artifact),
                id(source.metadata_entry),
            )

            artifact_requirement = (
                artifact_by_identity.get(
                    identity_key
                )
            )

            if artifact_requirement is None:
                raise ValueError(
                    "canonical kernel module has no exact Artifact "
                    "requirement during reporting"
                )

            representation_id = (
                build_representation_id_by_artifact_requirement_id.get(
                    artifact_requirement.requirement_id
                )
            )

            if representation_id is None:
                continue

            build_representation_id_by_module_object_id[
                id(module)
            ] = representation_id

        kernel_module_count = len(
            kernel_module_requirement.module_requirements
        )

        kernel_module_physical_representation_count = len(
            build_representation_id_by_module_object_id
        )

        kernel_module_hard_dependency_count = len(
            kernel_module_requirement.hard_dependencies
        )

        for dependency in (
            kernel_module_requirement.hard_dependencies
        ):
            owner_id = (
                build_representation_id_by_module_object_id.get(
                    id(dependency.owner)
                )
            )

            dependency_id = (
                build_representation_id_by_module_object_id.get(
                    id(dependency.dependency)
                )
            )

            if (
                owner_id is None
                or dependency_id is None
            ):
                continue

            if owner_id == dependency_id:
                continue

            kernel_module_expected_dependency_edges.add(
                (
                    owner_id,
                    dependency_id,
                )
            )

        kernel_module_representation_ids = set(
            build_representation_id_by_module_object_id.values()
        )

        for owner_id in kernel_module_representation_ids:
            owner_representation = (
                build_representation_by_id[
                    owner_id
                ]
            )

            for dependency_id in (
                owner_representation.dependency_ids
            ):
                if dependency_id in kernel_module_representation_ids:
                    kernel_module_physical_dependency_edges.add(
                        (
                            owner_id,
                            dependency_id,
                        )
                    )

        kernel_module_missing_dependency_edges = (
            kernel_module_expected_dependency_edges
            - kernel_module_physical_dependency_edges
        )

        kernel_module_missing_dependency_edge_count = len(
            kernel_module_missing_dependency_edges
        )

        all_build_representation_ids = set(
            build_representation_by_id
        )

        kernel_module_invalid_dependency_target_count = sum(
            1
            for (
                _,
                dependency_id,
            )
            in kernel_module_physical_dependency_edges
            if dependency_id not in all_build_representation_ids
        )

        kernel_module_build_coverage_match = (
            kernel_module_physical_representation_count
            == kernel_module_count
        )

        kernel_module_dependency_projection_match = (
            kernel_module_missing_dependency_edge_count == 0
            and kernel_module_invalid_dependency_target_count == 0
        )

    kernel_module_configuration_count = 0
    kernel_module_configuration_representation_count = 0
    kernel_module_configuration_kind_counts = Counter()
    kernel_module_configuration_coverage_match = True

    if kernel_module_requirement is not None:
        kernel_module_configuration_count = len(
            kernel_module_requirement.configuration_requirements
        )

        artifact_requirements = (
            runtime_linking_result
            .universe
            .artifact_requirements
            .requirements
        )

        config_artifact_requirement_ids = set()

        for configuration in (
            kernel_module_requirement.configuration_requirements
        ):
            model_source = (
                configuration.source.source
            )

            filesystem_artifact = (
                model_source.filesystem_source.artifact
            )

            filesystem_relative_path = (
                model_source.host_path.relative_to(
                    model_source.filesystem_source.filesystem.root
                )
            )

            physical_android_path = (
                "/"
                + filesystem_relative_path.as_posix()
            )

            matches = tuple(
                requirement
                for requirement
                in artifact_requirements
                if (
                    requirement.inventory_entry.artifact
                    is filesystem_artifact
                    and requirement.android_path
                    == physical_android_path
                )
            )

            if len(matches) != 1:
                raise ValueError(
                    "kernel-module configuration reporting requires "
                    "exactly one canonical Artifact requirement: "
                    f"source={model_source.identity_key!r}, "
                    f"matches={len(matches)}"
                )

            config_artifact_requirement_ids.add(
                matches[0].requirement_id
            )

            kernel_module_configuration_kind_counts[
                configuration.source.configuration_kind.value
            ] += 1

        kernel_module_configuration_build_representations = tuple(
            representation
            for representation
            in artifact_build_representations
            if (
                representation.canonical_requirement_id
                in config_artifact_requirement_ids
            )
        )

        kernel_module_configuration_representation_count = len(
            kernel_module_configuration_build_representations
        )

        represented_config_artifact_ids = {
            representation.canonical_requirement_id
            for representation
            in kernel_module_configuration_build_representations
        }

        kernel_module_configuration_coverage_match = (
            kernel_module_configuration_representation_count
            == kernel_module_configuration_count
            and represented_config_artifact_ids
            == config_artifact_requirement_ids
            and len(config_artifact_requirement_ids)
            == kernel_module_configuration_count
        )

    classpath_requirement = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
        .classpath_requirement
    )

    classpath_effective_entry_count = 0
    classpath_installed_jar_status_counts = Counter()

    classpath_resolved_artifact_ids = set()
    classpath_resolved_resolution_count = 0

    classpath_java_representation_ids = set()
    classpath_java_preserved_backed_count = 0
    classpath_java_requirement_backed_count = 0

    classpath_java_coverage_match = True

    if classpath_requirement is not None:
        classpath_effective_entry_count = sum(
            len(classpath.entries)
            for classpath
            in classpath_requirement.effective_classpaths
        )

        for resolution in (
            classpath_requirement.installed_jar_resolutions
        ):
            classpath_installed_jar_status_counts[
                resolution.status.value
            ] += 1

            if resolution.status.value != "resolved":
                continue

            classpath_resolved_resolution_count += 1

            if len(resolution.matched_artifacts) != 1:
                raise ValueError(
                    "resolved Classpath installed-JAR reporting "
                    "requires exactly one canonical Artifact requirement"
                )

            classpath_resolved_artifact_ids.add(
                resolution
                .matched_artifacts[0]
                .requirement_id
            )

        for representation in artifact_build_representations:
            if representation.kind.value != "java_library":
                continue

            represented_artifact_id = (
                representation.preserved_artifact_id
                if representation.preserved_artifact_id is not None
                else representation.canonical_requirement_id
            )

            if represented_artifact_id is None:
                continue

            classpath_java_representation_ids.add(
                represented_artifact_id
            )

            if representation.preserved_artifact_id is not None:
                classpath_java_preserved_backed_count += 1

            elif representation.canonical_requirement_id is not None:
                classpath_java_requirement_backed_count += 1

        classpath_java_coverage_match = (
            classpath_resolved_artifact_ids
            <= classpath_java_representation_ids
        )

    boot_requirements = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
        .boot_requirements
    )

    boot_requirement_ids = {
        requirement.requirement_id
        for requirement
        in boot_requirements
    }

    boot_requirement_kind_counts = Counter(
        requirement.container_kind
        for requirement
        in boot_requirements
    )

    boot_build_representations = tuple(
        representation
        for representation
        in artifact_build_representations
        if representation.kind.value == "boot_artifact"
    )

    boot_build_requirement_ids = {
        representation.canonical_requirement_id
        for representation
        in boot_build_representations
        if representation.canonical_requirement_id is not None
    }

    boot_build_kind_counts = Counter()

    boot_requirement_by_id = {
        requirement.requirement_id: requirement
        for requirement
        in boot_requirements
    }

    for representation in boot_build_representations:
        requirement_id = representation.canonical_requirement_id

        if requirement_id in boot_requirement_by_id:
            boot_build_kind_counts[
                boot_requirement_by_id[
                    requirement_id
                ].container_kind
            ] += 1

    boot_build_coverage_match = (
        boot_requirement_ids
        == boot_build_requirement_ids
        and len(boot_build_representations)
        == len(boot_requirements)
    )

    dtbo_requirements = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
        .dtbo_requirements
    )

    dtbo_requirement_ids = {
        requirement.requirement_id
        for requirement
        in dtbo_requirements
    }

    dtbo_build_representations = tuple(
        representation
        for representation
        in artifact_build_representations
        if representation.kind.value == "dtbo_artifact"
    )

    dtbo_build_requirement_ids = {
        representation.canonical_requirement_id
        for representation
        in dtbo_build_representations
        if representation.canonical_requirement_id is not None
    }

    dtbo_build_coverage_match = (
        dtbo_requirement_ids
        == dtbo_build_requirement_ids
        and len(dtbo_build_representations)
        == len(dtbo_requirements)
    )

    dtbo_population = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
        .dtbo_population
    )

    dtbo_population_entries = (
        ()
        if dtbo_population is None
        else dtbo_population.entries
    )

    dtbo_population_requirement_ids = {
        entry.requirement.requirement_id
        for entry
        in dtbo_population_entries
    }

    dtbo_population_identity_match = (
        dtbo_requirement_ids
        == dtbo_population_requirement_ids
        and len(dtbo_population_entries)
        == len(dtbo_requirements)
    )

    vbmeta_requirements = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
        .vbmeta_requirements
    )

    vbmeta_requirement_ids = {
        requirement.requirement_id
        for requirement
        in vbmeta_requirements
    }

    if (
        len(vbmeta_requirement_ids)
        != len(vbmeta_requirements)
    ):
        raise ValueError(
            "canonical Universe VBMeta requirements must expose "
            "unique exact requirement identities"
        )

    # Standalone VBMeta image ownership is structural:
    #
    #   standalone AVB0 root:
    #       artifact is container_artifact
    #
    #   embedded/footer VBMeta:
    #       artifact is not container_artifact
    #
    # Partition provenance is a separate AVB-topology property. Footer
    # metadata embedded in boot/system/vendor/etc. may therefore remain
    # partition-backed without becoming standalone VBMETA_ARTIFACT outputs.
    vbmeta_standalone_requirements = tuple(
        requirement
        for requirement
        in vbmeta_requirements
        if (
            requirement.artifact
            is requirement.container_artifact
        )
    )

    vbmeta_embedded_requirements = tuple(
        requirement
        for requirement
        in vbmeta_requirements
        if (
            requirement.artifact
            is not requirement.container_artifact
        )
    )

    if (
        len(vbmeta_standalone_requirements)
        + len(vbmeta_embedded_requirements)
        != len(vbmeta_requirements)
    ):
        raise ValueError(
            "canonical VBMeta requirements must partition exactly into "
            "standalone AVB0-root and embedded/footer populations"
        )

    if not all(
        requirement.is_partition_backed
        for requirement
        in vbmeta_standalone_requirements
    ):
        raise ValueError(
            "standalone canonical VBMeta roots must retain "
            "partition provenance"
        )

    vbmeta_standalone_requirement_ids = {
        requirement.requirement_id
        for requirement
        in vbmeta_standalone_requirements
    }

    if (
        len(vbmeta_standalone_requirement_ids)
        != len(vbmeta_standalone_requirements)
    ):
        raise ValueError(
            "standalone VBMeta roots must expose unique "
            "canonical requirement identities"
        )

    # Keep the complete partition-backed population independently for
    # canonical AVB topology coverage. This population intentionally
    # includes footer metadata attached to partition images.
    vbmeta_topology_partition_backed_requirements = tuple(
        requirement
        for requirement
        in vbmeta_requirements
        if requirement.is_partition_backed
    )

    vbmeta_topology_partition_requirement_ids = {
        requirement.requirement_id
        for requirement
        in vbmeta_topology_partition_backed_requirements
    }

    if (
        len(vbmeta_topology_partition_requirement_ids)
        != len(vbmeta_topology_partition_backed_requirements)
    ):
        raise ValueError(
            "partition-backed canonical AVB requirements must expose "
            "unique exact requirement identities"
        )

    vbmeta_build_representations = tuple(
        representation
        for representation
        in artifact_build_representations
        if representation.kind.value == "vbmeta_artifact"
    )

    vbmeta_build_requirement_ids = {
        representation.canonical_requirement_id
        for representation
        in vbmeta_build_representations
        if representation.canonical_requirement_id is not None
    }

    if (
        len(vbmeta_build_requirement_ids)
        != len(vbmeta_build_representations)
    ):
        raise ValueError(
            "VBMETA_ARTIFACT representations must each expose one unique "
            "canonical VBMeta requirement identity"
        )

    vbmeta_build_coverage_match = (
        vbmeta_standalone_requirement_ids
        == vbmeta_build_requirement_ids
        and len(vbmeta_build_representations)
        == len(vbmeta_standalone_requirements)
    )

    avb_topology = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
        .avb_topology
    )

    avb_topology_requirements = (
        ()
        if avb_topology is None
        else avb_topology.requirements
    )

    avb_topology_requirement_ids = {
        requirement.requirement_id
        for requirement
        in avb_topology_requirements
    }

    if (
        len(avb_topology_requirement_ids)
        != len(avb_topology_requirements)
    ):
        raise ValueError(
            "canonical AVB topology requirements must expose unique "
            "exact VBMeta requirement identities"
        )

    avb_topology_partition_backed_requirements = tuple(
        requirement
        for requirement
        in avb_topology_requirements
        if requirement.is_partition_backed
    )

    avb_topology_partition_requirement_ids = {
        requirement.requirement_id
        for requirement
        in avb_topology_partition_backed_requirements
    }

    avb_topology_partition_coverage_match = (
        vbmeta_topology_partition_requirement_ids
        == avb_topology_partition_requirement_ids
        and len(avb_topology_partition_backed_requirements)
        == len(vbmeta_topology_partition_backed_requirements)
    )

    avb_topology_identity_match = (
        len(avb_topology_requirements)
        == len(vbmeta_requirements)
        and all(
            any(
                topology_requirement is requirement
                for topology_requirement
                in avb_topology_requirements
            )
            for requirement
            in vbmeta_requirements
        )
        and all(
            any(
                requirement is topology_requirement
                for requirement
                in vbmeta_requirements
            )
            for topology_requirement
            in avb_topology_requirements
        )
    )

    build_dependency_validation = (
        AndroidReconstructionBuildDependencyValidator.validate(
            artifact_build_representations
        )
    )

    artifact_build_kind_counts = Counter(
        representation.kind.value
        for representation
        in artifact_build_representations
    )

    artifact_build_status_counts = Counter(
        representation.status.value
        for representation
        in artifact_build_representations
    )

    apk_requirement = getattr(
        runtime_linking_result.universe,
        "apk_requirement",
        None,
    )

    apk_packages = (
        apk_requirement.packages
        if apk_requirement is not None
        else ()
    )

    apk_overlay_resolutions = (
        apk_requirement.overlay_resolutions
        if apk_requirement is not None
        else ()
    )

    apk_artifact_ids = {
        package.artifact.requirement_id
        for package in apk_packages
    }

    apk_build_representations = tuple(
        representation
        for representation
        in artifact_build_representations
        if (
            (
                representation.preserved_artifact_id
                or representation.canonical_requirement_id
            )
            in apk_artifact_ids
        )
    )

    apk_build_representation_by_artifact_id = {
        (
            representation.preserved_artifact_id
            or representation.canonical_requirement_id
        ): representation
        for representation
        in apk_build_representations
    }

    apk_requirement_backed_count = sum(
        1
        for representation
        in apk_build_representations
        if representation.canonical_requirement_id is not None
    )

    apk_preserved_backed_count = sum(
        1
        for representation
        in apk_build_representations
        if representation.preserved_artifact_id is not None
    )

    apk_package_role_count = sum(
        representation.kind.value == "package"
        for representation
        in apk_build_representations
    )

    apk_package_coverage_match = (
        len(apk_build_representations)
        == len(apk_packages)
        and len(apk_build_representation_by_artifact_id)
        == len(apk_packages)
        and set(apk_build_representation_by_artifact_id)
        == apk_artifact_ids
        and apk_package_role_count
        == len(apk_packages)
    )

    apk_resolved_overlay_resolutions = tuple(
        resolution
        for resolution
        in apk_overlay_resolutions
        if resolution.status.value == "resolved"
    )

    apk_resolved_overlay_dependency_count = 0
    apk_expected_overlay_dependency_edges = set()

    for resolution in apk_resolved_overlay_resolutions:
        overlay_artifact_id = (
            resolution.overlay.artifact.requirement_id
        )

        target_artifact_id = (
            resolution.targets[0].artifact.requirement_id
        )

        overlay_representation = (
            apk_build_representation_by_artifact_id.get(
                overlay_artifact_id
            )
        )

        target_representation = (
            apk_build_representation_by_artifact_id.get(
                target_artifact_id
            )
        )

        if (
            overlay_representation is not None
            and target_representation is not None
            and target_representation.representation_id
            in overlay_representation.dependency_ids
        ):
            apk_resolved_overlay_dependency_count += 1
            apk_expected_overlay_dependency_edges.add(
                (
                    overlay_representation.representation_id,
                    target_representation.representation_id,
                )
            )

    apk_resolved_overlay_missing_dependency_count = (
        len(apk_resolved_overlay_resolutions)
        - apk_resolved_overlay_dependency_count
    )

    apk_overlay_dependency_coverage_match = (
        apk_resolved_overlay_missing_dependency_count == 0
    )

    build_dependency_actual_edges = {
        (
            representation.representation_id,
            dependency_id,
        )
        for representation
        in artifact_build_representations
        for dependency_id
        in representation.dependency_ids
    }

    build_dependency_elf_owned_edges = set(
        elf_expected_physical_dependency_edges
    )

    build_dependency_kernel_owned_edges = set(
        kernel_module_expected_dependency_edges
    )

    build_dependency_apk_owned_edges = set(
        apk_expected_overlay_dependency_edges
    )

    build_dependency_owned_edge_union = (
        build_dependency_elf_owned_edges
        | build_dependency_kernel_owned_edges
        | build_dependency_apk_owned_edges
    )

    build_dependency_family_edge_sum = (
        len(build_dependency_elf_owned_edges)
        + len(build_dependency_kernel_owned_edges)
        + len(build_dependency_apk_owned_edges)
    )

    build_dependency_family_overlap_count = (
        build_dependency_family_edge_sum
        - len(build_dependency_owned_edge_union)
    )

    build_dependency_missing_owned_edges = (
        build_dependency_owned_edge_union
        - build_dependency_actual_edges
    )

    build_dependency_unowned_actual_edges = (
        build_dependency_actual_edges
        - build_dependency_owned_edge_union
    )

    build_dependency_ownership_match = (
        build_dependency_family_overlap_count == 0
        and not build_dependency_missing_owned_edges
        and not build_dependency_unowned_actual_edges
        and len(build_dependency_actual_edges)
        == build_dependency_validation.dependency_edge_count
    )

    artifact_preserved_work_count = sum(
        1
        for item
        in reconstruction_result
        .reconstruction_input
        .work_items
        if (
            item.work_kind.value == "preserve"
            and item.requirement_kind == "artifact"
        )
    )

    artifact_work_by_preserved_id = {
        item.preserved_artifact_id: item
        for item
        in reconstruction_result
        .reconstruction_input
        .work_items
        if (
            item.work_kind.value == "preserve"
            and item.requirement_kind == "artifact"
        )
    }

    artifact_partial_kind_counts = Counter()

    artifact_partial_kind_tuple_counts = Counter()

    for representation in artifact_build_representations:
        if representation.status.value != "partial":
            continue

        if representation.preserved_artifact_id is None:
            continue

        work_item = artifact_work_by_preserved_id[
            representation.preserved_artifact_id
        ]

        requirement = work_item.obligation.requirement

        kind_values = tuple(
            kind.value
            for kind in requirement.kinds
        )

        artifact_partial_kind_tuple_counts[
            kind_values
        ] += 1

        for kind_value in kind_values:
            artifact_partial_kind_counts[
                kind_value
            ] += 1

    composition_relationships = (
        reconstruction_result.composition_relationships
    )

    composition_relationship_kind_counts = Counter(
        relationship.relationship.kind.value
        for relationship
        in composition_relationships
    )

    composition_relationship_status_counts = Counter(
        relationship.relationship.status.value
        for relationship
        in composition_relationships
    )

    composition_projection_status_counts = Counter(
        (
            "unresolved"
            if any(
                target.kind.value == "unresolved"
                for target in relationship.targets
            )
            else "resolved"
        )
        for relationship
        in composition_relationships
    )

    composition_projection_status_by_kind = {}

    for relationship in composition_relationships:
        relationship_kind = (
            relationship.relationship.kind.value
        )

        projection_status = (
            "unresolved"
            if any(
                target.kind.value == "unresolved"
                for target in relationship.targets
            )
            else "resolved"
        )

        composition_projection_status_by_kind.setdefault(
            relationship_kind,
            Counter(),
        )[projection_status] += 1

    composition_applicability_counts = Counter(
        relationship.applicability.status.value
        for relationship
        in composition_relationships
    )

    composition_endpoint_by_id = {}

    for relationship in composition_relationships:
        for endpoint in (
            relationship.source,
            *relationship.targets,
        ):
            existing = composition_endpoint_by_id.get(
                endpoint.endpoint_id
            )

            if (
                existing is not None
                and existing != endpoint
            ):
                raise RuntimeError(
                    "Composition endpoint identity maps to "
                    "conflicting endpoint values: "
                    f"{endpoint.endpoint_id}"
                )

            composition_endpoint_by_id[
                endpoint.endpoint_id
            ] = endpoint

    composition_endpoint_kind_counts = Counter(
        endpoint.kind.value
        for endpoint
        in composition_endpoint_by_id.values()
    )

    init_representation_count = len(
        reconstruction_result
        .init_source_representations
    )

    init_reconstructed_obligation_count = sum(
        len(
            representation
            .contributing_obligation_ids
        )
        for representation
        in reconstruction_result
        .init_source_representations
    )

    init_source_contents = (
        reconstruction_result
        .init_source_contents
    )

    init_source_content_status_counts = Counter(
        content.status.value
        for content
        in init_source_contents
    )

    init_source_content_media_kind_counts = Counter(
        content.media_kind.value
        for content
        in init_source_contents
    )

    init_source_content_contributing_count = sum(
        len(
            content
            .contributing_obligation_ids
        )
        for content
        in init_source_contents
    )

    init_source_content_excluded_count = sum(
        len(
            content
            .excluded_obligation_ids
        )
        for content
        in init_source_contents
    )

    init_source_content_unresolved_count = sum(
        len(
            content
            .unresolved_obligation_ids
        )
        for content
        in init_source_contents
    )

    runtime_property_representation_count = len(
        reconstruction_result
        .runtime_property_representations
    )

    runtime_property_source_contents = (
        reconstruction_result
        .runtime_property_source_contents
    )

    runtime_property_source_content_status_counts = Counter(
        content.status.value
        for content
        in runtime_property_source_contents
    )

    runtime_property_source_content_contributing_count = sum(
        len(
            content.contributing_obligation_ids
        )
        for content
        in runtime_property_source_contents
    )

    runtime_property_source_content_text_count = sum(
        1
        for content
        in runtime_property_source_contents
        if content.text is not None
    )

    runtime_property_source_content_raw_byte_count = sum(
        1
        for content
        in runtime_property_source_contents
        if content.raw_bytes is not None
    )

    fstab_source_representation_count = len(
        reconstruction_result
        .fstab_source_representations
    )

    fstab_reconstructed_obligation_count = sum(
        len(
            representation
            .contributing_obligation_ids
        )
        for representation
        in reconstruction_result
        .fstab_source_representations
    )

    fstab_active_source_context_count = (
        fstab_source_representation_count
    )

    fstab_active_contexts_with_unparsed_lines = sum(
        1
        for representation
        in reconstruction_result.fstab_source_representations
        if representation.source_context.unparsed_lines
    )

    fstab_active_unparsed_line_count = sum(
        len(
            representation
            .source_context
            .unparsed_lines
        )
        for representation
        in reconstruction_result.fstab_source_representations
    )

    fstab_source_contents = (
        reconstruction_result
        .fstab_source_contents
    )

    fstab_source_content_status_counts = Counter(
        content.status.value
        for content in fstab_source_contents
    )

    fstab_source_content_contributing_count = sum(
        len(content.contributing_obligation_ids)
        for content in fstab_source_contents
    )

    fstab_source_content_unresolved_obligation_count = sum(
        len(content.unresolved_obligation_ids)
        for content in fstab_source_contents
    )

    fstab_source_content_unresolved_context_count = sum(
        len(content.unresolved_context_ids)
        for content in fstab_source_contents
    )

    ueventd_source_representation_count = len(
        reconstruction_result
        .ueventd_source_representations
    )

    ueventd_reconstructed_obligation_count = sum(
        len(
            representation
            .contributing_obligation_ids
        )
        for representation
        in reconstruction_result
        .ueventd_source_representations
    )

    ueventd_active_source_context_count = len(
        reconstruction_result
        .ueventd_source_representations
    )

    ueventd_active_contexts_with_unparsed_lines = sum(
        1
        for representation
        in reconstruction_result
        .ueventd_source_representations
        if representation.source_context.unparsed_lines
    )

    ueventd_active_unparsed_line_count = sum(
        len(
            representation
            .source_context
            .unparsed_lines
        )
        for representation
        in reconstruction_result
        .ueventd_source_representations
    )

    ueventd_source_contents = (
        reconstruction_result
        .ueventd_source_contents
    )

    ueventd_source_content_status_counts = Counter(
        content.status.value
        for content
        in ueventd_source_contents
    )

    ueventd_source_content_contributing_count = sum(
        len(
            content.contributing_obligation_ids
        )
        for content
        in ueventd_source_contents
    )

    ueventd_source_content_unresolved_obligation_count = sum(
        len(
            content.unresolved_obligation_ids
        )
        for content
        in ueventd_source_contents
    )

    ueventd_source_content_unresolved_context_count = sum(
        len(
            content.unresolved_context_ids
        )
        for content
        in ueventd_source_contents
    )

    vintf_document_representation_count = len(
        reconstruction_result
        .vintf_document_representations
    )

    vintf_source_contents = (
        reconstruction_result
        .vintf_source_contents
    )

    vintf_source_content_status_counts = Counter(
        content.status.value
        for content
        in vintf_source_contents
    )

    vintf_source_content_contributing_count = sum(
        len(
            content.contributing_obligation_ids
        )
        for content
        in vintf_source_contents
    )

    vintf_source_content_unresolved_obligation_count = sum(
        len(
            content.unresolved_obligation_ids
        )
        for content
        in vintf_source_contents
    )

    vintf_source_content_unresolved_context_count = sum(
        len(
            content.unresolved_context_ids
        )
        for content
        in vintf_source_contents
    )

    selinux_source_representation_count = len(
        reconstruction_result
        .selinux_source_representations
    )

    selinux_source_contents = (
        reconstruction_result
        .selinux_source_contents
    )

    selinux_source_content_status_counts = Counter(
        content.status.value
        for content
        in selinux_source_contents
    )

    selinux_source_content_contributing_count = sum(
        len(
            content.contributing_obligation_ids
        )
        for content
        in selinux_source_contents
    )

    selinux_source_content_raw_byte_count = sum(
        len(content.raw_bytes)
        for content
        in selinux_source_contents
        if content.raw_bytes is not None
    )

    represented_reconstruction_work = (
        init_reconstructed_obligation_count
        + runtime_property_representation_count
        + fstab_reconstructed_obligation_count
        + ueventd_reconstructed_obligation_count
        + vintf_document_representation_count
        + selinux_source_representation_count
    )

    pending_reconstruction_work = (
        reconstruction_coverage
        .reconstruction_work
        - represented_reconstruction_work
    )

    if pending_reconstruction_work < 0:
        raise RuntimeError(
            "Reconstructed INIT work exceeds admitted "
            "Reconstruction work"
        )

    reconstruction_report_lines.extend(
        [
            "",
            "=== RECONSTRUCTION ===",
            "Status: SUCCESS",
            (
                "Outcomes: "
                f"{len(reconstruction_result.outcomes)}"
            ),
            (
                "Reconstructed: "
                f"{reconstruction_status_counts.get('reconstructed', 0)}"
            ),
            (
                "Preserved: "
                f"{reconstruction_status_counts.get('preserved', 0)}"
            ),
            (
                "Pending reconstruction work: "
                f"{pending_reconstruction_work}"
            ),
            "",
            "=== RECONSTRUCTION COMPOSITION ===",
            (
                "Relationships: "
                f"{len(composition_relationships)}"
            ),
            "",
            "Canonical Universe relationship status:",
            (
                "  Resolved: "
                f"{composition_relationship_status_counts.get('resolved', 0)}"
            ),
            (
                "  Ambiguous: "
                f"{composition_relationship_status_counts.get('ambiguous', 0)}"
            ),
            (
                "  Unresolved: "
                f"{composition_relationship_status_counts.get('unresolved', 0)}"
            ),
            "",
            "Reconstruction projection coverage:",
            (
                "  Resolved: "
                f"{composition_projection_status_counts.get('resolved', 0)}"
            ),
            (
                "  Unresolved: "
                f"{composition_projection_status_counts.get('unresolved', 0)}"
            ),
            "",
            "Applicability:",
            (
                "  Active: "
                f"{composition_applicability_counts.get('active', 0)}"
            ),
            (
                "  Conditional: "
                f"{composition_applicability_counts.get('conditional', 0)}"
            ),
            (
                "  Alternative: "
                f"{composition_applicability_counts.get('alternative', 0)}"
            ),
            (
                "  Unresolved: "
                f"{composition_applicability_counts.get('unresolved', 0)}"
            ),
            "",
            (
                "Unique endpoints: "
                f"{len(composition_endpoint_by_id)}"
            ),
            "Endpoints:",
            (
                "  Representation: "
                f"{composition_endpoint_kind_counts.get('representation', 0)}"
            ),
            (
                "  Preserved artifact: "
                f"{composition_endpoint_kind_counts.get('preserved_artifact', 0)}"
            ),
            (
                "  Canonical requirement: "
                f"{composition_endpoint_kind_counts.get('canonical_requirement', 0)}"
            ),
            (
                "  Semantic: "
                f"{composition_endpoint_kind_counts.get('semantic', 0)}"
            ),
            (
                "  Unresolved: "
                f"{composition_endpoint_kind_counts.get('unresolved', 0)}"
            ),
            "",
            "By relationship kind:",
        ]
    )

    for relationship_kind in sorted(
        composition_relationship_kind_counts
    ):
        reconstruction_report_lines.append(
            (
                f"  {relationship_kind}: "
                f"{composition_relationship_kind_counts[relationship_kind]}"
            )
        )

    reconstruction_report_lines.extend(
        [
            "",
            "Projection coverage by relationship kind:",
        ]
    )

    for relationship_kind in sorted(
        composition_projection_status_by_kind
    ):
        counts = (
            composition_projection_status_by_kind[
                relationship_kind
            ]
        )

        reconstruction_report_lines.append(
            (
                f"  {relationship_kind}: "
                f"resolved={counts.get('resolved', 0)} "
                f"unresolved={counts.get('unresolved', 0)}"
            )
        )

    reconstruction_report_lines.extend(
        [
            "",
            "=== BUILD-SYSTEM RECONSTRUCTION ===",
            "Status: SUCCESS",
            (
                "Artifact build representations: "
                f"{len(artifact_build_representations)}"
            ),
            (
                "Preserved artifact work: "
                f"{artifact_preserved_work_count}"
            ),
            (
                "Resolved: "
                f"{artifact_build_status_counts.get('resolved', 0)}"
            ),
            (
                "Partial: "
                f"{artifact_build_status_counts.get('partial', 0)}"
            ),
            (
                "Unresolved: "
                f"{artifact_build_status_counts.get('unresolved', 0)}"
            ),
            "",
            "Artifact build roles:",
        ]
    )

    for build_kind in sorted(
        artifact_build_kind_counts
    ):
        reconstruction_report_lines.append(
            (
                f"  {build_kind}: "
                f"{artifact_build_kind_counts[build_kind]}"
            )
        )

    reconstruction_report_lines.extend(
        [
            "",
            "=== INIT RECONSTRUCTION ===",
            (
                "Source representations: "
                f"{init_representation_count}"
            ),
            (
                "Represented obligations: "
                f"{init_reconstructed_obligation_count}"
            ),
            "",
            "=== SOURCE CONTENT ===",
            (
                "INIT RC content units: "
                f"{len(init_source_contents)}"
            ),
            (
                "Synthesized: "
                f"{init_source_content_status_counts.get('synthesized', 0)}"
            ),
            (
                "Partial unresolved: "
                f"{init_source_content_status_counts.get('partial_unresolved', 0)}"
            ),
            "",
            "=== RUNTIME PROPERTY RECONSTRUCTION ===",
            (
                "Representations: "
                f"{runtime_property_representation_count}"
            ),
            (
                "Source content units: "
                f"{len(runtime_property_source_contents)}"
            ),
            (
                "Source content not source declarable: "
                f"{runtime_property_source_content_status_counts.get('not_source_declarable', 0)}"
            ),
            "",
            "=== FSTAB RECONSTRUCTION ===",
            (
                "Source representations: "
                f"{fstab_source_representation_count}"
            ),
            (
                "Represented obligations: "
                f"{fstab_reconstructed_obligation_count}"
            ),
            (
                "Active source contexts: "
                f"{fstab_active_source_context_count}"
            ),
            (
                "Active contexts with unparsed lines: "
                f"{fstab_active_contexts_with_unparsed_lines}"
            ),
            (
                "Preserved unparsed lines available to Source Content: "
                f"{fstab_active_unparsed_line_count}"
            ),
            (
                "Source content units: "
                f"{len(fstab_source_contents)}"
            ),
            (
                "Source content synthesized: "
                f"{fstab_source_content_status_counts.get('synthesized', 0)}"
            ),
            (
                "Source content partial unresolved: "
                f"{fstab_source_content_status_counts.get('partial_unresolved', 0)}"
            ),
            "",
            "=== UEVENTD RECONSTRUCTION ===",
            (
                "Source representations: "
                f"{ueventd_source_representation_count}"
            ),
            (
                "Represented obligations: "
                f"{ueventd_reconstructed_obligation_count}"
            ),
            (
                "Active source contexts: "
                f"{ueventd_active_source_context_count}"
            ),
            (
                "Active contexts with unparsed lines: "
                f"{ueventd_active_contexts_with_unparsed_lines}"
            ),
            (
                "Preserved unparsed lines available to Source Content: "
                f"{ueventd_active_unparsed_line_count}"
            ),
            (
                "Source content units: "
                f"{len(ueventd_source_contents)}"
            ),
            (
                "Source content synthesized: "
                f"{ueventd_source_content_status_counts.get('synthesized', 0)}"
            ),
            (
                "Source content partial unresolved: "
                f"{ueventd_source_content_status_counts.get('partial_unresolved', 0)}"
            ),
            "",
            "=== VINTF RECONSTRUCTION ===",
            (
                "Document representations: "
                f"{vintf_document_representation_count}"
            ),
            (
                "Represented obligations: "
                f"{vintf_document_representation_count}"
            ),
            (
                "Source content units: "
                f"{len(vintf_source_contents)}"
            ),
            (
                "Source content preserved exact: "
                f"{vintf_source_content_status_counts.get('preserved_exact', 0)}"
            ),
            "",
            "=== SELINUX RECONSTRUCTION ===",
            (
                "Source representations: "
                f"{selinux_source_representation_count}"
            ),
            (
                "Represented obligations: "
                f"{selinux_source_representation_count}"
            ),
            (
                "Source content units: "
                f"{len(selinux_source_contents)}"
            ),
            (
                "Source content preserved exact: "
                f"{selinux_source_content_status_counts.get('preserved_exact', 0)}"
            ),
            (
                "Source content opaque: "
                f"{selinux_source_content_status_counts.get('opaque', 0)}"
            ),
        ]
    )

    reconstruction_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    preserved_artifact_build_representation_count = sum(
        1
        for representation
        in artifact_build_representations
        if representation.preserved_artifact_id is not None
    )

    build_system_report_lines = [
        "TreeForge Android Build-System Reconstruction",
        "",
        "=== BUILD-SYSTEM RECONSTRUCTION ===",
        "Status: SUCCESS",
        "",
        (
            "Build representations: "
            f"{len(artifact_build_representations)}"
        ),
        (
            "Preserved artifact work: "
            f"{artifact_preserved_work_count}"
        ),
        "",
        "By status:",
        (
            "  Resolved: "
            f"{artifact_build_status_counts.get('resolved', 0)}"
        ),
        (
            "  Partial: "
            f"{artifact_build_status_counts.get('partial', 0)}"
        ),
        (
            "  Unresolved: "
            f"{artifact_build_status_counts.get('unresolved', 0)}"
        ),
        "",
        "By build role:",
    ]

    for build_kind in sorted(
        artifact_build_kind_counts
    ):
        build_system_report_lines.append(
            (
                f"  {build_kind}: "
                f"{artifact_build_kind_counts[build_kind]}"
            )
        )

    build_system_report_lines.extend(
        [
            "",
            "Partial preserved artifacts by canonical kind:",
        ]
    )

    for artifact_kind in sorted(
        artifact_partial_kind_counts
    ):
        build_system_report_lines.append(
            (
                f"  {artifact_kind}: "
                f"{artifact_partial_kind_counts[artifact_kind]}"
            )
        )

    build_system_report_lines.extend(
        [
            "",
            "Partial preserved artifacts by exact kind tuple:",
        ]
    )

    for kind_tuple in sorted(
        artifact_partial_kind_tuple_counts
    ):
        build_system_report_lines.append(
            (
                "  "
                + ", ".join(kind_tuple)
                + ": "
                + str(
                    artifact_partial_kind_tuple_counts[
                        kind_tuple
                    ]
                )
            )
        )

    build_system_report_lines.extend(
        [
            "",
            "=== APK PACKAGE BUILD PARTICIPATION ===",
            (
                "Canonical APK packages: "
                f"{len(apk_packages)}"
            ),
            (
                "APK PACKAGE build representations: "
                f"{len(apk_build_representations)}"
            ),
            (
                "Requirement-backed packages: "
                f"{apk_requirement_backed_count}"
            ),
            (
                "Preserved-backed packages: "
                f"{apk_preserved_backed_count}"
            ),
            (
                "Canonical overlays: "
                f"{len(apk_overlay_resolutions)}"
            ),
            (
                "Resolved overlay targets: "
                f"{len(apk_resolved_overlay_resolutions)}"
            ),
            (
                "Resolved overlay build dependencies: "
                f"{apk_resolved_overlay_dependency_count}"
            ),
            (
                "Resolved overlays without build dependency: "
                f"{apk_resolved_overlay_missing_dependency_count}"
            ),
            (
                "APK package coverage: "
                + (
                    "PASS"
                    if apk_package_coverage_match
                    else "FAIL"
                )
            ),
            (
                "Overlay dependency coverage: "
                + (
                    "PASS"
                    if apk_overlay_dependency_coverage_match
                    else "FAIL"
                )
            ),
            "",
            "=== BOOT BUILD PARTICIPATION ===",
            (
                "Canonical boot-family requirements: "
                f"{len(boot_requirements)}"
            ),
            (
                "BOOT_ARTIFACT build representations: "
                f"{len(boot_build_representations)}"
            ),
            (
                "Boot-family build coverage: "
                + (
                    "PASS"
                    if boot_build_coverage_match
                    else "FAIL"
                )
            ),
            *(
                (
                    f"  {kind}: "
                    f"{boot_build_kind_counts.get(kind, 0)}"
                    f"/{count}"
                )
                for kind, count
                in sorted(
                    boot_requirement_kind_counts.items()
                )
            ),
            "",
            "=== DTBO BUILD PARTICIPATION ===",
            (
                "Canonical DTBO requirements: "
                f"{len(dtbo_requirements)}"
            ),
            (
                "DTBO_ARTIFACT build representations: "
                f"{len(dtbo_build_representations)}"
            ),
            (
                "DTBO build coverage: "
                + (
                    "PASS"
                    if dtbo_build_coverage_match
                    else "FAIL"
                )
            ),
            (
                "DTBO population entries: "
                f"{len(dtbo_population_entries)}"
            ),
            (
                "DTBO population identity coverage: "
                + (
                    "PASS"
                    if dtbo_population_identity_match
                    else "FAIL"
                )
            ),
            "",
            "=== VBMETA / AVB BUILD PARTICIPATION ===",
            (
                "Canonical VBMeta requirements: "
                f"{len(vbmeta_requirements)}"
            ),
            (
                "Standalone VBMeta roots: "
                f"{len(vbmeta_standalone_requirements)}"
            ),
            (
                "Embedded/footer VBMeta requirements: "
                f"{len(vbmeta_embedded_requirements)}"
            ),
            (
                "Partition-backed canonical AVB requirements: "
                f"{len(vbmeta_topology_partition_backed_requirements)}"
            ),
            (
                "VBMETA_ARTIFACT build representations: "
                f"{len(vbmeta_build_representations)}"
            ),
            (
                "Standalone VBMeta image build coverage: "
                + (
                    "PASS"
                    if vbmeta_build_coverage_match
                    else "FAIL"
                )
            ),
            (
                "AVB topology requirements: "
                f"{len(avb_topology_requirements)}"
            ),
            (
                "AVB topology partition coverage: "
                + (
                    "PASS"
                    if avb_topology_partition_coverage_match
                    else "FAIL"
                )
            ),
            (
                "AVB topology exact identity coverage: "
                + (
                    "PASS"
                    if avb_topology_identity_match
                    else "FAIL"
                )
            ),
            "",
            "=== CLASSPATH / JAVA BUILD PARTICIPATION ===",
            (
                "Effective Classpath entries: "
                f"{classpath_effective_entry_count}"
            ),
            (
                "Installed-JAR resolutions: "
                f"{sum(classpath_installed_jar_status_counts.values())}"
            ),
            (
                "  Resolved: "
                f"{classpath_installed_jar_status_counts.get('resolved', 0)}"
            ),
            (
                "  Absent: "
                f"{classpath_installed_jar_status_counts.get('absent', 0)}"
            ),
            (
                "  Ambiguous: "
                f"{classpath_installed_jar_status_counts.get('ambiguous', 0)}"
            ),
            (
                "Resolved Classpath entries: "
                f"{classpath_resolved_resolution_count}"
            ),
            (
                "Unique resolved Java artifacts: "
                f"{len(classpath_resolved_artifact_ids)}"
            ),
            (
                "JAVA_LIBRARY build representations: "
                f"{len(classpath_java_representation_ids)}"
            ),
            (
                "Preserved-backed Java representations: "
                f"{classpath_java_preserved_backed_count}"
            ),
            (
                "Requirement-backed Java representations: "
                f"{classpath_java_requirement_backed_count}"
            ),
            (
                "Resolved Java artifact coverage: "
                + (
                    "PASS"
                    if classpath_java_coverage_match
                    else "FAIL"
                )
            ),
            "",
            "=== BUILD DEPENDENCY INTEGRITY ===",
            (
                "Build representations validated: "
                f"{build_dependency_validation.representation_count}"
            ),
            (
                "Representations with dependencies: "
                f"{build_dependency_validation.representations_with_dependencies}"
            ),
            (
                "Physical build dependency edges: "
                f"{build_dependency_validation.dependency_edge_count}"
            ),
            (
                "ELF-owned dependency edges: "
                f"{len(build_dependency_elf_owned_edges)}"
            ),
            (
                "Kernel-owned dependency edges: "
                f"{len(build_dependency_kernel_owned_edges)}"
            ),
            (
                "APK/RRO-owned dependency edges: "
                f"{len(build_dependency_apk_owned_edges)}"
            ),
            (
                "Family-owned dependency edge union: "
                f"{len(build_dependency_owned_edge_union)}"
            ),
            (
                "Cross-family duplicate ownership: "
                f"{build_dependency_family_overlap_count}"
            ),
            (
                "Missing family-owned dependency edges: "
                f"{len(build_dependency_missing_owned_edges)}"
            ),
            (
                "Unowned physical dependency edges: "
                f"{len(build_dependency_unowned_actual_edges)}"
            ),
            (
                "Dependency ownership coverage: "
                + (
                    "PASS"
                    if build_dependency_ownership_match
                    else "FAIL"
                )
            ),
            "Dependency target integrity: PASS",
            "Self-dependency integrity: PASS",
            "Dependency uniqueness: PASS",
            "Dependency ordering: PASS",
            "",
            "=== KERNEL MODULE BUILD PARTICIPATION ===",
            (
                "Canonical kernel modules: "
                f"{kernel_module_count}"
            ),
            (
                "Physical kernel-module build representations: "
                f"{kernel_module_physical_representation_count}"
            ),
            (
                "Kernel-module physical coverage: "
                + (
                    "PASS"
                    if kernel_module_build_coverage_match
                    else "FAIL"
                )
            ),
            (
                "Canonical modules.dep hard dependencies: "
                f"{kernel_module_hard_dependency_count}"
            ),
            (
                "Expected physical kernel-module dependency edges: "
                f"{len(kernel_module_expected_dependency_edges)}"
            ),
            (
                "Physical kernel-module dependency edges: "
                f"{len(kernel_module_physical_dependency_edges)}"
            ),
            (
                "Missing physical kernel-module dependency edges: "
                f"{kernel_module_missing_dependency_edge_count}"
            ),
            (
                "Invalid kernel-module dependency targets: "
                f"{kernel_module_invalid_dependency_target_count}"
            ),
            (
                "Kernel-module dependency projection: "
                + (
                    "PASS"
                    if kernel_module_dependency_projection_match
                    else "FAIL"
                )
            ),
            "",
            "Kernel-module configuration build participation:",
            (
                "  Canonical modules.* configuration sources: "
                f"{kernel_module_configuration_count}"
            ),
            (
                "  modules.* build representations: "
                f"{kernel_module_configuration_representation_count}"
            ),
            (
                "  modules.* build coverage: "
                + (
                    "PASS"
                    if kernel_module_configuration_coverage_match
                    else "FAIL"
                )
            ),
            *(
                f"    {kind}: {count}"
                for kind, count
                in sorted(
                    kernel_module_configuration_kind_counts.items()
                )
            ),
            "",
            "=== APEX BUILD PARTICIPATION ===",
            (
                "Canonical APEX requirements: "
                f"{len(apex_requirements)}"
            ),
            (
                "APEX build representations: "
                f"{len(apex_build_representations)}"
            ),
            (
                "Requirement-backed APEX representations: "
                f"{apex_requirement_backed_count}"
            ),
            (
                "Preserved-backed APEX representations: "
                f"{apex_preserved_backed_count}"
            ),
            (
                "APEX role representations: "
                f"{apex_role_count}"
            ),
            (
                "APEX representations with partition: "
                f"{apex_with_partition_count}"
            ),
            (
                "APEX representations with Android path: "
                f"{apex_with_android_path_count}"
            ),
            (
                "APEX build coverage: "
                + (
                    "PASS"
                    if apex_package_coverage_match
                    else "FAIL"
                )
            ),
            "",
            "=== ELF BUILD-SYSTEM SEMANTICS ===",
            (
                "Semantic projections: "
                f"{len(elf_build_semantics)}"
            ),
            (
                "Attached to Artifact build representation: "
                f"{elf_build_attached_count}"
            ),
            (
                "Without Artifact build representation: "
                f"{elf_build_unattached_count}"
            ),
            (
                "With DT_NEEDED observations: "
                f"{elf_build_with_dependencies_count}"
            ),
            (
                "Without DT_NEEDED observations: "
                f"{elf_build_without_dependencies_count}"
            ),
            (
                "DT_NEEDED observations: "
                f"{elf_build_dependency_name_count}"
            ),
            (
                "Resolved build dependencies: "
                f"{elf_build_resolved_dependency_count}"
            ),
            "",
            "Physical ELF dependency projection:",
            (
                "  Physical ELF build representations: "
                f"{elf_physical_build_representation_count}"
            ),
            (
                "  ELF build reps with dependencies: "
                f"{elf_build_representations_with_dependencies_count}"
            ),
            (
                "  Final dependency edges on ELF-backed representations: "
                f"{elf_physical_dependency_edge_count}"
            ),
            (
                "  Expected physical ELF dependency edges: "
                f"{len(elf_expected_physical_dependency_edges)}"
            ),
            (
                "  Resolved providers with physical target: "
                f"{elf_resolved_provider_with_physical_target_count}"
            ),
            (
                "  Resolved providers without physical target: "
                f"{elf_resolved_provider_without_physical_target_count}"
            ),
            (
                "  Resolved self dependencies omitted: "
                f"{elf_resolved_provider_self_dependency_count}"
            ),
            (
                "  Missing physical ELF dependency edges: "
                f"{elf_missing_physical_dependency_edge_count}"
            ),
            (
                "  Invalid build dependency targets: "
                f"{elf_invalid_dependency_target_count}"
            ),
            (
                "  ELF dependency projection: "
                + (
                    "PASS"
                    if elf_dependency_projection_match
                    else "FAIL"
                )
            ),
            "",
            "By semantic status:",
        ]
    )

    for status in sorted(
        elf_build_status_counts
    ):
        build_system_report_lines.append(
            (
                f"  {status}: "
                f"{elf_build_status_counts[status]}"
            )
        )

    build_system_report_lines.extend(
        [
            "",
            "By ELF role:",
        ]
    )

    for role in sorted(
        elf_build_role_counts
    ):
        build_system_report_lines.append(
            (
                f"  {role}: "
                f"{elf_build_role_counts[role]}"
            )
        )

    build_system_report_lines.extend(
        [
            "",
            "=== ARTIFACT BUILD REPRESENTATIONS ===",
            (
                "Representations: "
                f"{len(artifact_build_representations)}"
            ),
            (
                "Preserved-artifact-backed representations: "
                f"{preserved_artifact_build_representation_count}"
            ),
            (
                "Exact preserved-artifact coverage: "
                f"{artifact_preserved_work_count}"
            ),
            (
                "Coverage match: "
                + (
                    "PASS"
                    if (
                        preserved_artifact_build_representation_count
                        == artifact_preserved_work_count
                    )
                    else "FAIL"
                )
            ),
        ]
    )

    preserved_artifact_coverage_match = (
        preserved_artifact_build_representation_count
        == artifact_preserved_work_count
    )

    elf_semantic_population_match = (
        len(elf_build_semantics)
        == len(
            runtime_linking_result
            .universe
            .elf_requirements
        )
    )

    build_participation_completion_checks = (
        (
            "Preserved canonical Artifact coverage",
            preserved_artifact_coverage_match,
        ),
        (
            "APK package coverage",
            apk_package_coverage_match,
        ),
        (
            "APK overlay dependency coverage",
            apk_overlay_dependency_coverage_match,
        ),
        (
            "Boot-family coverage",
            boot_build_coverage_match,
        ),
        (
            "DTBO build coverage",
            dtbo_build_coverage_match,
        ),
        (
            "DTBO population identity coverage",
            dtbo_population_identity_match,
        ),
        (
            "Standalone VBMeta image build coverage",
            vbmeta_build_coverage_match,
        ),
        (
            "AVB topology partition coverage",
            avb_topology_partition_coverage_match,
        ),
        (
            "AVB topology exact identity coverage",
            avb_topology_identity_match,
        ),
        (
            "Classpath / Java artifact coverage",
            classpath_java_coverage_match,
        ),
        (
            "Kernel-module physical coverage",
            kernel_module_build_coverage_match,
        ),
        (
            "Kernel-module configuration coverage",
            kernel_module_configuration_coverage_match,
        ),
        (
            "Kernel-module dependency projection",
            kernel_module_dependency_projection_match,
        ),
        (
            "APEX build coverage",
            apex_package_coverage_match,
        ),
        (
            "ELF semantic population coverage",
            elf_semantic_population_match,
        ),
        (
            "ELF dependency projection",
            elf_dependency_projection_match,
        ),
        (
            "Physical dependency ownership coverage",
            build_dependency_ownership_match,
        ),
        (
            "No unresolved build representations",
            (
                artifact_build_status_counts.get(
                    "unresolved",
                    0,
                )
                == 0
            ),
        ),
    )

    build_participation_completion_pass = all(
        passed
        for _, passed
        in build_participation_completion_checks
    )

    build_system_report_lines.extend(
        [
            "",
            "=== BUILD PARTICIPATION COMPLETION ===",
            (
                "Coverage checks: "
                f"{len(build_participation_completion_checks)}"
            ),
            (
                "Passed: "
                f"{sum(passed for _, passed in build_participation_completion_checks)}"
            ),
            (
                "Failed: "
                f"{sum(not passed for _, passed in build_participation_completion_checks)}"
            ),
            (
                "Zero silent build-participation omissions: "
                + (
                    "PASS"
                    if build_participation_completion_pass
                    else "FAIL"
                )
            ),
            (
                "Build participation complete: "
                + (
                    "PASS"
                    if build_participation_completion_pass
                    else "FAIL"
                )
            ),
            "",
            "Coverage matrix:",
            *(
                (
                    f"  {name}: "
                    + (
                        "PASS"
                        if passed
                        else "FAIL"
                    )
                )
                for name, passed
                in build_participation_completion_checks
            ),
        ]
    )

    build_system_report_path = (
        reconstruction_root
        / "build-system-report.txt"
    )

    build_system_report_path.write_text(
        "\n".join(
            build_system_report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    source_content_report_lines = [
        "TreeForge Android Source Content Synthesis",
        "",
        "=== SOURCE CONTENT ===",
        "Status: SUCCESS",
        "",
        (
            "Content units: "
            f"{len(init_source_contents) + len(runtime_property_source_contents) + len(fstab_source_contents) + len(ueventd_source_contents) + len(vintf_source_contents) + len(selinux_source_contents)}"
        ),
        "",
        "By media kind:",
        (
            "  INIT RC: "
            f"{init_source_content_media_kind_counts.get('init_rc', 0)}"
        ),
        (
            "  PROPERTY: "
            f"{len(runtime_property_source_contents)}"
        ),
        (
            "  FSTAB: "
            f"{len(fstab_source_contents)}"
        ),
        (
            "  UEVENTD: "
            f"{len(ueventd_source_contents)}"
        ),
        (
            "  VINTF XML: "
            f"{len(vintf_source_contents)}"
        ),
        (
            "  SELinux: "
            f"{len(selinux_source_contents)}"
        ),
        "",
        "By status:",
        (
            "  Synthesized: "
            f"{init_source_content_status_counts.get('synthesized', 0) + fstab_source_content_status_counts.get('synthesized', 0) + ueventd_source_content_status_counts.get('synthesized', 0)}"
        ),
        (
            "  Partial unresolved: "
            f"{init_source_content_status_counts.get('partial_unresolved', 0) + fstab_source_content_status_counts.get('partial_unresolved', 0) + ueventd_source_content_status_counts.get('partial_unresolved', 0)}"
        ),
        (
            "  Preserved exact: "
            f"{init_source_content_status_counts.get('preserved_exact', 0) + vintf_source_content_status_counts.get('preserved_exact', 0) + selinux_source_content_status_counts.get('preserved_exact', 0)}"
        ),
        (
            "  Not source declarable: "
            f"{init_source_content_status_counts.get('not_source_declarable', 0) + runtime_property_source_content_status_counts.get('not_source_declarable', 0)}"
        ),
        (
            "  Opaque: "
            f"{init_source_content_status_counts.get('opaque', 0) + selinux_source_content_status_counts.get('opaque', 0)}"
        ),
        "",
        "=== INIT RC SOURCE CONTENT ===",
        (
            "Content units: "
            f"{len(init_source_contents)}"
        ),
        (
            "Contributing obligations: "
            f"{init_source_content_contributing_count}"
        ),
        (
            "Excluded obligations: "
            f"{init_source_content_excluded_count}"
        ),
        (
            "Unresolved obligations: "
            f"{init_source_content_unresolved_count}"
        ),
        (
            "Complete synthesized units: "
            f"{init_source_content_status_counts.get('synthesized', 0)}"
        ),
        (
            "Partial unresolved units: "
            f"{init_source_content_status_counts.get('partial_unresolved', 0)}"
        ),
        "",
        "=== RUNTIME PROPERTY SOURCE CONTENT ===",
        (
            "Content units: "
            f"{len(runtime_property_source_contents)}"
        ),
        (
            "Contributing obligations: "
            f"{runtime_property_source_content_contributing_count}"
        ),
        (
            "Not source declarable units: "
            f"{runtime_property_source_content_status_counts.get('not_source_declarable', 0)}"
        ),
        (
            "Rendered text units: "
            f"{runtime_property_source_content_text_count}"
        ),
        (
            "Raw byte units: "
            f"{runtime_property_source_content_raw_byte_count}"
        ),
        "",
        "=== FSTAB SOURCE CONTENT ===",
        (
            "Content units: "
            f"{len(fstab_source_contents)}"
        ),
        (
            "Contributing obligations: "
            f"{fstab_source_content_contributing_count}"
        ),
        (
            "Unresolved obligations: "
            f"{fstab_source_content_unresolved_obligation_count}"
        ),
        (
            "Unresolved source-context lines: "
            f"{fstab_source_content_unresolved_context_count}"
        ),
        (
            "Complete synthesized units: "
            f"{fstab_source_content_status_counts.get('synthesized', 0)}"
        ),
        (
            "Partial unresolved units: "
            f"{fstab_source_content_status_counts.get('partial_unresolved', 0)}"
        ),
        "",
        "=== UEVENTD SOURCE CONTENT ===",
        (
            "Content units: "
            f"{len(ueventd_source_contents)}"
        ),
        (
            "Contributing obligations: "
            f"{ueventd_source_content_contributing_count}"
        ),
        (
            "Unresolved obligations: "
            f"{ueventd_source_content_unresolved_obligation_count}"
        ),
        (
            "Unresolved source-context lines: "
            f"{ueventd_source_content_unresolved_context_count}"
        ),
        (
            "Complete synthesized units: "
            f"{ueventd_source_content_status_counts.get('synthesized', 0)}"
        ),
        (
            "Partial unresolved units: "
            f"{ueventd_source_content_status_counts.get('partial_unresolved', 0)}"
        ),
        "",
        "=== VINTF SOURCE CONTENT ===",
        (
            "Content units: "
            f"{len(vintf_source_contents)}"
        ),
        (
            "Contributing obligations: "
            f"{vintf_source_content_contributing_count}"
        ),
        (
            "Unresolved obligations: "
            f"{vintf_source_content_unresolved_obligation_count}"
        ),
        (
            "Unresolved source context: "
            f"{vintf_source_content_unresolved_context_count}"
        ),
        (
            "Preserved exact units: "
            f"{vintf_source_content_status_counts.get('preserved_exact', 0)}"
        ),
        (
            "Partial unresolved units: "
            f"{vintf_source_content_status_counts.get('partial_unresolved', 0)}"
        ),
        "",
        "=== SELINUX SOURCE CONTENT ===",
        (
            "Content units: "
            f"{len(selinux_source_contents)}"
        ),
        (
            "Contributing obligations: "
            f"{selinux_source_content_contributing_count}"
        ),
        (
            "Preserved exact units: "
            f"{selinux_source_content_status_counts.get('preserved_exact', 0)}"
        ),
        (
            "Opaque units: "
            f"{selinux_source_content_status_counts.get('opaque', 0)}"
        ),
        (
            "Exact raw bytes: "
            f"{selinux_source_content_raw_byte_count}"
        ),
    ]

    source_content_report_path = (
        reconstruction_root
        / "source-content-report.txt"
    )

    source_content_report_path.write_text(
        "\n".join(
            source_content_report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    reconstruction_report_path = (
        reconstruction_root
        / "reconstruction-report.txt"
    )

    reconstruction_report_path.write_text(
        "\n".join(
            reconstruction_report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    typer.echo(
        "Status: SUCCESS"
    )

    if show_report_paths:
        typer.echo(
            f"Report: {reconstruction_report_path}"
        )
        typer.echo(
            f"Source Content report: {source_content_report_path}"
        )
        typer.echo(
            f"Build-System report: {build_system_report_path}"
        )

    return reconstruction_result
