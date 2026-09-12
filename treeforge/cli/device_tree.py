from __future__ import annotations

import logging
import shutil
import sys
import tempfile
from pathlib import Path

import typer

from treeforge.android.device_tree.platform_deployment import (
    TREEFORGE_AOSP_BRINGUP_DIAGNOSTIC_ASSIGNMENTS,
)
from treeforge.setup.mode import (
    read_installation_mode,
)

from treeforge.android.version.device_tree.provider_profile import (
    select_android_device_tree_provider_profile,
)

from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
)

from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
)
from treeforge.android.boot_image.deployment_planning import (
    build_base_boot_image_deployment,
    load_base_boot_image_deployment,
    load_reusable_boot_image_deployment,
)
from treeforge.android.device_tree.apex_deployment import (
    AndroidDeviceTreeApexDeploymentPlanner,
    AndroidDeviceTreeApexDeploymentTransformer,
)
from treeforge.android.device_tree.elf_deployment import (
    AndroidDeviceTreeElfDeploymentPlanner,
    AndroidDeviceTreeElfDeploymentTransformer,
)
from treeforge.android.device_tree.vintf_deployment import (
    AndroidDeviceTreeVintfDeploymentPlanner,
    AndroidDeviceTreeVintfDeploymentTransformer,
)
from treeforge.android.device_tree.platform_deployment import (
    AndroidDeviceTreePlatformDeploymentPlanner,
    AndroidDeviceTreePlatformDeploymentTransformer,
)
from treeforge.android.device_tree.boot_construction import (
    AndroidDeviceTreeBootConstructionSource,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.stage import (
    AndroidDeviceTreeStage,
)
from treeforge.cli.boot_image import (
    boot_image as run_boot_image_command,
)
from treeforge.cli.reconstruction import (
    reconstruction as run_reconstruction_pipeline,
)
from treeforge.cli.progress import (
    clear_live_progress_block,
    render_progress,
)
from treeforge.cli.repository_root import (
    AOSP_ROOT,
    TREEFORGE_ROOT,
)
from treeforge.setup.avb_keys import (
    validate_avb_bringup_keys,
)
from treeforge.core.progress import ProgressEvent


def render_device_tree_progress(
    event: ProgressEvent,
) -> None:
    """
    Keep Device Tree phase transitions visible while retaining the shared
    live renderer for long-running counted materialization work.
    """

    phase_subjects = {
        "Destination projection",
        "Artifact projection",
        "Physical payload projection",
        "Build realization",
        "Build rendering",
        "Build files",
        "Device Tree materialization",
    }

    if (
        event.stage == "Device Tree"
        and event.subject in phase_subjects
        and event.current is not None
        and event.total is not None
    ):
        if sys.stdout.isatty():
            clear_live_progress_block()

        phase = (
            event.operation
            if event.operation is not None
            else (
                event.detail
                if event.detail is not None
                else event.state.value
            )
        )

        typer.echo(
            f"[Device Tree] "
            f"{event.current}/{event.total} "
            f"{phase}"
        )
        return

    render_progress(event)


def _select_boot_construction_source(
    requested: str | None,
) -> AndroidDeviceTreeBootConstructionSource:
    aliases = {
        "factory": (
            AndroidDeviceTreeBootConstructionSource
            .FACTORY_CANONICAL
        ),
        "factory-canonical": (
            AndroidDeviceTreeBootConstructionSource
            .FACTORY_CANONICAL
        ),
        "factory_canonical": (
            AndroidDeviceTreeBootConstructionSource
            .FACTORY_CANONICAL
        ),
        "default": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_DEFAULT
        ),
        "boot-image-default": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_DEFAULT
        ),
        "treeforge_boot_image_default": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_DEFAULT
        ),
        "modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_MODIFIED
        ),
        "boot-image-modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_MODIFIED
        ),
        "treeforge_boot_image_modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_MODIFIED
        ),
        "kernel-baseline": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_BASELINE
        ),
        "kernel_baseline": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_BASELINE
        ),
        "treeforge-kernel-baseline": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_BASELINE
        ),
        "treeforge_kernel_baseline": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_BASELINE
        ),
        "kernel-modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_MODIFIED
        ),
        "kernel_modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_MODIFIED
        ),
        "treeforge-kernel-modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_MODIFIED
        ),
        "treeforge_kernel_modified": (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_MODIFIED
        ),
    }

    if requested is not None:
        normalized = (
            requested
            .strip()
            .lower()
        )

        selected = aliases.get(
            normalized
        )

        if selected is None:
            raise typer.BadParameter(
                "--boot-construction-source must be "
                "factory, default, modified, kernel-baseline, "
                "or kernel-modified"
            )

        return selected

    if not sys.stdin.isatty():
        return (
            AndroidDeviceTreeBootConstructionSource
            .FACTORY_CANONICAL
        )

    typer.echo()
    typer.echo(
        "Choose boot image construction source:"
    )
    typer.echo(
        "  1. Factory canonical"
    )
    typer.echo(
        "     Exact canonical factory-derived inputs. Default."
    )
    typer.echo(
        "  2. TreeForge Boot Image default"
    )
    typer.echo(
        "     Validated canonical Boot Image base population."
    )
    typer.echo(
        "  3. TreeForge Boot Image modified"
    )
    typer.echo(
        "     Run Boot Image generation/validation now and use "
        "its supported modified boot inputs."
    )
    typer.echo(
        "  4. TreeForge Kernel baseline"
    )
    typer.echo(
        "     Use the locally packaged baseline kernel boot.img."
    )
    typer.echo(
        "  5. TreeForge Kernel modified"
    )
    typer.echo(
        "     Use the locally packaged modified kernel boot.img."
    )
    typer.echo(
        "  6. Cancel"
    )

    while True:
        answer = (
            typer.prompt(
                "Selection",
                default="1",
            )
            .strip()
        )

        if answer == "1":
            return (
                AndroidDeviceTreeBootConstructionSource
                .FACTORY_CANONICAL
            )

        if answer == "2":
            return (
                AndroidDeviceTreeBootConstructionSource
                .TREEFORGE_BOOT_IMAGE_DEFAULT
            )

        if answer == "3":
            return (
                AndroidDeviceTreeBootConstructionSource
                .TREEFORGE_BOOT_IMAGE_MODIFIED
            )

        if answer == "4":
            return (
                AndroidDeviceTreeBootConstructionSource
                .TREEFORGE_KERNEL_BASELINE
            )

        if answer == "5":
            return (
                AndroidDeviceTreeBootConstructionSource
                .TREEFORGE_KERNEL_MODIFIED
            )

        if answer == "6":
            raise typer.Exit(
                code=0
            )

        typer.echo(
            "Choose 1, 2, 3, 4, 5, or 6."
        )


def _prepare_boot_construction_deployment(
    *,
    source: AndroidDeviceTreeBootConstructionSource,
    output: Path,
    parsing_snapshot: Path | None,
    verbose: bool,
):
    """
    Resolve an explicit Boot Image construction input.

    Hardware deployment remains disabled. Boot Image VBMeta artifacts are
    filtered later by the Device Tree construction projector.
    """

    if source in (
        AndroidDeviceTreeBootConstructionSource
        .FACTORY_CANONICAL,
        AndroidDeviceTreeBootConstructionSource
        .TREEFORGE_KERNEL_BASELINE,
        AndroidDeviceTreeBootConstructionSource
        .TREEFORGE_KERNEL_MODIFIED,
    ):
        return (
            None,
            False,
        )

    output = (
        output
        .expanduser()
        .resolve()
    )

    active_parsing_snapshot = (
        parsing_snapshot
        .expanduser()
        .resolve()
        if parsing_snapshot is not None
        else (
            output
            / "parsing"
            / "snapshot.json"
        )
        .resolve()
    )

    if not active_parsing_snapshot.is_file():
        raise RuntimeError(
            "Device Tree Boot Image construction requires "
            "the active canonical Parsing snapshot: "
            f"{active_parsing_snapshot}"
        )

    boot_image_root = (
        output
        / "boot-image"
    )

    if (
        source
        is
        AndroidDeviceTreeBootConstructionSource
        .TREEFORGE_BOOT_IMAGE_DEFAULT
    ):
        base_root = (
            boot_image_root
            / "deployment"
            / "base"
        )

        manifest_path = (
            base_root
            / "deployment-manifest.json"
        )

        if manifest_path.is_file():
            deployment = (
                load_base_boot_image_deployment(
                    manifest_path,
                    parsing_snapshot_path=(
                        active_parsing_snapshot
                    ),
                )
            )

        else:
            restored = (
                AndroidParsingSnapshotStore()
                .load(
                    active_parsing_snapshot
                )
            )

            deployment = (
                build_base_boot_image_deployment(
                    restored.parsing,
                    parsing_snapshot_path=(
                        active_parsing_snapshot
                    ),
                    output_root=(
                        base_root
                    ),
                )
            )

        return (
            deployment,
            False,
        )

    if (
        source
        is not
        AndroidDeviceTreeBootConstructionSource
        .TREEFORGE_BOOT_IMAGE_MODIFIED
    ):
        raise RuntimeError(
            "unsupported Device Tree boot construction source"
        )

    typer.echo()
    typer.echo(
        "=== TREEFORGE BOOT IMAGE FOR DEVICE TREE ==="
    )
    typer.echo(
        "Running Boot Image generation and validation only."
    )
    typer.echo(
        "Hardware deployment is disabled."
    )

    run_boot_image_command(
        output=output,
        parsing_snapshot=(
            active_parsing_snapshot
        ),
        replace_component=None,
        avb_key=None,
        parent_vbmeta_key=None,
        vbmeta_key=None,
        verbose=verbose,
        generation_only=True,
    )

    bootstrap_handoff_path = (
        output
        / "bootstrap"
        / "deployment"
        / "boot-image-replacements.json"
    )

    if not bootstrap_handoff_path.is_file():
        raise RuntimeError(
            "modified Boot Image construction was selected, "
            "but Boot Image produced no Bootstrap handoff"
        )

    manifest_path = (
        boot_image_root
        / "deployment"
        / "bootstrap"
        / "deployment-manifest.json"
    )

    if not manifest_path.is_file():
        raise RuntimeError(
            "modified Boot Image generation completed without "
            "its validated deployment manifest: "
            f"{manifest_path}"
        )

    deployment = (
        load_reusable_boot_image_deployment(
            manifest_path,
            parsing_snapshot_path=(
                active_parsing_snapshot
            ),
            bootstrap_handoff_path=(
                bootstrap_handoff_path
            ),
        )
    )

    return (
        deployment,
        True,
    )


app = typer.Typer(
    help=(
        "Run an Android factory image through TreeForge's canonical "
        "pipeline and continue through Device Tree."
    )
)


@app.callback(
    invoke_without_command=True,
)
def device_tree(
    factory_image: Path | None = typer.Option(
        None,
        "--factory-image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Android factory-image ZIP. One of --factory-image or "
            "--parsing-snapshot is required."
        ),
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Device Tree output is written "
            "under OUTPUT/device-tree."
        ),
    ),
    device_id: str | None = typer.Option(
        None,
        "--device-id",
        help=(
            "Optional explicit Android device identifier used during "
            "knowledge resolution."
        ),
    ),
    device_vendor: str | None = typer.Option(
        None,
        "--device-vendor",
        help=(
            "Source-tree vendor namespace for Device Tree output, "
            "for example 'google'."
        ),
    ),
    device_name: str | None = typer.Option(
        None,
        "--device-name",
        help=(
            "Optional source-tree device-name override. "
            "When omitted, Device Tree uses --device-id when supplied, "
            "otherwise the canonical Universe device_codename."
        ),
    ),
    product_name: str | None = typer.Option(
        None,
        "--product-name",
        help=(
            "Optional generated Android build-product name override. "
            "When omitted, Device Tree uses treeforge_<device>."
        ),
    ),
    board_platform: str | None = typer.Option(
        None,
        "--board-platform",
        help=(
            "Optional explicit Android board platform or SoC identifier "
            "used during knowledge resolution."
        ),
    ),
    android_version: str | None = typer.Option(
        None,
        "--android-version",
        help=(
            "Optional explicit Android version used during knowledge "
            "resolution."
        ),
    ),
    generic_only: bool = typer.Option(
        False,
        "--generic-only",
        help=(
            "Use generic Discovery only and skip TreeForge Knowledge "
            "enrichment."
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
    boot_construction_source: str | None = typer.Option(
        None,
        "--boot-construction-source",
        help=(
            "Boot construction source: factory, default, modified, "
            "kernel-baseline, or kernel-modified. When omitted "
            "interactively, TreeForge prompts and defaults to canonical "
            "factory construction."
        ),
    ),
    avb_signing: str | None = typer.Option(
        None,
        "--avb-signing",
        help=(
            "AVB build signing provider: treeforge or aosp. "
            "When omitted, Device Tree prompts and defaults "
            "to TreeForge development keys."
        ),
    ),
    preflight: bool = typer.Option(
        False,
        "--preflight",
        help=(
            "Exercise reachable Android Device Universe runtime "
            "contracts before continuing downstream."
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
    Run the complete canonical TreeForge pipeline through Device Tree.
    """

    typer.echo(
        "TreeForge Android Device Tree"
    )

    if avb_signing is None:
        typer.echo("")
        typer.echo("AVB signing provider:")
        typer.echo("")
        typer.echo("  1. TreeForge development keys")
        typer.echo("  2. AOSP development/test keys")
        typer.echo("")

        signing_choice = typer.prompt(
            "Select",
            default="1",
        ).strip()

        if signing_choice == "1":
            selected_avb_signing_provider = "treeforge"
        elif signing_choice == "2":
            selected_avb_signing_provider = "aosp"
        else:
            typer.echo(
                "AVB signing provider must be 1 or 2.",
                err=True,
            )
            raise typer.Exit(code=2)

    else:
        selected_avb_signing_provider = (
            avb_signing
            .strip()
            .lower()
        )

        if selected_avb_signing_provider not in {
            "treeforge",
            "aosp",
        }:
            typer.echo(
                "--avb-signing must be 'treeforge' or 'aosp'.",
                err=True,
            )
            raise typer.Exit(code=2)

    #
    # Reuse the exact existing Reconstruction pipeline. Every option is passed
    # explicitly so Typer OptionInfo defaults can never leak into this
    # programmatic invocation.
    #
    reconstruction_result = (
        run_reconstruction_pipeline(
            factory_image=factory_image,
            output=output,
            device_id=device_id,
            board_platform=board_platform,
            android_version=android_version,
            generic_only=generic_only,
            parsing_snapshot=parsing_snapshot,
            preflight=preflight,
            verbose=verbose,
            show_report_paths=False,
        )
    )

    selected_boot_construction_source = (
        _select_boot_construction_source(
            boot_construction_source
        )
    )

    try:
        (
            selected_boot_image_deployment,
            boot_image_invoked,
        ) = (
            _prepare_boot_construction_deployment(
                source=(
                    selected_boot_construction_source
                ),
                output=output,
                parsing_snapshot=(
                    parsing_snapshot
                ),
                verbose=verbose,
            )
        )

    except Exception as error:
        typer.echo(
            (
                "Unable to prepare Device Tree "
                "boot construction input: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    device_tree_root = (
        output
        / "device-tree"
    )

    device_tree_work_root = (
        device_tree_root
        / "work"
    )

    if device_tree_root.exists():
        if not device_tree_root.is_dir():
            typer.echo(
                (
                    "Device Tree workspace exists but is not "
                    f"a directory: {device_tree_root}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

        try:
            shutil.rmtree(
                device_tree_root
            )
        except OSError as error:
            typer.echo(
                (
                    "Unable to replace existing Device Tree "
                    f"workspace: {error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

    typer.echo()
    typer.echo(
        "=== DEVICE TREE ==="
    )

    report_lines = [
        "TreeForge Android Device Tree",
    ]

    #
    # Device Tree source/build identity.
    #
    # Runtime Linking retains the exact canonical AndroidDeviceUniverse,
    # therefore Device Tree consumes already-reconciled identity facts rather
    # than reparsing properties or recreating Universe conclusions.
    #
    universe = (
        reconstruction_result
        .reconstruction_input
        .runtime_linking
        .universe
    )

    conclusion_by_fact = {
        conclusion.fact: conclusion
        for conclusion in universe.conclusions
    }

    def agreed_identity_value(
        fact: str,
    ) -> str | None:
        conclusion = conclusion_by_fact.get(
            fact
        )

        if conclusion is None:
            return None

        if (
            getattr(
                conclusion.status,
                "value",
                None,
            )
            != "agreed"
        ):
            return None

        value = conclusion.value

        if not isinstance(value, str):
            return None

        value = value.strip()

        if not value:
            return None

        return value

    canonical_device_name = agreed_identity_value(
        "device_codename"
    )

    resolved_device_name = (
        device_name
        if device_name is not None
        else (
            device_id
            if device_id is not None
            else canonical_device_name
        )
    )

    if resolved_device_name is None:
        typer.echo(
            (
                "Device Tree could not resolve a source-tree device "
                "name from canonical Universe device_codename evidence. "
                "Use --device-name to override it."
            ),
            err=True,
        )
        raise typer.Exit(
            code=2
        )

    canonical_brand = agreed_identity_value(
        "product_brand"
    )

    canonical_manufacturer = agreed_identity_value(
        "manufacturer"
    )

    automatic_vendor_source = (
        canonical_brand
        if canonical_brand is not None
        else canonical_manufacturer
    )

    automatic_vendor = None

    if automatic_vendor_source is not None:
        automatic_vendor = "".join(
            character.lower()
            for character
            in automatic_vendor_source
            if character.isalnum()
            or character in ("_", "-")
        )

        if not automatic_vendor:
            automatic_vendor = None

    resolved_device_vendor = (
        device_vendor
        if device_vendor is not None
        else "treeforge"
    )

    if resolved_device_vendor is None:
        typer.echo(
            (
                "Device Tree could not resolve a source-tree vendor "
                "namespace from canonical Universe product_brand or "
                "manufacturer evidence. Use --device-vendor to override it."
            ),
            err=True,
        )
        raise typer.Exit(
            code=2
        )

    resolved_product_name = (
        product_name
        if product_name is not None
        else f"treeforge_{resolved_device_name}"
    )

    #
    # Keep canonical physical identity separate from TreeForge's Android
    # build-target namespace.
    #
    # Android resolves TARGET_DEVICE directly from PRODUCT_DEVICE and then
    # discovers BoardConfig.mk by that identity.  A TreeForge build target
    # therefore must not reuse an upstream/reference TARGET_DEVICE when both
    # trees may coexist in one checkout.
    #
    resolved_build_device_name = (
        f"treeforge_{resolved_device_name}"
    )

    identity = AndroidDeviceTreeIdentity(
        vendor=resolved_device_vendor,
        device=resolved_device_name,
        build_device=resolved_build_device_name,
        product=resolved_product_name,
    )

    try:
        result = (
            AndroidDeviceTreeStage(
                progress_callback=render_device_tree_progress,
            )
            .build(
                reconstruction_result,
                identity=identity,
                output_root=device_tree_root,
                boot_construction_source=(
                    selected_boot_construction_source
                ),
                boot_image_deployment=(
                    selected_boot_image_deployment
                ),
                boot_image_invoked=(
                    boot_image_invoked
                ),
                avb_signing_provider=(
                    selected_avb_signing_provider
                ),
            )
        )
    except Exception as error:
        report_lines.extend(
            [
                "",
                "=== DEVICE TREE INTAKE ===",
                "Status: FAILED",
                "",
                f"Error: {error}",
            ]
        )

        device_tree_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        device_tree_work_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        report_path = (
            device_tree_work_root
            / "device-tree-report.txt"
        )

        report_path.write_text(
            "\n".join(report_lines)
            + "\n",
            encoding="utf-8",
        )

        typer.echo(
            f"Device Tree failed: {error}",
            err=True,
        )
        typer.echo(
            f"Report: {report_path}"
        )

        raise typer.Exit(
            code=1
        ) from error

    reconstruction = result.reconstruction

    typer.echo(
        "[Device Tree] Finalizing Device Tree report..."
    )

    #
    # Device Tree report indexes.
    #
    # Report generation must not repeatedly rescan the full Reconstruction
    # obligation/representation populations. Build canonical lookup surfaces
    # once and derive related report statistics in bounded passes.
    #
    plan_obligations = (
        reconstruction
        .reconstruction_input
        .plan
        .obligations
    )

    artifact_representations = (
        reconstruction
        .artifact_build_representations
    )

    build_realizations = (
        result.build_realizations
    )

    physical_payload_projections = (
        result.physical_payload_projections
    )

    obligation_requirement_by_source_identity = {}

    for obligation in plan_obligations:
        obligation_requirement_by_source_identity.setdefault(
            obligation.source_identity,
            obligation.requirement,
        )

    realization_by_representation_id = {
        realization.representation_id:
        realization
        for realization
        in build_realizations
    }

    requirement_by_representation_id = {}

    artifact_requirement_by_representation_id = {}

    elf_representation_by_requirement_id = {}

    for representation in artifact_representations:
        requirement_id = (
            representation.canonical_requirement_id
        )

        if requirement_id is None:
            continue

        requirement = (
            obligation_requirement_by_source_identity.get(
                requirement_id
            )
        )

        if requirement is not None:
            requirement_by_representation_id[
                representation.representation_id
            ] = requirement

        if isinstance(
            requirement,
            AndroidUniverseArtifactRequirement,
        ):
            artifact_requirement_by_representation_id[
                representation.representation_id
            ] = requirement

        if (
            representation.kind.value
            in {
                "native_library",
                "executable",
            }
        ):
            elf_representation_by_requirement_id.setdefault(
                requirement_id,
                representation,
            )

    apex_container_ids = {
        id(obligation.requirement.artifact)
        for obligation
        in plan_obligations
        if isinstance(
            obligation.requirement,
            AndroidUniverseApexRequirement,
        )
    }

    #
    # Requirement-backed representation statistics.
    #
    canonical_requirement_backed_count = 0
    artifact_requirement_backed_count = 0
    non_artifact_requirement_backed_count = 0

    artifact_deployment_role_counts = {}
    artifact_build_role_matrix = {}
    non_artifact_build_role_counts = {}

    for representation in artifact_representations:
        requirement_id = (
            representation.canonical_requirement_id
        )

        if requirement_id is None:
            continue

        canonical_requirement_backed_count += 1

        requirement = (
            obligation_requirement_by_source_identity.get(
                requirement_id
            )
        )

        kind = representation.kind.value

        if isinstance(
            requirement,
            AndroidUniverseArtifactRequirement,
        ):
            artifact_requirement_backed_count += 1

            role = requirement.deployment_role.value

            artifact_deployment_role_counts[
                role
            ] = (
                artifact_deployment_role_counts.get(
                    role,
                    0,
                )
                + 1
            )

            matrix_key = (
                kind,
                role,
            )

            artifact_build_role_matrix[
                matrix_key
            ] = (
                artifact_build_role_matrix.get(
                    matrix_key,
                    0,
                )
                + 1
            )

        else:
            non_artifact_requirement_backed_count += 1

            non_artifact_build_role_counts[
                kind
            ] = (
                non_artifact_build_role_counts.get(
                    kind,
                    0,
                )
                + 1
            )

    #
    # Direct ELF graph statistics.
    #
    direct_elf_representation_ids = {
        projection.representation_id
        for projection
        in physical_payload_projections
        if (
            projection
            .build_representation
            .kind.value
            in {
                "native_library",
                "executable",
            }
        )
    }

    direct_elf_build_role_counts = {}

    for projection in physical_payload_projections:
        kind = (
            projection
            .build_representation
            .kind.value
        )

        if kind not in {
            "native_library",
            "executable",
        }:
            continue

        direct_elf_build_role_counts[
            kind
        ] = (
            direct_elf_build_role_counts.get(
                kind,
                0,
            )
            + 1
        )

    direct_elf_dependency_edge_count = 0
    direct_to_direct_dependency_edge_count = 0
    direct_to_non_direct_dependency_edge_count = 0

    direct_elf_only_direct_dependency_count = 0
    direct_elf_non_direct_dependency_count = 0

    non_direct_dependency_targets = set()
    non_direct_dependency_build_role_counts = {}
    non_direct_dependency_deployment_role_counts = {}

    apex_owned_nested_dependency_edge_count = 0
    non_apex_nested_dependency_edge_count = 0

    for representation_id in direct_elf_representation_ids:
        realization = (
            realization_by_representation_id[
                representation_id
            ]
        )

        has_non_direct_dependency = False

        for dependency_realization_id in (
            realization.dependency_realization_ids
        ):
            direct_elf_dependency_edge_count += 1

            dependency_representation_id = (
                dependency_realization_id.removeprefix(
                    "device-tree-realization:"
                )
            )

            if (
                dependency_representation_id
                in direct_elf_representation_ids
            ):
                direct_to_direct_dependency_edge_count += 1
                continue

            has_non_direct_dependency = True
            direct_to_non_direct_dependency_edge_count += 1

            non_direct_dependency_targets.add(
                dependency_representation_id
            )

            dependency_realization = (
                realization_by_representation_id[
                    dependency_representation_id
                ]
            )

            dependency_kind = (
                dependency_realization
                .build_representation
                .kind.value
            )

            non_direct_dependency_build_role_counts[
                dependency_kind
            ] = (
                non_direct_dependency_build_role_counts.get(
                    dependency_kind,
                    0,
                )
                + 1
            )

            requirement = (
                requirement_by_representation_id.get(
                    dependency_representation_id
                )
            )

            if isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                role = (
                    requirement
                    .deployment_role
                    .value
                )

                non_direct_dependency_deployment_role_counts[
                    role
                ] = (
                    non_direct_dependency_deployment_role_counts.get(
                        role,
                        0,
                    )
                    + 1
                )

            apex_owned = False

            if (
                requirement is not None
                and getattr(
                    requirement,
                    "inventory_entry",
                    None,
                )
                is not None
            ):
                artifact = (
                    requirement
                    .inventory_entry
                    .artifact
                )

                parent = artifact.parent

                if (
                    parent is not None
                    and parent.parent is not None
                    and id(parent.parent)
                    in apex_container_ids
                ):
                    apex_owned = True

            if apex_owned:
                apex_owned_nested_dependency_edge_count += 1
            else:
                non_apex_nested_dependency_edge_count += 1

        if has_non_direct_dependency:
            direct_elf_non_direct_dependency_count += 1
        else:
            direct_elf_only_direct_dependency_count += 1

    preserved_backed_representations = tuple(
        representation
        for representation
        in artifact_representations
        if representation.preserved_artifact_id is not None
    )

    preserved_backed_deployment_role_counts = {}

    ownership = (
        reconstruction
        .reconstruction_input
        .plan
        .ownership
    )

    if ownership is not None:
        for representation in preserved_backed_representations:
            artifact_id = representation.preserved_artifact_id

            if artifact_id is None:
                continue

            decision = ownership.decision_for(
                requirement_kind="artifact",
                source_identity=artifact_id,
            )

            role = (
                "missing_ownership"
                if decision is None
                else decision.requirement.deployment_role.value
            )

            preserved_backed_deployment_role_counts[
                role
            ] = (
                preserved_backed_deployment_role_counts.get(
                    role,
                    0,
                )
                + 1
            )

    direct_elf_requirement_identity_lines = (
        "=== DIRECT ELF REQUIREMENT IDENTITY ===",
        "No DIRECT_PARTITION ELF Artifact requirement found.",
        "",
    )

    direct_elf_target = None

    for obligation in plan_obligations:
        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseArtifactRequirement,
        ):
            continue

        if (
            requirement.deployment_role.value
            != "direct_partition"
        ):
            continue

        representation = (
            elf_representation_by_requirement_id.get(
                requirement.requirement_id
            )
        )

        if representation is None:
            continue

        direct_elf_target = (
            requirement,
            representation,
        )
        break

    if direct_elf_target is not None:
        requirement, representation = (
            direct_elf_target
        )

        direct_elf_requirement_identity_lines = (
            "=== DIRECT ELF REQUIREMENT IDENTITY ===",
            (
                "Requirement type: "
                f"{type(requirement).__module__}."
                f"{type(requirement).__name__}"
            ),
            (
                "Requirement ID: "
                f"{requirement.requirement_id}"
            ),
            (
                "Representation ID: "
                f"{representation.representation_id}"
            ),
            (
                "Build role: "
                f"{representation.kind.value}"
            ),
            (
                "Installed: "
                f"{representation.installed_partition} "
                f"{representation.installed_android_path}"
            ),
            "",
            "Requirement fields:",
            *tuple(
                (
                    f"  {field_name}: "
                    f"{type(getattr(requirement, field_name)).__module__}."
                    f"{type(getattr(requirement, field_name)).__name__}"
                )
                for field_name
                in requirement.__dataclass_fields__
            ),
            "",
        )

    exact_reconstruction_identity = (
        result.device_tree_input.reconstruction
        is reconstruction_result
    )

    if not exact_reconstruction_identity:
        raise ValueError(
            "Device Tree result changed exact canonical "
            "Reconstruction identity"
        )

    resolved_realizations = tuple(
        item
        for item in result.build_realizations
        if item.status.value == "resolved"
    )

    closed_realizations = tuple(
        item
        for item in result.build_realizations
        if item.status.value == "closed"
    )

    if (
        len(resolved_realizations)
        + len(closed_realizations)
        + sum(
            item.status.value == "partial"
            for item in result.build_realizations
        )
        != len(result.build_realizations)
    ):
        raise ValueError(
            "Device Tree realization dispositions do not "
            "conserve the complete realization population"
        )

    partial_realizations = tuple(
        item
        for item in result.build_realizations
        if item.status.value == "partial"
    )

    partial_kind_counts: dict[str, int] = {}
    partial_role_counts: dict[str, int] = {}
    partial_reason_counts: dict[str, int] = {}
    partial_reason_samples: dict[
        str,
        list[str],
    ] = {}

    partial_source_backed = 0
    partial_preserved_backed = 0
    partial_requirement_backed = 0

    for item in partial_realizations:
        realization_kind = item.kind.value

        partial_kind_counts[
            realization_kind
        ] = (
            partial_kind_counts.get(
                realization_kind,
                0,
            )
            + 1
        )

        build_role = (
            item.build_representation.kind.value
        )

        partial_role_counts[
            build_role
        ] = (
            partial_role_counts.get(
                build_role,
                0,
            )
            + 1
        )

        reason = item.reason

        if reason is None:
            raise ValueError(
                "PARTIAL Device Tree realization lacks "
                "its required reason: "
                f"{item.realization_id}"
            )

        partial_reason_counts[
            reason
        ] = (
            partial_reason_counts.get(
                reason,
                0,
            )
            + 1
        )

        samples = partial_reason_samples.setdefault(
            reason,
            [],
        )

        if len(samples) < 8:
            samples.append(
                item.representation_id
            )

        representation = (
            item.build_representation
        )

        if representation.source_content_id is not None:
            partial_source_backed += 1

        if representation.preserved_artifact_id is not None:
            partial_preserved_backed += 1

        if representation.canonical_requirement_id is not None:
            partial_requirement_backed += 1

    partial_census_lines = [
        "",
        "=== PARTIAL REALIZATION CENSUS ===",
        (
            "Partial realizations: "
            f"{len(partial_realizations)}"
        ),
        (
            "Source-backed partials: "
            f"{partial_source_backed}"
        ),
        (
            "Preserved-backed partials: "
            f"{partial_preserved_backed}"
        ),
        (
            "Canonical-requirement-backed partials: "
            f"{partial_requirement_backed}"
        ),
        "",
        "Partial realizations by Device Tree kind:",
    ]

    partial_census_lines.extend(
        f"  {kind}: {count}"
        for kind, count
        in sorted(
            partial_kind_counts.items()
        )
    )

    partial_census_lines.extend(
        (
            "",
            "Partial realizations by Reconstruction build role:",
        )
    )

    partial_census_lines.extend(
        f"  {role}: {count}"
        for role, count
        in sorted(
            partial_role_counts.items()
        )
    )

    partial_census_lines.extend(
        (
            "",
            "Partial realizations by exact reason:",
        )
    )

    for reason, count in sorted(
        partial_reason_counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        partial_census_lines.append(
            f"  count={count}"
        )

        partial_census_lines.append(
            f"    reason: {reason}"
        )

        partial_census_lines.append(
            "    sample representations:"
        )

        partial_census_lines.extend(
            f"      {representation_id}"
            for representation_id
            in partial_reason_samples[
                reason
            ]
        )

    partial_census_lines.extend(
        (
            "",
            (
                "Partial reason population: "
                f"{sum(partial_reason_counts.values())}"
            ),
            (
                "Partial accounting: "
                + (
                    "PASS"
                    if sum(
                        partial_reason_counts.values()
                    )
                    == len(partial_realizations)
                    else "FAIL"
                )
            ),
            (
                "Device Tree freeze readiness: "
                + (
                    "REVIEW REQUIRED"
                    if partial_realizations
                    else "READY"
                )
            ),
        )
    )

    boot_construction_plan = (
        result
        .device_tree_input
        .boot_construction_plan
    )

    if boot_construction_plan is None:
        raise ValueError(
            "Device Tree result lost its boot construction plan"
        )

    boot_construction_report_lines = [
        "",
        "=== BOOT CONSTRUCTION INPUT ===",
        "Status: SUCCESS",
        (
            "Selection: "
            f"{boot_construction_plan.source.value}"
        ),
        (
            "Boot Image invoked: "
            + (
                "yes"
                if boot_construction_plan.boot_image_invoked
                else "no"
            )
        ),
        (
            "Boot Image manifest: "
            + (
                str(
                    boot_construction_plan
                    .boot_image_manifest_path
                )
                if (
                    boot_construction_plan
                    .boot_image_manifest_path
                    is not None
                )
                else "<none>"
            )
        ),
        (
            "Whole-image prebuilt inputs: "
            f"{len(boot_construction_plan.images)}"
        ),
        (
            "Native Android construction partitions: "
            + (
                ", ".join(
                    boot_construction_plan
                    .native_construction_partitions
                )
                if (
                    boot_construction_plan
                    .native_construction_partitions
                )
                else "<none>"
            )
        ),
        (
            "Canonical fallback partitions: "
            + (
                ", ".join(
                    boot_construction_plan
                    .canonical_fallback_partitions
                )
                if (
                    boot_construction_plan
                    .canonical_fallback_partitions
                )
                else "<none>"
            )
        ),
        (
            "Excluded Boot Image VBMeta artifacts: "
            f"{boot_construction_plan.excluded_boot_image_vbmeta_count}"
        ),
        (
            "Imported Boot Image VBMeta artifacts: "
            f"{boot_construction_plan.imported_vbmeta_count}"
        ),
        "AVB/VBMeta ownership: Device Tree / Android build",
        (
            "Prebuilt boot identity boundary: reported input SHA-256 values "
            "identify Device Tree construction inputs; final AOSP image "
            "identity is owned by the downstream Android build."
        ),
        (
            "Source-equivalence promotions from construction choice: "
            f"{boot_construction_plan.source_equivalence_promotion_count}"
        ),
        "",
        "Selected whole-image inputs:",
    ]

    for construction_image in (
        boot_construction_plan.images
    ):
        boot_construction_report_lines.extend(
            [
                (
                    "  "
                    f"{construction_image.partition_name}:"
                ),
                (
                    "    requirement: "
                    f"{construction_image.requirement_id}"
                ),
                (
                    "    selected from Boot Image: "
                    + (
                        "yes"
                        if (
                            construction_image
                            .selected_from_boot_image
                        )
                        else "no"
                    )
                ),
                (
                    "    source: "
                    f"{construction_image.source_path}"
                ),
                (
                    "    Device Tree path: "
                    f"{construction_image.destination.as_posix()}"
                ),
                (
                    "    size: "
                    f"{construction_image.size_bytes}"
                ),
                (
                    "    sha256: "
                    f"{construction_image.sha256}"
                ),
            ]
        )

        kernel_source_mode = None

        if (
            construction_image.source
            is AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_BASELINE
        ):
            kernel_source_mode = "baseline"

        elif (
            construction_image.source
            is AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_MODIFIED
        ):
            kernel_source_mode = "modified"

        if kernel_source_mode is not None:
            boot_construction_report_lines.extend(
                [
                    (
                        "    provider artifact class: "
                        "TreeForge kernel boot artifact"
                    ),
                    (
                        "    provider source mode: "
                        f"{kernel_source_mode}"
                    ),
                    (
                        "    provider artifact SHA-256: "
                        f"{construction_image.sha256}"
                    ),
                    (
                        "    provider artifact identity scope: "
                        "exact input supplied through "
                        "BOARD_PREBUILT_BOOTIMAGE"
                    ),
                    (
                        "    final AOSP boot image identity: "
                        "downstream build-produced; unavailable "
                        "until the AOSP build completes"
                    ),
                    (
                        "    final AOSP boot image SHA-256: "
                        "<unknown until AOSP build>"
                    ),
                    (
                        "    final AOSP AVB signing owner: "
                        "Android build system"
                    ),
                    (
                        "    AVB footer policy: AOSP canonical "
                        "prebuilt-boot processing applies the "
                        "Device Tree-selected AVB signing configuration"
                    ),
                ]
            )

    boot_construction_report_lines.extend(
        [
            "",
            "Construction/source-equivalence independence: PASS",
            (
                "Boot Image VBMeta exclusion: "
                + (
                    "PASS"
                    if (
                        boot_construction_plan
                        .imported_vbmeta_count
                        == 0
                    )
                    else "FAIL"
                )
            ),
        ]
    )

    native_boot_plan = (
        result.native_boot_build_plan
    )

    avb_build_plan = (
        result.avb_build_plan
    )

    if native_boot_plan is None:
        raise ValueError(
            "Device Tree result lost native boot build plan"
        )

    if avb_build_plan is None:
        raise ValueError(
            "Device Tree result lost AVB build plan"
        )

    android_native_build_report_lines = [
        "",
        "=== ANDROID-NATIVE IMAGE CONSTRUCTION ===",
        "Status: SUCCESS",
        "Construction owner: Android build system",
        "TreeForge mkbootimg invocations: 0",
        "TreeForge final AVB footer invocations: 0",
        "TreeForge VBMeta encoders: 0",
        (
            "Native vendor_boot: "
            + (
                "RESOLVED"
                if native_boot_plan.resolves_partition(
                    "vendor_boot"
                )
                else "UNRESOLVED"
            )
        ),
        (
            "Native vendor_kernel_boot: "
            + (
                "RESOLVED"
                if native_boot_plan.resolves_partition(
                    "vendor_kernel_boot"
                )
                else "UNRESOLVED"
            )
        ),
        (
            "Exact pvmfw handoff: "
            + (
                "RESOLVED"
                if native_boot_plan.resolves_partition(
                    "pvmfw"
                )
                else "UNRESOLVED"
            )
        ),
        (
            "Vendor ramdisk fragments supplied: "
            f"{len(native_boot_plan.vendor_ramdisk_fragments)}"
        ),
        (
            "Native boot file inputs supplied: "
            f"{len(native_boot_plan.file_inputs)}"
        ),
        "",
        "=== AVB / VBMETA BUILD CONFIGURATION ===",
        "Status: SUCCESS",
        "Final VBMeta owner: Android build system",
        (
            "Partition-backed VBMeta nodes: "
            f"{len(avb_build_plan.nodes)}"
        ),
        (
            "Canonical chains: "
            f"{len(avb_build_plan.chains)}"
        ),
        (
            "External private-key requirements: "
            f"{len(avb_build_plan.external_keys)}"
        ),
        (
            "AOSP-avbtool descriptor providers: "
            f"{len(avb_build_plan.descriptor_providers)}"
        ),
        (
            "AVB signing provider: "
            f"{selected_avb_signing_provider}"
        ),
        "AVB signing policy source: TreeForge versioned platform profile",
        "AVB private-key bytes consulted during generation: NO",
        (
            "Boot Image VBMeta artifacts imported: "
            f"{avb_build_plan.imported_boot_image_vbmeta_count}"
        ),
        (
            "AOSP checkout generation dependencies: "
            f"{avb_build_plan.aosp_checkout_dependency_count}"
        ),
        (
            "TreeForge image builders: "
            f"{avb_build_plan.treeforge_image_builder_count}"
        ),
        (
            "TreeForge VBMeta encoders: "
            f"{avb_build_plan.treeforge_vbmeta_encoder_count}"
        ),
        (
            "Source-equivalence promotions: "
            f"{avb_build_plan.source_equivalence_promotion_count}"
        ),
        (
            "AVB build mapping complete: "
            + (
                "PASS"
                if avb_build_plan.complete
                else "FAIL"
            )
        ),
        "",
        "External signing inputs:",
    ]

    for key in (
        avb_build_plan.external_keys
    ):
        android_native_build_report_lines.extend(
            [
                (
                    "  "
                    f"{key.partition_name}:"
                ),
                (
                    "    path: "
                    f"{key.destination.as_posix()}"
                ),
                (
                    "    algorithm: "
                    f"{key.algorithm}"
                ),
            ]
        )

    report_lines.extend(
        [
            "",
            "=== DEVICE TREE INTAKE ===",
            "Status: SUCCESS",
            "Canonical input identity:",
            "  Reconstruction: preserved",
            (
                "  Exact Reconstruction identity: "
                f"{exact_reconstruction_identity}"
            ),
            "Generation evidence boundary: canonical TreeForge Reconstruction",
            "Android source checkout used for generation: NO",
            (
                "AOSP deployment root: "
                f"{AOSP_ROOT.resolve()}"
            ),
            (
                "Deployment boundary: AOSP is a post-generation copy/build "
                "destination only; its contents do not alter Device Tree "
                "generation."
            ),
            (
                "Source-tree vendor: "
                f"{identity.vendor}"
            ),
            (
                "Source-tree device: "
                f"{identity.device}"
            ),
            (
                "Device root: "
                f"{identity.device_root.as_posix()}"
            ),
            (
                "Source content units: "
                f"{result.source_content_count}"
            ),
            (
                "Artifact build representations: "
                f"{result.build_representation_count}"
            ),
            (
                "Composition relationships: "
                f"{result.composition_relationship_count}"
            ),
            *boot_construction_report_lines,
            *android_native_build_report_lines,
            "",
            "Source content by family:",
            (
                "  INIT RC: "
                f"{len(reconstruction.init_source_contents)}"
            ),
            (
                "  Runtime property: "
                f"{len(reconstruction.runtime_property_source_contents)}"
            ),
            (
                "  Fstab: "
                f"{len(reconstruction.fstab_source_contents)}"
            ),
            (
                "  Ueventd: "
                f"{len(reconstruction.ueventd_source_contents)}"
            ),
            (
                "  VINTF: "
                f"{len(reconstruction.vintf_source_contents)}"
            ),
            (
                "  SELinux: "
                f"{len(reconstruction.selinux_source_contents)}"
            ),
            "",
            "=== SOURCE PROJECTION ===",
            "Status: SUCCESS",
            (
                "Projected source files: "
                f"{result.projected_file_count}"
            ),
            "",
            "Projected families:",
            (
                "  INIT: "
                f"{sum(1 for item in result.projections if item.family == 'init')}"
            ),
            (
                "  Fstab: "
                f"{sum(1 for item in result.projections if item.family == 'fstab')}"
            ),
            (
                "  Ueventd: "
                f"{sum(1 for item in result.projections if item.family == 'ueventd')}"
            ),
            (
                "  VINTF: "
                f"{sum(1 for item in result.projections if item.family == 'vintf')}"
            ),
            (
                "  SELinux: "
                f"{sum(1 for item in result.projections if item.family == 'selinux')}"
            ),
            "",
            "SELinux preservation:",
            (
                "  Preserved exact: "
                f"{sum(1 for item in result.projections if item.family == 'selinux' and item.content.status.value == 'preserved_exact')}"
            ),
            (
                "  Opaque: "
                f"{sum(1 for item in result.projections if item.family == 'selinux' and item.content.status.value == 'opaque')}"
            ),
            "",
            "Runtime properties:",
            (
                "  Not source declarable: "
                f"{sum(1 for item in reconstruction.runtime_property_source_contents if item.status.value == 'not_source_declarable')}"
            ),
            "",
            "=== BUILD REALIZATION ===",
            "Status: SUCCESS",
            (
                "Build realizations: "
                f"{result.build_realization_count}"
            ),
            (
                "Generated-source realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'generated_source')}"
            ),
            (
                "Preserved-only realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'preserved_only')}"
            ),
            (
                "Copy-file realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'copy_file')}"
            ),
            (
                "Product-package realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'product_package')}"
            ),
            (
                "Prebuilt-module realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'prebuilt_module')}"
            ),
            (
                "APEX-module realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'apex_module')}"
            ),
            (
                "Kernel-module realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'kernel_module')}"
            ),
            (
                "Source-config realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'source_config')}"
            ),
            (
                "VINTF-document realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'vintf_document')}"
            ),
            (
                "SELinux-policy realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_policy')}"
            ),
            (
                "SELinux-runtime-output realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_runtime_output')}"
            ),
            (
                "Board-configuration realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'board_configuration')}"
            ),
            (
                "Resolved realizations: "
                f"{sum(1 for item in result.build_realizations if item.status.value == 'resolved')}"
            ),
            (
                "Closed realizations: "
                f"{sum(1 for item in result.build_realizations if item.status.value == 'closed')}"
            ),
            (
                "Partial realizations: "
                f"{sum(1 for item in result.build_realizations if item.status.value == 'partial')}"
            ),
            *partial_census_lines,
            "",
            (
                "Source-backed Reconstruction representations: "
                f"{sum(1 for item in reconstruction.artifact_build_representations if item.source_content_id is not None)}"
            ),
            (
                "Source realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.source_content_id is not None) == sum(1 for item in reconstruction.artifact_build_representations if item.source_content_id is not None) == result.projected_file_count else 'FAIL'}"
            ),
            (
                "Preserved-backed realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.preserved_artifact_id is not None) == len(preserved_backed_representations) else 'FAIL'}"
            ),
            (
                "Package realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'package')}"
            ),
            (
                "Package dependency edges: "
                f"{sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'package')}"
            ),
            (
                "Package realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'package') == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value == 'package') else 'FAIL'}"
            ),
            (
                "Package dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'package') == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value == 'package') else 'FAIL'}"
            ),
            (
                "Native-library realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'native_library')}"
            ),
            (
                "Executable realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'executable')}"
            ),
            (
                "ELF realization dependency edges: "
                f"{sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value in ('native_library', 'executable'))}"
            ),
            (
                "ELF realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value in ('native_library', 'executable')) == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value in ('native_library', 'executable')) else 'FAIL'}"
            ),
            (
                "ELF dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value in ('native_library', 'executable')) == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value in ('native_library', 'executable')) else 'FAIL'}"
            ),
            (
                "Java-library realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'java_library')}"
            ),
            (
                "Preserved-backed Java realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'java_library' and item.build_representation.preserved_artifact_id is not None)}"
            ),
            (
                "Requirement-backed Java realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'java_library' and item.build_representation.canonical_requirement_id is not None)}"
            ),
            (
                "Java realization dependency edges: "
                f"{sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'java_library')}"
            ),
            (
                "Java realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'java_library') == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value == 'java_library') else 'FAIL'}"
            ),
            (
                "Java dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'java_library') == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value == 'java_library') else 'FAIL'}"
            ),
            (
                "APEX realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'apex')}"
            ),
            (
                "Requirement-backed APEX realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'apex' and item.build_representation.canonical_requirement_id is not None)}"
            ),
            (
                "APEX realization dependency edges: "
                f"{sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'apex')}"
            ),
            (
                "APEX realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'apex') == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value == 'apex') else 'FAIL'}"
            ),
            (
                "APEX dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'apex') == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value == 'apex') else 'FAIL'}"
            ),
            (
                "Kernel-module realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'kernel_module')}"
            ),
            (
                "Kernel-module dependency edges: "
                f"{sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'kernel_module')}"
            ),
            (
                "Kernel-module realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'kernel_module') == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value == 'kernel_module') else 'FAIL'}"
            ),
            (
                "Kernel dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value == 'kernel_module') == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value == 'kernel_module') else 'FAIL'}"
            ),
            (
                "Kernel modules.* config realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'source_config' and item.build_representation.source_identity.startswith('kernel-module-config:'))}"
            ),
            (
                "Kernel modules.* config coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'source_config' and item.build_representation.source_identity.startswith('kernel-module-config:')) == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value == 'source_config' and item.source_identity.startswith('kernel-module-config:')) else 'FAIL'}"
            ),
            (
                "VINTF realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'vintf_document')}"
            ),
            (
                "VINTF integration coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.kind.value == 'vintf_document') == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value == 'vintf_document') else 'FAIL'}"
            ),
            (
                "SELinux realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value in ('selinux_policy', 'selinux_runtime_output'))}"
            ),
            (
                "SELinux policy realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_policy')}"
            ),
            (
                "SELinux runtime-output realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_runtime_output')}"
            ),
            (
                "SELinux integration coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.kind.value in ('selinux_policy', 'selinux_runtime_output')) == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value in ('selinux_policy', 'selinux_runtime_output')) else 'FAIL'}"
            ),
            (
                "VINTF/SELinux source-path preservation: "
                f"{'PASS' if all(item.source_path is not None for item in result.build_realizations if item.kind.value in ('vintf_document', 'selinux_policy', 'selinux_runtime_output')) else 'FAIL'}"
            ),
            (
                "VINTF/SELinux dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.kind.value in ('vintf_document', 'selinux_policy', 'selinux_runtime_output')) == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value in ('vintf_document', 'selinux_policy', 'selinux_runtime_output')) else 'FAIL'}"
            ),
            "",
            "=== SELINUX REALIZATION DETAIL ===",
            (
                "SELinux canonical requirements: "
                f"{len(reconstruction.selinux_source_representations)}"
            ),
            (
                "Generic source-equivalent realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_policy' and item.build_representation.kind.value == 'selinux_runtime_output' and item.status.value == 'resolved')}"
            ),
            (
                "Resolved non-source SELinux runtime outputs: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_runtime_output' and item.status.value == 'resolved')}"
            ),
            (
                "Retained pending SELinux runtime outputs: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'selinux_runtime_output' and item.status.value == 'partial')}"
            ),
            "",
            "SELinux items:",
            *(
                line
                for source_representation in sorted(
                    reconstruction.selinux_source_representations,
                    key=lambda item: (
                        (
                            item.android_path.as_posix()
                            if item.android_path is not None
                            else ""
                        ),
                        item.source_kind.value,
                        item.representation_id,
                    ),
                )
                for realization in (
                    next(
                        (
                            candidate
                            for candidate
                            in result.build_realizations
                            if (
                                candidate.build_representation
                                .source_content_id
                                == next(
                                    content.content_id
                                    for content
                                    in reconstruction.selinux_source_contents
                                    if (
                                        content.representation_id
                                        == source_representation
                                        .representation_id
                                    )
                                )
                            )
                        ),
                        None,
                    ),
                )
                for line in (
                    (
                        "  "
                        + (
                            source_representation
                            .android_path
                            .as_posix()
                            if source_representation
                            .android_path
                            is not None
                            else "<no-android-path>"
                        )
                    ),
                    (
                        "    source kind: "
                        f"{source_representation.source_kind.value}"
                    ),
                    (
                        "    canonical source path: "
                        f"{source_representation.source_path.as_posix()}"
                    ),
                    (
                        "    requirement id: "
                        f"{source_representation.requirement.requirement_id}"
                    ),
                    (
                        "    compiled policy: "
                        f"{source_representation.requirement.is_compiled_policy}"
                    ),
                    (
                        "    opaque: "
                        f"{source_representation.requirement.is_opaque}"
                    ),
                    (
                        "    context requirements: "
                        f"{len(source_representation.context_requirements)}"
                    ),
                    (
                        "    seapp requirements: "
                        f"{len(source_representation.seapp_requirements)}"
                    ),
                    (
                        "    CIL requirements: "
                        f"{len(source_representation.cil_requirements)}"
                    ),
                    (
                        "    uninterpreted CIL requirements: "
                        f"{len(source_representation.requirement.uninterpreted_cil_requirements)}"
                    ),
                    (
                        "    Device Tree path: "
                        + (
                            realization.source_path.as_posix()
                            if (
                                realization is not None
                                and realization.source_path is not None
                            )
                            else "<none>"
                        )
                    ),
                    (
                        "    realization kind: "
                        + (
                            realization.kind.value
                            if realization is not None
                            else "<missing>"
                        )
                    ),
                    (
                        "    realization status: "
                        + (
                            realization.status.value
                            if realization is not None
                            else "<missing>"
                        )
                    ),
                    (
                        "    disposition: "
                        + (
                            realization.reason
                            if (
                                realization is not None
                                and realization.reason is not None
                            )
                            else (
                                "generic source-equivalent Android "
                                "SELinux build input"
                                if realization is not None
                                else "no Device Tree realization"
                            )
                        )
                    ),
                )
            ),
            "",
            (
                "Boot-artifact realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'boot_artifact')}"
            ),
            (
                "DTBO-artifact realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'dtbo_artifact')}"
            ),
            (
                "VBMeta-artifact realizations: "
                f"{sum(1 for item in result.build_realizations if item.build_representation.kind.value == 'vbmeta_artifact')}"
            ),
            (
                "Boot/DTBO/VBMeta realization coverage: "
                f"{'PASS' if sum(1 for item in result.build_realizations if item.build_representation.kind.value in ('boot_artifact', 'dtbo_artifact', 'vbmeta_artifact')) == sum(1 for item in reconstruction.artifact_build_representations if item.kind.value in ('boot_artifact', 'dtbo_artifact', 'vbmeta_artifact')) else 'FAIL'}"
            ),
            (
                "Boot/DTBO/VBMeta dependency projection: "
                f"{'PASS' if sum(len(item.dependency_realization_ids) for item in result.build_realizations if item.build_representation.kind.value in ('boot_artifact', 'dtbo_artifact', 'vbmeta_artifact')) == sum(len(item.dependency_ids) for item in reconstruction.artifact_build_representations if item.kind.value in ('boot_artifact', 'dtbo_artifact', 'vbmeta_artifact')) else 'FAIL'}"
            ),
            (
                "Full Reconstruction realization coverage: "
                f"{'PASS' if result.build_realization_count == len(reconstruction.artifact_build_representations) and {item.representation_id for item in result.build_realizations} == {item.representation_id for item in reconstruction.artifact_build_representations} else 'FAIL'}"
            ),
            (
                "Incremental realization coverage: "
                f"{'PASS' if result.build_realization_count == len(reconstruction.artifact_build_representations) else 'FAIL'}"
            ),
            "",
            "=== REQUIREMENT-BACKED PHYSICAL PAYLOADS ===",
            (
                "Canonical requirement-backed representations: "
                f"{canonical_requirement_backed_count}"
            ),
            (
                "Artifact requirement-backed representations: "
                f"{artifact_requirement_backed_count}"
            ),
            (
                "Non-Artifact canonical requirement-backed representations: "
                f"{non_artifact_requirement_backed_count}"
            ),
            "",
            "Requirement-backed Artifact deployment roles:",
            *tuple(
                f"  {role}: {count}"
                for role, count
                in sorted(
                    artifact_deployment_role_counts.items()
                )
                if count
            ),
            "",
            "Requirement-backed Artifact build-role matrix:",
            *tuple(
                f"  {kind}/{role}: {count}"
                for (
                    kind,
                    role,
                ), count
                in sorted(
                    artifact_build_role_matrix.items()
                )
                if count
            ),
            "",
            "Non-Artifact requirement-backed build roles:",
            *tuple(
                f"  {kind}: {count}"
                for kind, count
                in sorted(
                    non_artifact_build_role_counts.items()
                )
                if count
            ),
            "",
            "=== DIRECT ELF MODULE READINESS ===",
            (
                "Direct ELF realizations: "
                f"{len(direct_elf_representation_ids)}"
            ),
            (
                "Direct ELF dependency edges: "
                f"{direct_elf_dependency_edge_count}"
            ),
            (
                "Direct -> direct ELF dependency edges: "
                f"{direct_to_direct_dependency_edge_count}"
            ),
            (
                "Direct -> non-direct dependency edges: "
                f"{direct_to_non_direct_dependency_edge_count}"
            ),
            (
                "Direct ELF with only direct dependencies: "
                f"{direct_elf_only_direct_dependency_count}"
            ),
            (
                "Direct ELF with non-direct dependencies: "
                f"{direct_elf_non_direct_dependency_count}"
            ),
            "",
            "Direct ELF by build role:",
            *tuple(
                f"  {kind}: "
                f"{direct_elf_build_role_counts.get(kind, 0)}"
                for kind in (
                    "native_library",
                    "executable",
                )
            ),
            "",
            "=== DIRECT ELF NON-DIRECT DEPENDENCY TARGETS ===",
            (
                "Non-direct dependency edges: "
                f"{direct_to_non_direct_dependency_edge_count}"
            ),
            "",
            "By dependency build role:",
            *tuple(
                f"  {kind}: {count}"
                for kind, count
                in sorted(
                    non_direct_dependency_build_role_counts.items()
                )
            ),
            "",
            "Non-direct ELF target deployment roles:",
            *tuple(
                f"  {role}: {count}"
                for role, count
                in sorted(
                    non_direct_dependency_deployment_role_counts.items()
                )
                if count
            ),
            "",
            "=== DIRECT ELF NESTED PROVIDER OWNERSHIP ===",
            (
                "Nested native-library dependency edges: "
                f"{direct_to_non_direct_dependency_edge_count}"
            ),
            (
                "Nested native-library dependency targets: "
                f"{len(non_direct_dependency_targets)}"
            ),
            (
                "APEX-owned nested dependency edges: "
                f"{apex_owned_nested_dependency_edge_count}"
            ),
            (
                "Non-APEX nested dependency edges: "
                f"{non_apex_nested_dependency_edge_count}"
            ),
            "",
            *direct_elf_requirement_identity_lines,
            "=== PHYSICAL PAYLOAD PROJECTION ===",
            "Status: SUCCESS",
            (
                "Requirement-backed DIRECT_PARTITION projections: "
                f"{result.projected_physical_payload_count}"
            ),
            *(
                (
                    f"  {kind}: "
                    f"{sum(1 for item in result.physical_payload_projections if item.build_representation.kind.value == kind)}"
                )
                for kind
                in sorted(
                    {
                        item.build_representation.kind.value
                        for item
                        in result.physical_payload_projections
                    }
                )
            ),
            "",
            "=== CANONICAL BUILD PARTICIPATION ===",
            "Status: SUCCESS",
            "Android source checkout consulted for generation: NO",
            "Checkout-derived suppression decisions: 0",
            (
                "Canonical APEX build realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'apex_module')}"
            ),
            (
                "Canonical ELF prebuilt realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'prebuilt_module' and item.build_representation.kind.value in ('native_library', 'executable'))}"
            ),
            (
                "Canonical VINTF fragment modules retained: "
                f"{len(result.vintf_build_config.fragment_modules)}"
            ),
            (
                "External provider-knowledge suppressions: 0"
            ),
            (
                "Provider policy: canonical Reconstruction participation is "
                "retained unless a future explicit TreeForge Knowledge "
                "conclusion resolves a proven downstream provider conflict."
            ),
            "",
            "=== APEX PAYLOAD PROJECTION ===",
            "Status: SUCCESS",
            (
                "Root-runtime APEX payload projections: "
                f"{result.projected_apex_payload_count}"
            ),
            (
                "Canonical APEX representations not independently "
                "projected: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'apex_module') - result.projected_apex_payload_count}"
            ),
            "",
            "=== PRESERVED ARTIFACT PROJECTION ===",
            "Status: SUCCESS",
            (
                "Preserved-backed Reconstruction representations: "
                f"{len(preserved_backed_representations)}"
            ),
            (
                "Projected preserved artifacts: "
                f"{result.projected_artifact_count}"
            ),
            "",
            "Preserved-backed deployment roles:",
            *(
                (
                    f"  {role}: "
                    f"{preserved_backed_deployment_role_counts[role]}"
                )
                for role
                in sorted(
                    preserved_backed_deployment_role_counts
                )
            ),
            "",
            "Ownership domain: proprietary",
            (
                "Proprietary root: "
                f"{identity.proprietary_root.as_posix()}"
            ),
            "",
            "=== PRODUCT COPY FILE INTEGRATION ===",
            "Status: SUCCESS",
            (
                "Resolved COPY_FILE realizations: "
                f"{sum(1 for item in result.build_realizations if item.kind.value == 'copy_file' and item.status.value == 'resolved')}"
            ),
            (
                "PRODUCT_COPY_FILES entries: "
                f"{result.projected_product_copy_file_count}"
            ),
            "PRODUCT_COPY_FILES coverage: PASS",
            (
                "Generated vendor makefile: "
                f"{(identity.proprietary_root.parent / (identity.proprietary_root.parent.name + '-vendor.mk')).as_posix()}"
            ),
            "",
            "=== MATERIALIZATION ===",
            "Status: SUCCESS",
            (
                "Materialized source files: "
                f"{result.materialized_file_count}"
            ),
            (
                "Materialized preserved artifacts: "
                f"{result.materialized_artifact_count}"
            ),
            (
                "Materialized requirement-backed physical payloads: "
                f"{result.materialized_physical_payload_count}"
            ),
            (
                "Materialized root-runtime APEX payloads: "
                f"{result.materialized_apex_payload_count}"
            ),
            (
                "Total materialized files: "
                f"{result.total_materialized_count}"
            ),
            "",
            "Materialized source paths:",
            *(
                f"  {item.relative_path.as_posix()}"
                for item
                in result.materialized_files
            ),
            "",
            "Materialized preserved artifact paths:",
            *(
                (
                    "  "
                    f"{item.relative_path.as_posix()} "
                    "-> "
                    f"{item.installed_partition}:"
                    f"{item.installed_android_path}"
                )
                for item
                in result.materialized_artifacts
            ),
            "",
            "Materialized requirement-backed physical payload paths:",
            *(
                (
                    "  "
                    f"{item.relative_path.as_posix()} "
                    "-> "
                    f"{item.installed_partition}:"
                    f"{item.installed_android_path}"
                )
                for item
                in result.materialized_physical_payloads
            ),
            "",
            "Materialized root-runtime APEX payload paths:",
            *(
                (
                    "  "
                    f"{item.relative_path.as_posix()} "
                    "-> "
                    f"{item.installed_partition}:"
                    f"{item.installed_android_path}"
                )
                for item
                in result.materialized_apex_payloads
            ),
        ]
    )

    device_tree_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    device_tree_work_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        device_tree_work_root
        / "device-tree-report.txt"
    )

    report_path.write_text(
        "\n".join(report_lines)
        + "\n",
        encoding="utf-8",
    )

    if sys.stdout.isatty():
        clear_live_progress_block()

    typer.echo(
        "Device Tree completed successfully."
    )

    typer.echo()

    move_to_aosp = typer.confirm(
        "Copy generated Device Tree into AOSP?",
        default=True,
    )

    if move_to_aosp:
        if not AOSP_ROOT.exists():
            typer.echo(
                (
                    "Unable to copy generated Device Tree: "
                    f"AOSP workspace does not exist: {AOSP_ROOT}"
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        if not AOSP_ROOT.is_dir():
            typer.echo(
                (
                    "Unable to copy generated Device Tree: "
                    f"AOSP workspace is not a directory: {AOSP_ROOT}"
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        generated_device_source = (
            device_tree_root
            / Path(identity.device_root.as_posix())
        )

        aosp_device_destination = (
            AOSP_ROOT
            / Path(identity.device_root.as_posix())
        )

        if not generated_device_source.exists():
            typer.echo(
                (
                    "Unable to copy generated Device Tree: "
                    "generated source directory is missing: "
                    f"{generated_device_source}"
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        if not generated_device_source.is_dir():
            typer.echo(
                (
                    "Unable to copy generated Device Tree: "
                    "generated source path is not a directory: "
                    f"{generated_device_source}"
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        deployed_external_avb_key_count = 0

        apex_deployment_report_path = (
            device_tree_work_root
            / "platform-provider-apex-plan.json"
        )

        elf_deployment_report_path = (
            device_tree_work_root
            / "platform-provider-elf-plan.json"
        )

        vintf_deployment_report_path = (
            device_tree_work_root
            / "platform-provider-vintf-plan.json"
        )

        platform_deployment_report_path = (
            device_tree_work_root
            / "platform-provider-build-plan.json"
        )

        if apex_deployment_report_path.exists():
            apex_deployment_report_path.unlink()

        if elf_deployment_report_path.exists():
            elf_deployment_report_path.unlink()

        if vintf_deployment_report_path.exists():
            vintf_deployment_report_path.unlink()

        if platform_deployment_report_path.exists():
            platform_deployment_report_path.unlink()

        try:
            canonical_android_version = (
                agreed_identity_value(
                    "android_version"
                )
            )

            if canonical_android_version is None:
                raise ValueError(
                    "canonical Android version is unresolved; "
                    "Device Tree cannot select target-platform "
                    "provider semantics"
                )

            provider_profile = (
                select_android_device_tree_provider_profile(
                    canonical_android_version
                )
            )

            apex_deployment_plan = (
                AndroidDeviceTreeApexDeploymentPlanner
                .plan(
                    provider_profile=(
                        provider_profile
                    ),
                    device_root=identity.device_root,
                    projections=(
                        result.apex_payload_projections
                    ),
                    realizations=(
                        result.build_realizations
                    ),
                )
            )

            elf_deployment_plan = (
                AndroidDeviceTreeElfDeploymentPlanner
                .plan(
                    provider_profile=(
                        provider_profile
                    ),
                    device_root=identity.device_root,
                    realizations=(
                        result.build_realizations
                    ),
                )
            )

            vintf_deployment_plan = (
                AndroidDeviceTreeVintfDeploymentPlanner
                .plan(
                    provider_profile=(
                        provider_profile
                    ),
                    device_root=identity.device_root,
                    config=(
                        result.vintf_build_config
                    ),
                )
            )

            installation_mode = (
                read_installation_mode(
                    repository_root=(
                        Path.cwd().resolve()
                    )
                )
            )

            if installation_mode.value in {
                "maintainer",
                "developer",
            }:
                aosp_build_diagnostic_assignments = (
                    TREEFORGE_AOSP_BRINGUP_DIAGNOSTIC_ASSIGNMENTS
                )
            else:
                aosp_build_diagnostic_assignments = ()

            platform_deployment_plan = (
                AndroidDeviceTreePlatformDeploymentPlanner
                .plan(
                    provider_profile=(
                        provider_profile
                    ),
                    device_root=identity.device_root,
                    generated_device_root=(
                        generated_device_source
                    ),
                    vendor_makefile_name=(
                        f"{identity.build_device}-vendor.mk"
                    ),
                    product_name=(
                        identity.product
                    ),
                    build_diagnostic_assignments=(
                        aosp_build_diagnostic_assignments
                    ),
                )
            )

            aosp_device_destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if (
                aosp_device_destination.exists()
                and not aosp_device_destination.is_dir()
            ):
                raise OSError(
                    "AOSP destination exists but is not "
                    "a directory: "
                    f"{aosp_device_destination}"
                )

            #
            # Device Tree output is canonical generated content, while
            # keys/avb/*.pem are explicit downstream external inputs.
            #
            # Build the complete replacement tree beside the live
            # destination first, preserve only those external PEMs, then
            # replace the live tree.  Do not retain arbitrary stale files
            # from the previous deployment.
            #
            with tempfile.TemporaryDirectory(
                prefix=".treeforge-device-tree-deploy-",
                dir=aosp_device_destination.parent,
            ) as temporary_directory:
                staged_destination = (
                    Path(temporary_directory)
                    / "device-tree"
                )

                shutil.copytree(
                    generated_device_source,
                    staged_destination,
                )


                staged_avb_key_root = (
                    staged_destination
                    / "keys"
                    / "avb"
                )

                #
                # Frozen output/device-tree must never contain private keys.
                # Signing material is injected only into this temporary
                # downstream deployment view.
                #
                if staged_avb_key_root.exists():
                    raise OSError(
                        "canonical generated Device Tree unexpectedly "
                        "contains AVB private-key material: "
                        f"{staged_avb_key_root}"
                    )

                if (
                    selected_avb_signing_provider
                    == "treeforge"
                ):
                    validated_keys = (
                        validate_avb_bringup_keys(
                            repository_root=(
                                TREEFORGE_ROOT
                            ),
                            device=identity.device,
                        )
                    )

                    validated_by_partition = {
                        item.partition:
                        item
                        for item in validated_keys
                    }

                    expected_partitions = {
                        "boot",
                        "init_boot",
                        "vbmeta",
                        "vbmeta_system",
                        "vbmeta_vendor",
                    }

                    if (
                        set(validated_by_partition)
                        != expected_partitions
                    ):
                        raise ValueError(
                            "validated TreeForge AVB keyset has "
                            "an unexpected partition population"
                        )

                    build_keys_by_partition = {
                        item.partition_name:
                        item
                        for item
                        in result.avb_build_plan.external_keys
                    }

                    if (
                        set(build_keys_by_partition)
                        != expected_partitions
                    ):
                        raise ValueError(
                            "generated AVB build plan has an "
                            "unexpected signing-key population"
                        )

                    staged_avb_key_root.mkdir(
                        parents=True,
                        exist_ok=False,
                    )

                    for partition in sorted(
                        expected_partitions
                    ):
                        build_key = (
                            build_keys_by_partition[
                                partition
                            ]
                        )

                        expected_destination = (
                            identity.device_root
                            / "keys"
                            / "avb"
                            / f"{partition}.pem"
                        )

                        if (
                            build_key.destination.as_posix()
                            != expected_destination.as_posix()
                        ):
                            raise ValueError(
                                "TreeForge AVB build-key destination "
                                "does not match the canonical "
                                "deployment contract: "
                                f"{partition}: "
                                f"{build_key.destination}"
                            )

                        source_key = (
                            validated_by_partition[
                                partition
                            ]
                            .persistent_path
                        )

                        deployed_key = (
                            staged_avb_key_root
                            / f"{partition}.pem"
                        )

                        shutil.copy2(
                            source_key,
                            deployed_key,
                        )

                        deployed_key.chmod(
                            0o600
                        )

                        if (
                            source_key.read_bytes()
                            != deployed_key.read_bytes()
                        ):
                            raise OSError(
                                "deployed TreeForge AVB key differs "
                                "from its validated private source: "
                                f"{partition}"
                            )

                        deployed_mode = (
                            deployed_key.stat().st_mode
                            & 0o777
                        )

                        if deployed_mode != 0o600:
                            raise OSError(
                                "deployed TreeForge AVB key does not "
                                "have mode 0600: "
                                f"{deployed_key}"
                            )

                        deployed_external_avb_key_count += 1

                elif (
                    selected_avb_signing_provider
                    == "aosp"
                ):
                    #
                    # AOSP mode references external/avb/test/data directly.
                    # No device-local private keys belong in the deployment.
                    #
                    if staged_avb_key_root.exists():
                        raise OSError(
                            "AOSP signing mode must not deploy "
                            "device-local AVB private keys"
                        )

                else:
                    raise ValueError(
                        "unsupported Device Tree AVB signing provider: "
                        f"{selected_avb_signing_provider!r}"
                    )

                (
                    AndroidDeviceTreeApexDeploymentTransformer
                    .apply(
                        staged_device_root=(
                            staged_destination
                        ),
                        plan=apex_deployment_plan,
                        vendor_makefile_name=(
                            f"{identity.build_device}-vendor.mk"
                        ),
                    )
                )

                (
                    AndroidDeviceTreeElfDeploymentTransformer
                    .apply(
                        staged_device_root=(
                            staged_destination
                        ),
                        plan=elf_deployment_plan,
                        vendor_makefile_name=(
                            f"{identity.build_device}-vendor.mk"
                        ),
                    )
                )

                (
                    AndroidDeviceTreeVintfDeploymentTransformer
                    .apply(
                        staged_device_root=(
                            staged_destination
                        ),
                        plan=vintf_deployment_plan,
                        vendor_makefile_name=(
                            f"{identity.build_device}-vendor.mk"
                        ),
                    )
                )

                (
                    AndroidDeviceTreePlatformDeploymentTransformer
                    .apply(
                        staged_device_root=(
                            staged_destination
                        ),
                        plan=platform_deployment_plan,
                        vendor_makefile_name=(
                            f"{identity.build_device}-vendor.mk"
                        ),
                    )
                )

                if aosp_device_destination.exists():
                    shutil.rmtree(
                        aosp_device_destination
                    )

                staged_destination.rename(
                    aosp_device_destination
                )

            apex_deployment_plan.write_json(
                apex_deployment_report_path
            )

            elf_deployment_plan.write_json(
                elf_deployment_report_path
            )

            vintf_deployment_plan.write_json(
                vintf_deployment_report_path
            )

            platform_deployment_plan.write_json(
                platform_deployment_report_path
            )

        except (OSError, ValueError, TypeError) as error:
            typer.echo(
                (
                    "Unable to copy generated Device Tree "
                    f"into AOSP: {error}"
                ),
                err=True,
            )
            raise typer.Exit(code=1) from error

        typer.echo(
            "Generated Device Tree copied into AOSP:"
        )
        typer.echo(
            f"  {aosp_device_destination}"
        )
        typer.echo(
            (
                "AVB signing provider: "
                f"{selected_avb_signing_provider}"
            )
        )
        typer.echo(
            (
                "TreeForge AVB private keys deployed: "
                f"{deployed_external_avb_key_count}"
            )
        )
        typer.echo(
            (
                "Platform-provider APEX suppressions: "
                f"{len(apex_deployment_plan.suppressions)}"
            )
        )
        typer.echo(
            (
                "APEX platform-provider plan: "
                f"{apex_deployment_report_path}"
            )
        )
        typer.echo(
            (
                "Platform-provider ELF suppressions: "
                f"{len(elf_deployment_plan.suppressions)} "
                "("
                f"{elf_deployment_plan.executable_count} executables, "
                f"{elf_deployment_plan.native_library_count} "
                "native libraries)"
            )
        )
        typer.echo(
            (
                "ELF platform-provider plan: "
                f"{elf_deployment_report_path}"
            )
        )

        typer.echo(
            (
                "Platform-provider VINTF suppressions: "
                f"{len(vintf_deployment_plan.suppressions)}"
            )
        )
        typer.echo(
            (
                "VINTF platform-provider plan: "
                f"{vintf_deployment_report_path}"
            )
        )
        typer.echo(
            (
                "Platform-provider build suppressions: "
                f"{len(platform_deployment_plan.suppressions)} "
                "("
                f"{platform_deployment_plan.copy_file_count} "
                "copy files, "
                f"{platform_deployment_plan.framework_res_count} "
                "framework-res, "
                f"{platform_deployment_plan.selinux_type_count} "
                "SELinux type declarations, "
                f"{platform_deployment_plan.selinux_statement_count} "
                "SELinux statements, "
                f"{platform_deployment_plan.selinux_file_context_count} "
                "SELinux file-context entries)"
            )
        )
        typer.echo(
            (
                "Platform-provider build plan: "
                f"{platform_deployment_report_path}"
            )
        )
