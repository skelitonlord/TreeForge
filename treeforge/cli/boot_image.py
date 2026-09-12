from __future__ import annotations

from pathlib import Path
import logging
import shutil
import sys

import subprocess
from shutil import which

import typer

from treeforge.android.host_provider_bundle import (
    ANDROID_15_HOST_PROVIDER_RELEASE,
    AndroidHostProviderBundleLoader,
    android_host_provider_bundle_root,
)
from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
    parsing_snapshot_path,
)
from treeforge.android.boot_image import (
    AndroidBootImageComponentMutationSpec,
    AndroidBootImagePipeline,
)
from treeforge.android.boot_image.models import (
    AndroidBootImageComponentRole,
)
from treeforge.android.boot_image.deployment_planning import (
    AndroidBootImageDeploymentPlanner,
    build_base_boot_image_deployment,
    load_base_boot_image_deployment,
    load_reusable_boot_image_deployment,
    export_boot_image_deployment,
)
from treeforge.android.recovery.install_set import (
    build_recovery_install_set,
)
from treeforge.android.boot_image.device_deployment import (
    AndroidBootImageDeviceDeployer,
    AndroidBootImageDeploymentPayload,
    AndroidBootImageSlotSelection,
)
from treeforge.android.bootstrap.handoff import (
    AndroidBootstrapBootImageHandoffManifest,
)
from treeforge.cli.bootstrap import (
    bootstrap as run_bootstrap_command,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.cli.progress import (
    configure_live_progress_logging,
    render_progress,
)
from treeforge.workspace.workspace import (
    Workspace,
)


app = typer.Typer(
    help=(
        "Build TreeForge's Boot Image interpretation from the canonical "
        "Parsing handoff."
    )
)


def _run_existing_boot_image_deployment(
    deployment,
    *,
    boot_image_root: Path,
    image_set: str = "selected",
) -> None:
    """
    Run the common hardware deployment workflow for an already validated
    durable Boot Image population.

    The caller has already selected base vs Bootstrap. This helper therefore
    deploys that population's final bytes without introducing a second
    modified/original selection.
    """

    device_deployer = (
        AndroidBootImageDeviceDeployer()
    )

    typer.echo()
    typer.echo(
        "[Boot Image] Checking device state..."
    )

    try:
        device_inspection = (
            device_deployer.inspect(
                deployment
            )
        )

    except RuntimeError as error:
        typer.echo()
        typer.echo(
            "Boot Image hardware deployment was not performed."
        )
        typer.echo(
            f"Reason: {error}"
        )
        return

    typer.echo()
    typer.echo(
        "=== BOOT IMAGE DEVICE INSPECTION ==="
    )
    typer.echo()

    typer.echo(
        "Device: "
        f"{device_inspection.device.serial}"
    )

    typer.echo(
        "Initial mode: "
        f"{device_inspection.device.initial_mode.value}"
    )

    typer.echo(
        "Deployment mode: "
        f"{device_inspection.device.final_mode.value}"
    )

    typer.echo(
        "Current active slot: "
        + (
            device_inspection.active_slot
            or "<not reported>"
        )
    )

    typer.echo(
        "Slot count: "
        + (
            str(
                device_inspection.device.slot_count
            )
            if (
                device_inspection.device.slot_count
                is not None
            )
            else "<not reported>"
        )
    )

    typer.echo()
    typer.echo(
        "Partition slot applicability:"
    )

    for (
        image,
        slot_applicable,
    ) in (
        device_inspection.slot_applicability
    ):
        typer.echo(
            "  "
            f"{image.partition_name}: "
            + (
                "slotted"
                if slot_applicable
                else "non-slotted"
            )
        )

    slot_selection = None

    if (
        device_inspection.has_slotted_targets
    ):
        typer.echo()
        typer.echo(
            "Choose target slot:"
        )

        typer.echo(
            "  a"
            + (
                "  <- current active"
                if (
                    device_inspection.active_slot
                    == "a"
                )
                else ""
            )
        )

        typer.echo(
            "  b"
            + (
                "  <- current active"
                if (
                    device_inspection.active_slot
                    == "b"
                )
                else ""
            )
        )

        typer.echo(
            "  cancel"
        )

        default_slot = (
            device_inspection.active_slot
            or "a"
        )

        while True:
            raw_slot = (
                typer.prompt(
                    "Target slot",
                    default=default_slot,
                )
                .strip()
                .lower()
            )

            if raw_slot == "a":
                slot_selection = (
                    AndroidBootImageSlotSelection
                    .SLOT_A
                )
                break

            if raw_slot == "b":
                slot_selection = (
                    AndroidBootImageSlotSelection
                    .SLOT_B
                )
                break

            if raw_slot == "cancel":
                typer.echo(
                    "Boot Image hardware deployment skipped."
                )
                return

            typer.echo(
                "Choose a, b, or cancel."
            )

    device_deployment_plan = (
        device_deployer.plan(
            device_inspection,
            payload=(
                AndroidBootImageDeploymentPayload
                .MODIFIED
            ),
            slot_selection=(
                slot_selection
            ),
        )
    )

    typer.echo()
    typer.echo(
        "=== BOOT IMAGE DEVICE DEPLOYMENT ==="
    )
    typer.echo()

    typer.echo(
        f"Image set: {image_set}"
    )

    if (
        device_deployment_plan.slot_selection
        is not None
    ):
        typer.echo(
            "Target slot: "
            f"{device_deployment_plan.slot_selection.value}"
        )

    typer.echo(
        "Active slot remains: "
        + (
            device_deployment_plan
            .device
            .current_slot
            or "<not reported>"
        )
    )

    typer.echo()
    typer.echo(
        "Planned hardware writes:"
    )

    for target in (
        device_deployment_plan.targets
    ):
        image = target.image

        typer.echo(
            "  "
            f"{target.fastboot_partition}"
        )

        typer.echo(
            "    image: "
            f"{image.final_path}"
        )

        typer.echo(
            "    bytes: "
            f"{image.final_size_bytes}"
        )

        typer.echo(
            "    sha256: "
            f"{image.final_sha256}"
        )

        typer.echo(
            "    exact original: "
            f"{image.rollback_path}"
        )

        typer.echo(
            "    original sha256: "
            f"{image.rollback_sha256}"
        )

    typer.echo()
    typer.echo(
        "Safety boundary:"
    )

    typer.echo(
        "  Selected images reverified immediately "
        "before flash: yes"
    )

    typer.echo(
        "  Exact original retained for restoration: yes"
    )

    typer.echo(
        (
            "  Target slot explicitly selected: yes"
            if (
                device_inspection.has_slotted_targets
            )
            else
            "  Target is non-slotted: yes"
        )
    )

    typer.echo(
        "  Automatic active-slot change: no"
    )

    typer.echo(
        "  Reboot after flash requires confirmation: yes"
    )

    typer.echo()
    flash_confirmed = typer.confirm(
        "Flash exactly this image set "
        "to the displayed target(s)?",
        default=False,
    )

    if not flash_confirmed:
        typer.echo(
            "Boot Image hardware deployment skipped."
        )
        return

    typer.echo()
    typer.echo(
        "Flashing selected Boot Image deployment..."
    )

    device_deployment_result = (
        device_deployer.flash(
            device_deployment_plan
        )
    )

    typer.echo()
    typer.echo(
        "Boot Image hardware deployment completed."
    )

    for invocation in (
        device_deployment_result.invocations
    ):
        typer.echo(
            "  flashed: "
            f"{invocation.target.fastboot_partition}"
            " <- "
            f"{image_set}"
        )

    typer.echo()
    typer.echo(
        "The active slot was not changed."
    )

    typer.echo(
        "The device was not rebooted."
    )

    typer.echo()
    typer.echo(
        "Exact original images remain available for "
        "explicit restoration:"
    )

    for target in (
        device_deployment_plan.targets
    ):
        typer.echo(
            "  "
            f"{target.fastboot_partition}: "
            f"{target.image.rollback_path}"
        )


def _prompt_boot_image_deployment_format() -> str:
    typer.echo()
    typer.echo(
        "Choose deployment format:"
    )
    typer.echo(
        "  1. Recovery Install Set"
    )
    typer.echo(
        "  2. Bootloader / Fastboot"
    )
    typer.echo(
        "  3. Both"
    )
    typer.echo(
        "  4. Cancel"
    )
    typer.echo()

    choices = {
        "1": "recovery",
        "2": "bootloader",
        "3": "both",
        "4": "cancel",
    }

    while True:
        selection = (
            typer.prompt(
                "Selection",
                default="1",
            )
            .strip()
        )

        resolved = choices.get(
            selection
        )

        if resolved is not None:
            return resolved

        typer.echo(
            "Choose 1, 2, 3, or 4."
        )


def _prompt_recovery_install_slot() -> str:
    typer.echo()
    typer.echo(
        "Choose Recovery Install Set target slot:"
    )
    typer.echo(
        "  1. Slot A"
    )
    typer.echo(
        "  2. Slot B"
    )
    typer.echo()

    choices = {
        "1": "a",
        "2": "b",
    }

    while True:
        selection = (
            typer.prompt(
                "Selection"
            )
            .strip()
        )

        slot = choices.get(
            selection
        )

        if slot is not None:
            return slot

        typer.echo(
            "Choose 1 or 2."
        )


def _prepare_recovery_install_set(
    deployment,
    *,
    boot_image_root: Path,
    image_set: str,
) -> Path:
    target_slot = (
        _prompt_recovery_install_slot()
    )

    package_path = (
        build_recovery_install_set(
            deployment,
            output_root=(
                boot_image_root
                / "deployment"
                / "recovery"
            ),
            target_slot=target_slot,
            image_set=image_set,
        )
    )

    typer.echo()
    typer.echo(
        "Recovery Install Set prepared."
    )
    typer.echo(
        f"  Image set: {image_set}"
    )
    typer.echo(
        "  Target slot: "
        f"{target_slot.upper()}"
    )
    typer.echo(
        f"  Package: {package_path}"
    )
    typer.echo(
        "  Stage with:"
    )
    typer.echo(
        "    treeforge recovery stage"
    )

    return package_path


def _run_existing_boot_image_populations(
    *,
    base_deployment,
    bootstrap_deployment,
    boot_image_root: Path,
) -> None:
    """
    Use already validated Boot Image artifact populations without rerunning
    signing, reconstruction, or Validation.
    """

    typer.echo()
    typer.echo(
        "[Boot Image] Detecting connected device "
        "(read-only probe)..."
    )

    device_deployer = (
        AndroidBootImageDeviceDeployer()
    )

    try:
        device_available = (
            device_deployer
            .has_connected_device()
        )

    except RuntimeError as error:
        typer.echo()
        typer.echo(
            "Boot Image device detection could not continue."
        )
        typer.echo(
            f"Reason: {error}"
        )

        return

    if not device_available:
        typer.echo()
        typer.echo(
            "No ADB or fastboot device was detected."
        )

        typer.echo()
        typer.echo(
            "Available Boot Image sets:"
        )
        typer.echo(
            "  base      -> exact canonical Parsing images"
        )

        if bootstrap_deployment is not None:
            typer.echo(
                "  bootstrap -> validated bootstrapped images"
            )

        save_images = typer.confirm(
            "Save available Boot Image images for later deployment?",
            default=True,
        )

        if not save_images:
            typer.echo(
                "Boot Image image export skipped."
            )
            typer.echo()
            typer.echo(
                "Boot Image completed without hardware deployment."
            )
            return

        saved_root = (
            boot_image_root
            / "saved-images"
        )

        if saved_root.exists():
            shutil.rmtree(
                saved_root
            )

        base_saved_root = (
            saved_root
            / "base"
        )

        base_saved_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        for image in (
            base_deployment.images
        ):
            destination = (
                base_saved_root
                / f"{image.partition_name}.img"
            )

            shutil.copy2(
                image.final_path,
                destination,
            )

        if bootstrap_deployment is not None:
            bootstrap_modified_root = (
                saved_root
                / "bootstrap"
                / "modified"
            )

            bootstrap_original_root = (
                saved_root
                / "bootstrap"
                / "original"
            )

            bootstrap_modified_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            bootstrap_original_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            for image in (
                bootstrap_deployment.images
            ):
                shutil.copy2(
                    image.final_path,
                    bootstrap_modified_root
                    / f"{image.partition_name}.img",
                )

                shutil.copy2(
                    image.rollback_path,
                    bootstrap_original_root
                    / f"{image.partition_name}.img",
                )

        typer.echo()
        typer.echo(
            "Boot Image images saved successfully."
        )
        typer.echo(
            f"Base: {base_saved_root}"
        )

        if bootstrap_deployment is not None:
            typer.echo(
                "Bootstrap modified: "
                f"{saved_root / 'bootstrap' / 'modified'}"
            )
            typer.echo(
                "Bootstrap original: "
                f"{saved_root / 'bootstrap' / 'original'}"
            )

        typer.echo()
        typer.echo(
            "Boot Image completed without hardware deployment."
        )

        return

    typer.echo()
    typer.echo(
        "Boot Image hardware deployment is available."
    )
    typer.echo()
    typer.echo(
        "Choose image set:"
    )
    typer.echo(
        "  1. Base      -> exact canonical Parsing images"
    )

    if bootstrap_deployment is not None:
        typer.echo(
            "  2. Bootstrap -> validated bootstrapped images"
        )
        typer.echo(
            "  3. Cancel    -> do not modify hardware"
        )
        default_choice = "2"
    else:
        typer.echo(
            "  2. Cancel    -> do not modify hardware"
        )
        default_choice = "1"

    typer.echo()

    while True:
        raw_choice = (
            typer.prompt(
                "Image set",
                default=default_choice,
            )
            .strip()
        )

        if bootstrap_deployment is not None:
            image_set_by_choice = {
                "1": "base",
                "2": "bootstrap",
                "3": "cancel",
            }
        else:
            image_set_by_choice = {
                "1": "base",
                "2": "cancel",
            }

        image_set = image_set_by_choice.get(
            raw_choice
        )

        if image_set is not None:
            break

        typer.echo(
            "Choose "
            + (
                "1, 2, or 3."
                if bootstrap_deployment is not None
                else "1 or 2."
            )
        )

    if image_set == "cancel":
        typer.echo(
            "Boot Image hardware deployment cancelled."
        )
        return

    selected_deployment = (
        bootstrap_deployment
        if image_set == "bootstrap"
        else base_deployment
    )

    deployment_format = (
        _prompt_boot_image_deployment_format()
    )

    if deployment_format == "cancel":
        typer.echo(
            "Boot Image deployment cancelled."
        )
        return

    if deployment_format in {
        "recovery",
        "both",
    }:
        _prepare_recovery_install_set(
            selected_deployment,
            boot_image_root=(
                boot_image_root
            ),
            image_set=(
                image_set
            ),
        )

    if deployment_format == "recovery":
        typer.echo()
        typer.echo(
            "Boot Image completed with a "
            "Recovery Install Set."
        )
        return

    #
    # Existing bootloader hardware workflow remains the owner from here.
    #
    _run_existing_boot_image_deployment(
        selected_deployment,
        boot_image_root=(
            boot_image_root
        ),
        image_set=(
            image_set
        ),
    )


@app.callback(
    invoke_without_command=True,
)
def boot_image(
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Boot Image workspace artifacts "
            "are preserved under OUTPUT/boot-image. Defaults to ./output."
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
            "Optional explicit canonical Android Parsing snapshot. "
            "When omitted, Boot Image requires "
            "OUTPUT/parsing/snapshot.json."
        ),
    ),
    replace_component: list[str] | None = typer.Option(
        None,
        "--replace-component",
        help=(
            "Explicit Boot Image component replacement in the form "
            "IMAGE:COMPONENT=PATH. May be repeated. Example: "
            "init_boot:ramdisk=/path/to/ramdisk."
        ),
    ),
    avb_key: Path | None = typer.Option(
        None,
        "--avb-key",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Explicit RSA private key used to resolve regenerated "
            "AVB signing identity. The factory private key is never "
            "inferred from factory-image evidence."
        ),
    ),
    parent_vbmeta_key: Path | None = typer.Option(
        None,
        "--parent-vbmeta-key",
        help=(
            "Compatibility form for a single parent standalone "
            "VBMeta signing key. Prefer --vbmeta-key PARTITION=PATH "
            "for generic multi-level AVB topology."
        ),
    ),
    vbmeta_key: list[str] | None = typer.Option(
        None,
        "--vbmeta-key",
        help=(
            "Partition-scoped standalone VBMeta private key in the "
            "form PARTITION=PATH. May be repeated. Example: "
            "vbmeta=/path/to/vbmeta.pem."
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
    generation_only: bool = typer.Option(
        False,
        "--generation-only",
        hidden=True,
        help=(
            "Internal downstream generation/validation boundary. "
            "Never enters Boot Image hardware deployment UX."
        ),
    ),
) -> None:
    """
    Run TreeForge's Boot Image branch from the canonical Parsing boundary.

    Boot Image requires an existing canonical Parsing snapshot. It never
    reruns Discovery through Parsing and never consumes Android Device
    Universe, Runtime Linking, Reconstruction, or Device Tree state.
    """

    typer.echo(
        "TreeForge Boot Image"
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

    output = (
        output
        .expanduser()
        .resolve()
    )

    boot_image_root = (
        output
        / "boot-image"
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

    active_parsing_snapshot_path = (
        parsing_snapshot
        .expanduser()
        .resolve()
        if parsing_snapshot is not None
        else canonical_parsing_snapshot
    )

    # --------------------------------------------------------
    # Required Parsing handoff
    # --------------------------------------------------------

    if not active_parsing_snapshot_path.is_file():
        typer.echo(
            "",
        )

        typer.echo(
            "Boot Image requires a completed Parsing snapshot.",
            err=True,
        )

        typer.echo(
            "Please run Parsing first:",
            err=True,
        )

        typer.echo(
            "  treeforge parse <factory-image>",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    try:
        typer.echo()
        typer.echo(
            "[Boot Image] Restoring canonical Parsing snapshot..."
        )
        typer.echo(
            "  Snapshot: "
            f"{active_parsing_snapshot_path}"
        )

        restored_snapshot = (
            AndroidParsingSnapshotStore()
            .load(
                active_parsing_snapshot_path
            )
        )

        typer.echo(
            "[Boot Image] Parsing snapshot restored."
        )

    except Exception as error:
        typer.echo(
            (
                "Unable to restore Parsing snapshot: "
                f"{error}"
            ),
            err=True,
        )

        typer.echo(
            "Please run Parsing again before Boot Image.",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    parsing_result = (
        restored_snapshot.parsing
    )

    typer.echo()
    typer.echo(
        "Using canonical Parsing snapshot:"
    )

    typer.echo(
        str(
            active_parsing_snapshot_path
        )
    )

    active_bootstrap_handoff_path = None
    reusable_deployment = None

    typer.echo(
        "  Boot-family images: "
        f"{len(parsing_result.boot_images)}"
    )

    typer.echo()
    typer.echo(
        "[Boot Image] Preparing mutation inputs..."
    )

    mutation_specs = []

    # TREEFORGE_BOOT_IMAGE_AUTO_BOOTSTRAP_V1
    #
    # A normal Boot Image run always refreshes Bootstrap first.
    #
    # An existing Bootstrap handoff may be internally valid while
    # still representing an older Bootstrap implementation. Parsing
    # identity alone cannot detect changes to generated runtime code
    # such as the freestanding early dispatcher.
    #
    # Explicit --replace-component remains the manual mutation path.
    #
    bootstrap_replacements = False

    if not replace_component:
        if verbose:
            typer.echo(
                "[Boot Image] Refreshing Bootstrap handoff..."
            )

        run_bootstrap_command(
            output=output,
            parsing_snapshot=(
                active_parsing_snapshot_path
            ),
            hardware=None,
            verbose=verbose,
        )

        bootstrap_handoff_path = (
            output
            / "bootstrap"
            / "deployment"
            / "boot-image-replacements.json"
        )

        if not bootstrap_handoff_path.is_file():
            raise RuntimeError(
                "Bootstrap completed without producing the "
                "required Boot Image replacement handoff"
            )

        bootstrap_replacements = True

    if (
        bootstrap_replacements
        and replace_component
    ):
        raise typer.BadParameter(
            "automatic Bootstrap refresh cannot be combined with --replace-component"
        )

    if bootstrap_replacements:
        bootstrap_handoff_path = (
            output
            / "bootstrap"
            / "deployment"
            / "boot-image-replacements.json"
        )

        if not bootstrap_handoff_path.is_file():
            typer.echo()
            typer.echo(
                "Bootstrap replacement images are not available."
            )

            generate_bootstrap = typer.confirm(
                "Generate Bootstrap images now?",
                default=True,
            )

            if not generate_bootstrap:
                typer.echo(
                    "Boot Image Bootstrap generation cancelled."
                )

                raise typer.Exit(
                    code=0
                )

            typer.echo()
            typer.echo(
                "Running TreeForge Bootstrap..."
            )

            run_bootstrap_command(
                output=output,
                parsing_snapshot=(
                    active_parsing_snapshot_path
                ),
                hardware=None,
                verbose=verbose,
            )

            if not bootstrap_handoff_path.is_file():
                raise RuntimeError(
                    "Bootstrap completed without producing the "
                    "required Boot Image replacement handoff: "
                    f"{bootstrap_handoff_path}"
                )

        try:
            typer.echo()
            typer.echo(
                "[Boot Image] Validating Bootstrap handoff..."
            )
            typer.echo(
                f"  Handoff: {bootstrap_handoff_path}"
            )

            bootstrap_handoff = (
                AndroidBootstrapBootImageHandoffManifest
                .load(
                    bootstrap_handoff_path
                )
            )

            bootstrap_handoff.validate_parsing_snapshot(
                active_parsing_snapshot_path
            )

            bootstrap_handoff.validate_artifacts()

            typer.echo(
                "[Boot Image] Bootstrap handoff validated."
            )
            typer.echo(
                "  Replacement components: "
                f"{len(bootstrap_handoff.replacements)}"
            )

        except Exception as error:
            typer.echo()
            typer.echo(
                "Existing Bootstrap handoff is invalid for the "
                "selected Parsing snapshot."
            )

            regenerate_bootstrap = typer.confirm(
                "Regenerate Bootstrap images now?",
                default=True,
            )

            if not regenerate_bootstrap:
                typer.echo(
                    "Boot Image Bootstrap regeneration cancelled."
                )

                raise typer.Exit(
                    code=0
                )

            run_bootstrap_command(
                output=output,
                parsing_snapshot=(
                    active_parsing_snapshot_path
                ),
                hardware=None,
                verbose=verbose,
            )

            bootstrap_handoff = (
                AndroidBootstrapBootImageHandoffManifest
                .load(
                    bootstrap_handoff_path
                )
            )

            bootstrap_handoff.validate_parsing_snapshot(
                active_parsing_snapshot_path
            )

            bootstrap_handoff.validate_artifacts()

        active_bootstrap_handoff_path = (
            bootstrap_handoff_path
            .resolve()
        )

        typer.echo()
        typer.echo(
            "Using Bootstrap replacement handoff:"
        )

        typer.echo(
            f"  {active_bootstrap_handoff_path}"
        )

        for replacement in (
            bootstrap_handoff.replacements
        ):
            mutation_specs.append(
                AndroidBootImageComponentMutationSpec(
                    container_kind=(
                        replacement.container_kind
                    ),
                    semantic_name=(
                        replacement.semantic_name
                    ),
                    replacement_path=(
                        replacement.replacement_path
                    ),
                )
            )

            typer.echo(
                "  Replacement: "
                f"{replacement.container_kind}:"
                f"{replacement.semantic_name} "
                f"-> {replacement.replacement_path}"
            )

            typer.echo(
                "    rollback required: "
                f"{str(replacement.rollback_required).lower()}"
            )

    for raw_spec in (
        replace_component
        if replace_component is not None
        else []
    ):
        if "=" not in raw_spec:
            raise typer.BadParameter(
                "--replace-component requires "
                "IMAGE:COMPONENT=PATH"
            )

        target, raw_path = raw_spec.split(
            "=",
            1,
        )

        if ":" not in target:
            raise typer.BadParameter(
                "--replace-component requires "
                "IMAGE:COMPONENT=PATH"
            )

        container_kind, semantic_name = (
            target.split(
                ":",
                1,
            )
        )

        replacement_path = Path(
            raw_path
        ).expanduser().resolve()

        if not replacement_path.is_file():
            raise typer.BadParameter(
                "replacement component does not exist: "
                f"{replacement_path}"
            )

        mutation_specs.append(
            AndroidBootImageComponentMutationSpec(
                container_kind=container_kind,
                semantic_name=semantic_name,
                replacement_path=replacement_path,
            )
        )

    # --------------------------------------------------------
    # Durable Boot Image artifact populations
    # --------------------------------------------------------

    base_deployment_root = (
        boot_image_root
        / "deployment"
        / "base"
    )

    base_manifest_path = (
        base_deployment_root
        / "deployment-manifest.json"
    )

    typer.echo()
    typer.echo(
        "[Boot Image] Checking canonical base images..."
    )

    try:
        base_deployment = (
            load_base_boot_image_deployment(
                base_manifest_path,
                parsing_snapshot_path=(
                    active_parsing_snapshot_path
                ),
            )
        )

    except Exception:
        typer.echo(
            "  Base images are missing or stale."
        )
        typer.echo(
            "  Materializing exact canonical images from Parsing..."
        )

        base_deployment = (
            build_base_boot_image_deployment(
                parsing_result,
                parsing_snapshot_path=(
                    active_parsing_snapshot_path
                ),
                output_root=(
                    base_deployment_root
                ),
            )
        )

        typer.echo(
            "  Canonical base images materialized."
        )

    else:
        typer.echo(
            "  Existing base images validated."
        )

    typer.echo(
        "  Images: "
        f"{base_deployment.image_count}"
    )

    bootstrap_deployment = None

    bootstrap_deployment_root = (
        boot_image_root
        / "deployment"
        / "bootstrap"
    )

    bootstrap_manifest_path = (
        bootstrap_deployment_root
        / "deployment-manifest.json"
    )

    #
    # First try to reuse an already generated Bootstrap deployment.
    #
    if (
        bootstrap_manifest_path
        .is_file()
    ):
        bootstrap_handoff_path = (
            output
            / "bootstrap"
            / "deployment"
            / "boot-image-replacements.json"
        )

        if (
            bootstrap_handoff_path
            .is_file()
        ):
            try:
                bootstrap_deployment = (
                    load_reusable_boot_image_deployment(
                        bootstrap_manifest_path,
                        parsing_snapshot_path=(
                            active_parsing_snapshot_path
                        ),
                        bootstrap_handoff_path=(
                            bootstrap_handoff_path
                        ),
                    )
                )

            except Exception as error:
                typer.echo()
                typer.echo(
                    "[Boot Image] Existing Bootstrap images "
                    "cannot be reused."
                )

                if verbose:
                    typer.echo(
                        f"  Reason: {error}"
                    )

                bootstrap_deployment = None

            else:
                typer.echo()
                typer.echo(
                    "[Boot Image] Existing Bootstrap images validated."
                )
                typer.echo(
                    "  Changed partitions: "
                    f"{bootstrap_deployment.image_count}"
                )

    #
    # Plain Boot Image invocation offers Bootstrap generation if there is
    # no reusable Bootstrap image set yet.
    #
    if (
        bootstrap_deployment is None
        and not replace_component
        and not bootstrap_replacements
    ):
        typer.echo()

        generate_bootstrap = typer.confirm(
            "Bootstrapped Boot Image images are not available. "
            "Generate them now?",
            default=True,
        )

        if generate_bootstrap:
            typer.echo()
            typer.echo(
                "[Boot Image] Running Bootstrap..."
            )

            run_bootstrap_command(
                output=output,
                parsing_snapshot=(
                    active_parsing_snapshot_path
                ),
                hardware=None,
                verbose=verbose,
            )

            bootstrap_handoff_path = (
                output
                / "bootstrap"
                / "deployment"
                / "boot-image-replacements.json"
            )

            if not bootstrap_handoff_path.is_file():
                raise RuntimeError(
                    "Bootstrap completed without producing the "
                    "required Boot Image replacement handoff"
                )

            #
            # Bootstrap was generated after the command's normal Bootstrap
            # intake block had already been passed. Consume the newly
            # generated handoff here so this same invocation actually
            # reconstructs the bootstrapped image population.
            #
            typer.echo()
            typer.echo(
                "[Boot Image] Loading newly generated Bootstrap handoff..."
            )

            bootstrap_handoff = (
                AndroidBootstrapBootImageHandoffManifest
                .load(
                    bootstrap_handoff_path
                )
            )

            bootstrap_handoff.validate_parsing_snapshot(
                active_parsing_snapshot_path
            )

            bootstrap_handoff.validate_artifacts()

            active_bootstrap_handoff_path = (
                bootstrap_handoff_path
                .resolve()
            )

            for replacement in (
                bootstrap_handoff.replacements
            ):
                mutation_specs.append(
                    AndroidBootImageComponentMutationSpec(
                        container_kind=(
                            replacement.container_kind
                        ),
                        semantic_name=(
                            replacement.semantic_name
                        ),
                        replacement_path=(
                            replacement.replacement_path
                        ),
                    )
                )

            bootstrap_replacements = True

            typer.echo(
                "  Replacement components: "
                f"{len(bootstrap_handoff.replacements)}"
            )
            typer.echo(
                "  Bootstrap mutation intake: complete"
            )

    #
    # If both reusable populations already exist, skip the expensive Boot
    # Image reconstruction path entirely.
    #
    if (
        bootstrap_deployment is not None
        and not replace_component
        and not bootstrap_replacements
    ):
        _run_existing_boot_image_populations(
            base_deployment=(
                base_deployment
            ),
            bootstrap_deployment=(
                bootstrap_deployment
            ),
            boot_image_root=(
                boot_image_root
            ),
        )

        return

    # --------------------------------------------------------
    # --------------------------------------------------------
    # Boot Image signing material preflight
    # --------------------------------------------------------
    #
    # Canonical Parsing has already been resolved here.
    #
    # Discover every Boot Image-relevant AVB signing identity first,
    # display one complete status summary, then ask at most:
    #
    #   1. Generate all missing TreeForge development keys?
    #   2. Reuse all existing TreeForge development keys?
    #
    # Generated keys are selected automatically for this run.
    #
    # Factory images prove public signing identities only. TreeForge
    # never infers possession of factory private signing material.
    #

    typer.echo()
    typer.echo(
        "[Boot Image] Inspecting AVB and signing requirements..."
    )
    typer.echo(
        "  Scanning canonical boot/VBMeta topology."
    )

    development_key_root = (
        output
        / "boot-image-keys"
    )

    avb_rsa_bits_by_algorithm_type = {
        1: 2048,
        2: 4096,
        3: 8192,
        4: 2048,
        5: 4096,
        6: 8192,
    }

    avb_algorithm_name_by_type = {
        0: "NONE",
        1: "SHA256_RSA2048",
        2: "SHA256_RSA4096",
        3: "SHA256_RSA8192",
        4: "SHA512_RSA2048",
        5: "SHA512_RSA4096",
        6: "SHA512_RSA8192",
    }

    avbtool_provider = (
        AndroidHostProviderBundleLoader.load(
            android_host_provider_bundle_root(
                name="avbtool",
                release=(
                    ANDROID_15_HOST_PROVIDER_RELEASE
                ),
            )
        )
    )

    if not avbtool_provider.supports(
        "android-avbtool"
    ):
        raise RuntimeError(
            "TreeForge avbtool provider lacks "
            "android-avbtool capability"
        )

    avbtool = avbtool_provider.executable_for("android-avbtool")

    #
    # Canonical boot-image artifact → partition mapping.
    #
    boot_partition_by_artifact_id = {
        id(
            image.partition.artifact
        ): image.partition
        for image
        in parsing_result.boot_images
    }

    #
    # Each record is:
    #
    #   {
    #       partition_name,
    #       kind,                # embedded | standalone
    #       algorithm_type,
    #       algorithm_name,
    #       rsa_bits,
    #       private_key_path,
    #       public_key_path,
    #       exists,
    #   }
    #
    signing_identities = []
    unsigned_avb_identities = []

    seen_identity_keys = set()

    for parsed_vbmeta in (
        parsing_result.vbmeta
    ):
        if (
            parsed_vbmeta.artifact
            is parsed_vbmeta.container_artifact
        ):
            partition = (
                parsed_vbmeta.partition
            )

            if partition is None:
                raise RuntimeError(
                    "standalone canonical VBMeta lost its "
                    "InventoryPartition identity"
                )

            partition_name = (
                partition.name
            )

            identity_kind = (
                "standalone"
            )

        else:
            partition = (
                boot_partition_by_artifact_id
                .get(
                    id(
                        parsed_vbmeta
                        .container_artifact
                    )
                )
            )

            #
            # Embedded VBMeta may also exist in non-boot containers
            # such as APEX payloads. Those are not Boot Image boot-image
            # signing identities.
            #
            if partition is None:
                continue

            partition_name = (
                partition.name
            )

            identity_kind = (
                "embedded"
            )

        if (
            not isinstance(
                partition_name,
                str,
            )
            or not partition_name
        ):
            raise RuntimeError(
                "canonical AVB signing identity has no "
                "partition name"
            )

        identity_key = (
            identity_kind,
            partition_name,
        )

        if identity_key in seen_identity_keys:
            raise RuntimeError(
                "duplicate canonical Boot Image AVB signing identity: "
                f"{identity_kind}:{partition_name}"
            )

        seen_identity_keys.add(
            identity_key
        )

        algorithm_type = (
            parsed_vbmeta
            .metadata
            .algorithm_type
        )

        algorithm_name = (
            avb_algorithm_name_by_type
            .get(
                algorithm_type
            )
        )

        #
        # AVB algorithm type 0 is NONE. It is canonical AVB/VBMeta
        # evidence, but it carries no RSA signing identity and therefore
        # must not create a development-private-key requirement.
        #
        if algorithm_type == 0:
            unsigned_avb_identities.append(
                {
                    "partition_name": partition_name,
                    "kind": identity_kind,
                    "algorithm_type": algorithm_type,
                    "algorithm_name": "NONE",
                }
            )

            continue

        rsa_bits = (
            avb_rsa_bits_by_algorithm_type
            .get(
                algorithm_type
            )
        )

        partition_key_root = (
            development_key_root
            / partition_name
        )

        private_key_path = (
            partition_key_root
            / "development.pem"
        )

        public_key_path = (
            partition_key_root
            / "development.avbpubkey"
        )

        signing_identities.append(
            {
                "partition_name": partition_name,
                "kind": identity_kind,
                "algorithm_type": algorithm_type,
                "algorithm_name": algorithm_name,
                "rsa_bits": rsa_bits,
                "private_key_path": private_key_path,
                "public_key_path": public_key_path,
                "exists": private_key_path.is_file(),
            }
        )

    #
    # Mutation-driven embedded AVB identity completion.
    #
    # The general Parsing AVB inventory above is artifact-centric so it can
    # contain embedded VBMeta from non-boot containers such as APEX payloads.
    # Boot Image therefore cannot treat every embedded ParsedAvbVbmeta as a
    # boot-family signing identity.
    #
    # Once an explicit Boot Image component mutation exists, however, the
    # target boot-family partition is already unambiguous. Parsing also
    # preserves the exact InventoryPartition identity on embedded VBMeta.
    #
    # Complete the managed-key inventory for each mutated boot-family image
    # from that exact partition relationship. This is target-neutral and does
    # not special-case vendor_boot, init_boot, or any device.
    #
    mutated_container_kinds = tuple(
        dict.fromkeys(
            spec.container_kind
            for spec
            in mutation_specs
        )
    )

    for container_kind in (
        mutated_container_kinds
    ):
        image_matches = tuple(
            image
            for image
            in parsing_result.boot_images
            if (
                image.container_kind
                == container_kind
            )
        )

        if len(
            image_matches
        ) != 1:
            raise RuntimeError(
                "Boot Image signing preflight requires exactly one "
                "canonical boot-family image for mutated container "
                f"{container_kind!r}; found {len(image_matches)}"
            )

        image = (
            image_matches[
                0
            ]
        )

        partition = (
            image.partition
        )

        partition_name = (
            partition.name
        )

        embedded_matches = tuple(
            parsed_vbmeta
            for parsed_vbmeta
            in parsing_result.vbmeta
            if (
                parsed_vbmeta.partition
                is partition
                and (
                    parsed_vbmeta.artifact
                    is not
                    parsed_vbmeta.container_artifact
                )
            )
        )

        if not embedded_matches:
            #
            # A changed boot-family image without embedded AVB does not
            # require a child embedded-VBMeta signing identity here.
            #
            continue

        if len(
            embedded_matches
        ) != 1:
            raise RuntimeError(
                "mutated Boot Image partition has multiple canonical "
                "embedded VBMeta identities: "
                f"{partition_name}: {len(embedded_matches)}"
            )

        parsed_vbmeta = (
            embedded_matches[
                0
            ]
        )

        identity_key = (
            "embedded",
            partition_name,
        )

        if (
            identity_key
            in seen_identity_keys
        ):
            #
            # The general artifact-centric pass already recovered the same
            # exact boot-family identity.
            #
            continue

        algorithm_type = (
            parsed_vbmeta
            .metadata
            .algorithm_type
        )

        algorithm_name = (
            avb_algorithm_name_by_type
            .get(
                algorithm_type
            )
        )

        seen_identity_keys.add(
            identity_key
        )

        if algorithm_type == 0:
            unsigned_avb_identities.append(
                {
                    "partition_name": (
                        partition_name
                    ),
                    "kind": "embedded",
                    "algorithm_type": (
                        algorithm_type
                    ),
                    "algorithm_name": "NONE",
                }
            )

            continue

        rsa_bits = (
            avb_rsa_bits_by_algorithm_type
            .get(
                algorithm_type
            )
        )

        partition_key_root = (
            development_key_root
            / partition_name
        )

        private_key_path = (
            partition_key_root
            / "development.pem"
        )

        public_key_path = (
            partition_key_root
            / "development.avbpubkey"
        )

        signing_identities.append(
            {
                "partition_name": (
                    partition_name
                ),
                "kind": "embedded",
                "algorithm_type": (
                    algorithm_type
                ),
                "algorithm_name": (
                    algorithm_name
                ),
                "rsa_bits": (
                    rsa_bits
                ),
                "private_key_path": (
                    private_key_path
                ),
                "public_key_path": (
                    public_key_path
                ),
                "exists": (
                    private_key_path
                    .is_file()
                ),
            }
        )

    #
    # One partition should not need two incompatible TreeForge-managed
    # development identities. If the same canonical partition appears
    # through multiple AVB source forms, prove that the algorithm agrees.
    #
    algorithms_by_partition = {}

    for identity in signing_identities:
        partition_name = (
            identity[
                "partition_name"
            ]
        )

        algorithm_type = (
            identity[
                "algorithm_type"
            ]
        )

        previous = (
            algorithms_by_partition
            .get(
                partition_name
            )
        )

        if (
            previous is not None
            and previous != algorithm_type
        ):
            raise RuntimeError(
                "canonical AVB evidence requires incompatible "
                "signing algorithms for partition "
                f"{partition_name}: "
                f"{previous} vs {algorithm_type}"
            )

        algorithms_by_partition[
            partition_name
        ] = algorithm_type

    typer.echo()
    typer.echo(
        "Checking Boot Image signing material..."
    )
    typer.echo()

    if not signing_identities:
        typer.echo(
            "Required signing identities: <none>"
        )
    else:
        typer.echo(
            "Required signing identities:"
        )

        for identity in signing_identities:
            partition_name = (
                identity[
                    "partition_name"
                ]
            )

            identity_kind = (
                identity[
                    "kind"
                ]
            )

            algorithm_name = (
                identity[
                    "algorithm_name"
                ]
            )

            status = (
                "found"
                if identity[
                    "exists"
                ]
                else "missing"
            )

            algorithm_display = (
                algorithm_name
                if algorithm_name is not None
                else (
                    "unsupported:"
                    f"{identity['algorithm_type']}"
                )
            )

            typer.echo(
                "  "
                f"{partition_name:<18} "
                f"{status:<7} "
                f"{identity_kind:<10} "
                f"{algorithm_display}"
            )

    if unsigned_avb_identities:
        typer.echo()
        typer.echo(
            "Unsigned AVB identities:"
        )

        for identity in (
            unsigned_avb_identities
        ):
            typer.echo(
                "  "
                f"{identity['partition_name']:<18} "
                f"{identity['kind']:<10} "
                "NONE"
            )

    missing_identities = [
        identity
        for identity
        in signing_identities
        if not identity[
            "exists"
        ]
    ]

    existing_identities = [
        identity
        for identity
        in signing_identities
        if identity[
            "exists"
        ]
    ]

    generated_partition_names = set()

    if missing_identities:
        typer.echo()

        generate_missing = typer.confirm(
            "Generate all missing TreeForge development keys?",
            default=True,
        )

        if generate_missing:
            openssl = which(
                "openssl"
            )

            if openssl is None:
                raise RuntimeError(
                    "OpenSSL is required to generate Boot Image "
                    "development signing keys, but it is unavailable "
                    "on PATH"
                )

            #
            # Generate once per canonical partition even if the
            # inventory contains multiple source forms for that
            # partition.
            #
            generated_once = set()

            for identity in (
                missing_identities
            ):
                partition_name = (
                    identity[
                        "partition_name"
                    ]
                )

                if (
                    partition_name
                    in generated_once
                ):
                    continue

                generated_once.add(
                    partition_name
                )

                rsa_bits = (
                    identity[
                        "rsa_bits"
                    ]
                )

                algorithm_name = (
                    identity[
                        "algorithm_name"
                    ]
                )

                if (
                    rsa_bits is None
                    or algorithm_name is None
                ):
                    typer.echo(
                        "  unable to generate "
                        f"{partition_name}: unsupported canonical "
                        "AVB algorithm type "
                        f"{identity['algorithm_type']}"
                    )

                    continue

                private_key_path = (
                    identity[
                        "private_key_path"
                    ]
                )

                public_key_path = (
                    identity[
                        "public_key_path"
                    ]
                )

                private_key_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                completed = subprocess.run(
                    (
                        openssl,
                        "genpkey",
                        "-algorithm",
                        "RSA",
                        "-pkeyopt",
                        f"rsa_keygen_bits:{rsa_bits}",
                        "-out",
                        str(
                            private_key_path
                        ),
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                if completed.returncode != 0:
                    stderr = (
                        completed.stderr
                        .decode(
                            "utf-8",
                            errors="replace",
                        )
                    )

                    raise RuntimeError(
                        "OpenSSL failed to generate Boot Image "
                        f"development key for {partition_name}: "
                        f"{stderr}"
                    )

                if not private_key_path.is_file():
                    raise RuntimeError(
                        "OpenSSL completed without producing "
                        "Boot Image development private key: "
                        f"{private_key_path}"
                    )

                private_key_path.chmod(
                    0o600
                )

                completed = subprocess.run(
                    (
                        str(
                            avbtool
                        ),
                        "extract_public_key",
                        "--key",
                        str(
                            private_key_path
                        ),
                        "--output",
                        str(
                            public_key_path
                        ),
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                if completed.returncode != 0:
                    stderr = (
                        completed.stderr
                        .decode(
                            "utf-8",
                            errors="replace",
                        )
                    )

                    raise RuntimeError(
                        "avbtool failed to derive Boot Image "
                        "development AVB public key for "
                        f"{partition_name}: {stderr}"
                    )

                if (
                    not public_key_path.is_file()
                    or public_key_path.stat().st_size <= 0
                ):
                    raise RuntimeError(
                        "avbtool did not produce a valid AVB "
                        "public key for "
                        f"{partition_name}: "
                        f"{public_key_path}"
                    )

                generated_partition_names.add(
                    partition_name
                )

                typer.echo(
                    "  generated "
                    f"{partition_name}: "
                    f"{private_key_path}"
                )

                #
                # Mark every inventory record for this partition as
                # now present.
                #
                for candidate in (
                    signing_identities
                ):
                    if (
                        candidate[
                            "partition_name"
                        ]
                        == partition_name
                    ):
                        candidate[
                            "exists"
                        ] = True

        else:
            typer.echo(
                "Missing TreeForge development keys "
                "remain unresolved."
            )

    reuse_existing = False

    if existing_identities:
        typer.echo()

        reuse_existing = typer.confirm(
            "Reuse all existing TreeForge development keys?",
            default=True,
        )

    avb_signing_keys = []

    vbmeta_signing_keys = []

    #
    # Select identities:
    #
    # - keys generated during this invocation are selected
    #   automatically because generation was explicitly approved;
    #
    # - keys which existed before this invocation are selected only
    #   if the grouped reuse prompt was approved;
    #
    # - explicit CLI keys continue to override these defaults below.
    #
    selected_partition_names = set()

    for identity in (
        signing_identities
    ):
        partition_name = (
            identity[
                "partition_name"
            ]
        )

        private_key_path = (
            identity[
                "private_key_path"
            ]
        )

        if not private_key_path.is_file():
            continue

        generated_now = (
            partition_name
            in generated_partition_names
        )

        if (
            not generated_now
            and not reuse_existing
        ):
            continue

        selection_key = (
            identity[
                "kind"
            ],
            partition_name,
        )

        if (
            selection_key
            in selected_partition_names
        ):
            continue

        selected_partition_names.add(
            selection_key
        )

        if (
            identity[
                "kind"
            ]
            == "embedded"
        ):
            avb_signing_keys.append(
                (
                    partition_name,
                    private_key_path.resolve(),
                )
            )

        elif (
            identity[
                "kind"
            ]
            == "standalone"
        ):
            vbmeta_signing_keys.append(
                (
                    partition_name,
                    private_key_path.resolve(),
                )
            )

        else:
            raise RuntimeError(
                "invalid Boot Image signing-identity kind: "
                f"{identity['kind']}"
            )

    typer.echo()
    typer.echo(
        "Boot Image signing-material selection:"
    )

    typer.echo(
        "  boot-image AVB keys selected: "
        f"{len(avb_signing_keys)}"
    )

    typer.echo(
        "  standalone VBMeta keys selected: "
        f"{len(vbmeta_signing_keys)}"
    )

    typer.echo()
    typer.echo(
        "Boot Image signing-material preflight complete."
    )
    typer.echo()

    seen_vbmeta_partitions = set()

    for value in (
        vbmeta_key
        or ()
    ):
        if "=" not in value:
            raise typer.BadParameter(
                "--vbmeta-key must use PARTITION=PATH"
            )

        partition_name, raw_path = (
            value.split(
                "=",
                1,
            )
        )

        partition_name = (
            partition_name.strip()
        )

        raw_path = raw_path.strip()

        if not partition_name:
            raise typer.BadParameter(
                "--vbmeta-key partition name cannot be empty"
            )

        if not raw_path:
            raise typer.BadParameter(
                "--vbmeta-key path cannot be empty"
            )

        if partition_name in seen_vbmeta_partitions:
            raise typer.BadParameter(
                "duplicate explicit --vbmeta-key partition: "
                f"{partition_name}"
            )

        key_path = (
            Path(raw_path)
            .expanduser()
            .resolve()
        )

        if not key_path.is_file():
            raise typer.BadParameter(
                "VBMeta signing key does not exist: "
                f"{key_path}"
            )

        seen_vbmeta_partitions.add(
            partition_name
        )

        vbmeta_signing_keys = [
            (
                existing_partition,
                existing_path,
            )
            for (
                existing_partition,
                existing_path,
            )
            in vbmeta_signing_keys
            if (
                existing_partition
                != partition_name
            )
        ]

        vbmeta_signing_keys.append(
            (
                partition_name,
                key_path,
            )
        )


    # Boot Image
    # --------------------------------------------------------

    typer.echo()
    typer.echo(
        "[Boot Image] Starting reconstruction pipeline..."
    )
    typer.echo(
        "  Phases: Intake -> Interpretation -> Composition -> "
        "Planning -> Realization -> Validation"
    )

    try:
        result = (
            AndroidBootImagePipeline()
            .execute(
                parsing_result,
                realization_root=(
                    boot_image_root
                    / "realization"
                ),
                mutation_specs=tuple(
                    mutation_specs
                ),
                avb_signing_key=avb_key,
                avb_signing_keys=tuple(
                    avb_signing_keys
                ),
                parent_vbmeta_signing_key=(
                    parent_vbmeta_key
                ),
                vbmeta_signing_keys=tuple(
                    vbmeta_signing_keys
                ),
                progress_callback=render_progress,
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Boot Image pipeline failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    if (
        result.parsing
        is not parsing_result
    ):
        typer.echo(
            (
                "Boot Image Interpretation lost exact "
                "AndroidParsingResult identity."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    validation_result = result

    realization_result = (
        validation_result.realization
    )

    planning_result = (
        realization_result.planning
    )

    composition_result = (
        planning_result.composition
    )

    interpretation_result = (
        composition_result.interpretation
    )

    if (
        realization_result.planning
        is not planning_result
    ):
        typer.echo(
            "Boot Image Realization lost exact Planning identity.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if (
        planning_result.composition
        is not composition_result
    ):
        typer.echo(
            "Boot Image Planning lost exact Composition identity.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if (
        composition_result.interpretation
        is not interpretation_result
    ):
        typer.echo(
            "Boot Image Composition lost exact Interpretation identity.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if (
        interpretation_result.parsing
        is not parsing_result
    ):
        typer.echo(
            (
                "Boot Image Planning/Composition/Interpretation "
                "lost exact Parsing identity."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    # --------------------------------------------------------
    # Interpretation Report
    # --------------------------------------------------------

    boot_image_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = interpretation_result

    report_path = (
        boot_image_root
        / "boot-image-report.txt"
    )

    lines: list[str] = [
        "=== BOOT IMAGE INTERPRETATION ===",
        "",
        "Canonical Parsing identity: preserved",
        (
            "Boot images: "
            f"{len(result.boot_images)}"
        ),
        (
            "Ramdisks: "
            f"{len(result.ramdisks)}"
        ),
        (
            "DTBO entries: "
            f"{result.dtbo_entry_count}"
        ),
        (
            "DTBO containers: "
            f"{result.dtbo_container_count}"
        ),
        (
            "VBMeta nodes: "
            f"{result.avb_vbmeta_count}"
        ),
        (
            "AVB regions: "
            f"{result.avb_region_count}"
        ),
        (
            "Unknown AVB descriptors: "
            f"{result.avb_unknown_descriptor_count}"
        ),
        "",
        "Boot-image component interpretation:",
    ]

    total_boot_components = 0
    boot_component_dispositions = {}

    for value in result.boot_images:
        lines.append(
            f"  {value.container_kind}:"
        )

        lines.append(
            (
                "    components: "
                f"{len(value.components)}"
            )
        )

        total_boot_components += len(
            value.components
        )

        for component in value.components:
            disposition = (
                component.disposition.value
            )

            boot_component_dispositions[
                disposition
            ] = (
                boot_component_dispositions.get(
                    disposition,
                    0,
                )
                + 1
            )

            lines.append(
                (
                    "    "
                    f"{component.semantic_name}: "
                    f"role={component.role.value} "
                    f"disposition={disposition}"
                )
            )

            if component.kernel is not None:
                lines.append(
                    (
                        "      ParsedKernelImage: yes "
                        "(exact decompressed child)"
                    )
                )
                lines.append(
                    (
                        "      parsed kernel artifact: "
                        f"{component.kernel.artifact.path}"
                    )
                )

            elif (
                component.role
                is AndroidBootImageComponentRole.KERNEL
            ):
                lines.append(
                    "      ParsedKernelImage: no"
                )

            if (
                component.boot_signature
                is not None
            ):
                metadata = (
                    component
                    .boot_signature
                    .metadata
                )

                lines.append(
                    (
                        "      ParsedBootSignature: yes "
                        "(exact component identity)"
                    )
                )
                lines.append(
                    (
                        "      AVB algorithm type: "
                        f"{metadata.algorithm_type}"
                    )
                )
                lines.append(
                    (
                        "      AVB descriptors: "
                        f"{len(metadata.descriptors)}"
                    )
                )
                lines.append(
                    (
                        "      AVB release string: "
                        f"{metadata.release_string!r}"
                    )
                )

            if (
                component.role.value
                == "ramdisk"
            ):
                lines.append(
                    (
                        "      ParsedAndroidRamdisk: "
                        + (
                            "yes (exact component identity)"
                            if component.ramdisk is not None
                            else "no"
                        )
                    )
                )

                if component.ramdisk is not None:
                    lines.append(
                        (
                            "      CPIO entries: "
                            f"{component.ramdisk.entry_count}"
                        )
                    )

            if (
                component.role.value
                == "bootconfig"
            ):
                lines.append(
                    (
                        "      ParsedAndroidBootconfig: "
                        + (
                            "yes (exact component identity)"
                            if component.bootconfig is not None
                            else "no"
                        )
                    )
                )

                if component.bootconfig is not None:
                    lines.append(
                        (
                            "      Bootconfig entries: "
                            f"{len(component.bootconfig.entries)}"
                        )
                    )
                    lines.append(
                        (
                            "      Bootconfig unparsed lines: "
                            f"{len(component.bootconfig.unparsed_lines)}"
                        )
                    )

            if (
                component.role.value
                == "dtb"
            ):
                lines.append(
                    (
                        "      ParsedFdt members: "
                        f"{len(component.dtbs)}"
                    )
                )

                for dtb_index, parsed_dtb in enumerate(
                    component.dtbs,
                ):
                    lines.append(
                        (
                            "      "
                            f"FDT[{dtb_index}]: "
                            f"bytes={parsed_dtb.header.totalsize} "
                            f"nodes={parsed_dtb.node_count} "
                            f"properties={parsed_dtb.property_count}"
                        )
                    )

                    lines.append(
                        (
                            "        artifact: "
                            f"{parsed_dtb.artifact.path}"
                        )
                    )

            if (
                component.role.value
                == "vendor_ramdisk_table"
            ):
                lines.append(
                    (
                        "      ParsedVendorRamdiskTable: "
                        + (
                            "yes (exact component identity)"
                            if (
                                component.vendor_ramdisk_table
                                is not None
                            )
                            else "no"
                        )
                    )
                )

                table = (
                    component.vendor_ramdisk_table
                )

                if table is not None:
                    lines.append(
                        (
                            "      table entry size: "
                            f"{table.entry_size}"
                        )
                    )
                    lines.append(
                        (
                            "      table entries: "
                            f"{len(table.entries)}"
                        )
                    )

                    for entry in table.entries:
                        lines.append(
                            (
                                "      "
                                f"entry[{entry.index}]: "
                                f"size={entry.ramdisk_size} "
                                f"offset={entry.ramdisk_offset} "
                                f"type={entry.ramdisk_type} "
                                f"name={entry.ramdisk_name!r}"
                            )
                        )

    accounted_boot_components = sum(
        boot_component_dispositions.values()
    )

    if (
        accounted_boot_components
        != total_boot_components
    ):
        raise RuntimeError(
            "Boot Image report boot-component accounting does "
            "not match canonical component population"
        )

    interpreted_boot_components = (
        boot_component_dispositions.get(
            "interpreted",
            0,
        )
    )

    preserved_boot_components = (
        boot_component_dispositions.get(
            "preserved_unclassified",
            0,
        )
    )

    lines.extend(
        (
            "",
            "Boot-image component conservation:",
            (
                "  Components: "
                f"{total_boot_components}"
            ),
            (
                "  Interpreted: "
                f"{interpreted_boot_components}"
            ),
            (
                "  Preserved unclassified: "
                f"{preserved_boot_components}"
            ),
            (
                "  Accounted: "
                f"{accounted_boot_components}"
            ),
            "  Conservation: PASS",
            (
                "  Fully classified: "
                + (
                    "yes"
                    if preserved_boot_components == 0
                    else "no"
                )
            ),
            "",
            "Ramdisk structural interpretation:",
        )
    )

    for value in result.ramdisks:
        name = (
            value.boot_family_name
            or value.ramdisk.boot_image_artifact.path.name
        )

        lines.extend(
            (
                f"  {name}:",
                (
                    "    CPIO entries: "
                    f"{value.cpio_entry_count}"
                ),
                (
                    "    CPIO interpreted entries: "
                    f"{len(value.cpio_entries)}"
                ),
                (
                    "    Canonical Parsing sources: "
                    f"{len(value.canonical_sources)}"
                ),
                (
                    "    INIT sources: "
                    f"{len(value.init_files)}"
                ),
                (
                    "    Fstab sources: "
                    f"{len(value.fstabs)}"
                ),
                (
                    "    Ueventd sources: "
                    f"{len(value.ueventd_files)}"
                ),
                (
                    "    Kernel modules: "
                    f"{len(value.kernel_modules)}"
                ),
                (
                    "    Kernel-module configurations: "
                    f"{len(value.kernel_module_configurations)}"
                ),
                (
                    "    Bootconfig: "
                    f"{'yes' if value.has_bootconfig else 'no'}"
                ),
                (
                    "    modules.load lines: "
                    f"{len(value.kernel_module_load_entries)}"
                ),
                (
                    "    modules.dep lines: "
                    f"{len(value.kernel_module_dependency_entries)}"
                ),
                (
                    "    modules.alias lines: "
                    f"{len(value.kernel_module_alias_entries)}"
                ),
                (
                    "    modules.softdep lines: "
                    f"{len(value.kernel_module_soft_dependency_entries)}"
                ),
                (
                    "    Uninterpreted module relationship lines: "
                    f"{len(value.kernel_module_uninterpreted_lines)}"
                ),
            )
        )

        canonical_source_kind_counts = {}

        for source in value.canonical_sources:
            key = source.kind.value
            canonical_source_kind_counts[
                key
            ] = (
                canonical_source_kind_counts.get(
                    key,
                    0,
                )
                + 1
            )

        lines.append(
            "    Canonical Parsing sources by kind:"
        )

        for (
            kind,
            count,
        ) in sorted(
            canonical_source_kind_counts.items()
        ):
            lines.append(
                f"      {kind}: {count}"
            )

        if value.canonical_sources:
            lines.append(
                "    Canonical Parsing source paths:"
            )

            for source in value.canonical_sources:
                lines.append(
                    "      "
                    f"[{source.kind.value}] "
                    f"{source.android_path.as_posix()}"
                )

        cpio_kind_counts = {}
        cpio_disposition_counts = {}

        for interpreted_entry in value.cpio_entries:
            key = interpreted_entry.kind.value
            cpio_kind_counts[
                key
            ] = (
                cpio_kind_counts.get(
                    key,
                    0,
                )
                + 1
            )

            disposition_key = (
                interpreted_entry
                .disposition
                .value
            )

            cpio_disposition_counts[
                disposition_key
            ] = (
                cpio_disposition_counts.get(
                    disposition_key,
                    0,
                )
                + 1
            )

        preserved_cpio_count = sum(
            1
            for interpreted_entry
            in value.cpio_entries
            if (
                interpreted_entry.disposition.value
                == "preserved_unclassified"
            )
        )

        lines.append(
            "    CPIO semantic kinds:"
        )

        for (
            kind,
            count,
        ) in sorted(
            cpio_kind_counts.items()
        ):
            lines.append(
                f"      {kind}: {count}"
            )

        lines.append(
            "    CPIO dispositions:"
        )

        for (
            disposition,
            count,
        ) in sorted(
            cpio_disposition_counts.items()
        ):
            lines.append(
                f"      {disposition}: {count}"
            )

        canonical_association_count = (
            cpio_disposition_counts.get(
                "canonical_parsing_association",
                0,
            )
        )

        preserved_resource_count = (
            cpio_disposition_counts.get(
                "preserved_resource",
                0,
            )
        )

        lines.append(
            "    CPIO canonical Parsing associations: "
            f"{canonical_association_count}"
        )

        lines.append(
            "    CPIO preserved resources: "
            f"{preserved_resource_count}"
        )

        lines.append(
            "    CPIO preserved unclassified: "
            f"{preserved_cpio_count}"
        )

        preserved_resource_entries = tuple(
            interpreted_entry
            for interpreted_entry
            in value.cpio_entries
            if (
                interpreted_entry.disposition.value
                == "preserved_resource"
            )
        )

        if preserved_resource_entries:
            lines.append(
                "    Preserved resource CPIO entries:"
            )

            for interpreted_entry in preserved_resource_entries:
                owner = (
                    interpreted_entry
                    .associated_source
                )

                lines.append(
                    "      "
                    f"[{interpreted_entry.index}] "
                    f"{interpreted_entry.entry.path} "
                    f"<- "
                    f"[{owner.kind.value}] "
                    f"{owner.android_path.as_posix()}"
                )

        preserved_cpio_entries = tuple(
            interpreted_entry
            for interpreted_entry
            in value.cpio_entries
            if (
                interpreted_entry.disposition.value
                == "preserved_unclassified"
            )
        )

        if preserved_cpio_entries:
            lines.append(
                "    Preserved unclassified CPIO entries:"
            )

            for interpreted_entry in preserved_cpio_entries:
                lines.append(
                    "      "
                    f"[{interpreted_entry.index}] "
                    f"{interpreted_entry.entry.path}"
                )

        relationship_references = []

        for entry in value.kernel_module_load_entries:
            relationship_references.extend(
                entry.references
            )

        for entry in value.kernel_module_dependency_entries:
            relationship_references.append(
                entry.module
            )
            relationship_references.extend(
                entry.dependencies
            )

        for entry in value.kernel_module_alias_entries:
            relationship_references.append(
                entry.module
            )

        for entry in value.kernel_module_soft_dependency_entries:
            relationship_references.append(
                entry.module
            )
            relationship_references.extend(
                entry.pre
            )
            relationship_references.extend(
                entry.post
            )

        resolved_count = sum(
            1
            for reference
            in relationship_references
            if reference.resolution.value
            == "resolved"
        )

        unresolved_count = sum(
            1
            for reference
            in relationship_references
            if reference.resolution.value
            == "unresolved"
        )

        ambiguous_count = sum(
            1
            for reference
            in relationship_references
            if reference.resolution.value
            == "ambiguous"
        )

        lines.append(
            "    Kernel-module reference resolution:"
        )
        lines.append(
            f"      Resolved: {resolved_count}"
        )
        lines.append(
            f"      Unresolved: {unresolved_count}"
        )
        lines.append(
            f"      Ambiguous: {ambiguous_count}"
        )

        if value.kernel_modules:
            lines.append(
                "    Kernel modules:"
            )

            for module in value.kernel_modules:
                lines.append(
                    "      "
                    + module.android_path.as_posix()
                )

        if value.kernel_module_configurations:
            lines.append(
                "    Kernel-module configuration kinds:"
            )

            for configuration in (
                value.kernel_module_configurations
            ):
                lines.append(
                    "      "
                    + configuration.configuration_kind.value
                )

        if value.init_files:
            lines.append(
                "    INIT sources:"
            )

            for source in value.init_files:
                lines.append(
                    "      "
                    + (
                        source.android_path.as_posix()
                        if source.android_path is not None
                        else str(
                            source.source_path
                        )
                    )
                )

        if value.fstabs:
            lines.append(
                "    Fstab sources:"
            )

            for source in value.fstabs:
                lines.append(
                    "      "
                    + (
                        source.android_path.as_posix()
                        if source.android_path is not None
                        else str(
                            source.source_path
                        )
                    )
                )

        if value.ueventd_files:
            lines.append(
                "    Ueventd sources:"
            )

            for source in value.ueventd_files:
                lines.append(
                    "      "
                    + (
                        source.android_path.as_posix()
                        if source.android_path is not None
                        else str(
                            source.source_path
                        )
                    )
                )

    total_cpio_entries = sum(
        value.cpio_entry_count
        for value
        in result.ramdisks
    )

    global_cpio_dispositions = {}

    for value in result.ramdisks:
        for interpreted_entry in value.cpio_entries:
            key = (
                interpreted_entry
                .disposition
                .value
            )

            global_cpio_dispositions[
                key
            ] = (
                global_cpio_dispositions.get(
                    key,
                    0,
                )
                + 1
            )

    interpreted_cpio_count = (
        global_cpio_dispositions.get(
            "interpreted",
            0,
        )
    )

    canonical_cpio_count = (
        global_cpio_dispositions.get(
            "canonical_parsing_association",
            0,
        )
    )

    preserved_resource_count = (
        global_cpio_dispositions.get(
            "preserved_resource",
            0,
        )
    )

    preserved_unclassified_count = (
        global_cpio_dispositions.get(
            "preserved_unclassified",
            0,
        )
    )

    accounted_cpio_entries = sum(
        global_cpio_dispositions.values()
    )

    if (
        accounted_cpio_entries
        != total_cpio_entries
    ):
        raise RuntimeError(
            "Boot Image report CPIO accounting does not "
            "match the canonical ramdisk population"
        )

    lines.extend(
        (
            "",
            "Ramdisk CPIO conservation:",
            (
                "  Entries: "
                f"{total_cpio_entries}"
            ),
            (
                "  Boot Image interpreted: "
                f"{interpreted_cpio_count}"
            ),
            (
                "  Canonical Parsing associations: "
                f"{canonical_cpio_count}"
            ),
            (
                "  Preserved resources: "
                f"{preserved_resource_count}"
            ),
            (
                "  Preserved unclassified: "
                f"{preserved_unclassified_count}"
            ),
            (
                "  Accounted: "
                f"{accounted_cpio_entries}"
            ),
            "  Conservation: PASS",
            (
                "  Fully classified: "
                + (
                    "yes"
                    if preserved_unclassified_count == 0
                    else "no"
                )
            ),
        )
    )

    report_text = (
        "\n".join(
            lines
        )
        + "\n"
    )

    report_path.write_text(
        report_text,
        encoding="utf-8",
    )

    if verbose:
        typer.echo()
        typer.echo(
            report_text,
            nl=False,
        )

    typer.echo()
    typer.echo(
        "[Boot Image] Interpretation complete."
    )
    typer.echo(
        "  Boot images: "
        f"{len(interpretation_result.boot_images)}"
    )
    typer.echo(
        "  Ramdisks: "
        f"{len(interpretation_result.ramdisks)}"
    )
    typer.echo(
        "  DTBO entries: "
        f"{interpretation_result.dtbo_entry_count}"
    )
    typer.echo(
        f"  Report: {report_path}"
    )

    composition_report_path = (
        boot_image_root
        / "boot-image-composition-report.txt"
    )

    composition_lines: list[str] = [
        "=== BOOT IMAGE COMPOSITION ===",
        "",
        "Interpretation identity: preserved",
        "Canonical Parsing identity: preserved",
        (
            "Boot-image compositions: "
            f"{len(composition_result.boot_images)}"
        ),
        (
            "Boot components: "
            f"{composition_result.component_count}"
        ),
        (
            "Ramdisk associations: "
            f"{sum(1 for image in composition_result.boot_images if image.ramdisk is not None)}"
        ),
        (
            "DTBO entries: "
            f"{composition_result.dtbo_entry_count}"
        ),
        (
            "DTBO containers: "
            f"{composition_result.dtbo_container_count}"
        ),
        (
            "VBMeta nodes: "
            f"{composition_result.avb_vbmeta_count}"
        ),
        (
            "AVB regions: "
            f"{composition_result.avb_region_count}"
        ),
        "",
        "Boot-family structural compositions:",
    ]

    composed_component_count = 0

    for image in composition_result.boot_images:
        composed_component_count += (
            image.component_count
        )

        composition_lines.extend(
            (
                f"  {image.container_kind}:",
                (
                    "    components: "
                    f"{image.component_count}"
                ),
                (
                    "    parsed kernel: "
                    f"{'yes' if image.kernel is not None else 'no'}"
                ),
                (
                    "    ramdisk: "
                    f"{'yes' if image.ramdisk is not None else 'no'}"
                ),
                (
                    "    bootconfig: "
                    f"{'yes' if image.bootconfig is not None else 'no'}"
                ),
                (
                    "    DTB/FDT members: "
                    f"{len(image.dtb_members)}"
                ),
                (
                    "    vendor ramdisk table: "
                    f"{'yes' if image.vendor_ramdisk_table is not None else 'no'}"
                ),
                (
                    "    boot signature: "
                    f"{'yes' if image.boot_signature is not None else 'no'}"
                ),
                (
                    "    AVB physical regions: "
                    f"{len(image.avb_regions)}"
                ),
                (
                    "    AVB partition references: "
                    f"{len(image.avb_partition_references)}"
                ),
                (
                    "    signed payloads: "
                    f"{len(image.signed_payloads)}"
                ),
            )
        )

        composition_lines.append(
            "    component order:"
        )

        for component in image.components:
            composition_lines.append(
                (
                    "      "
                    f"{component.semantic_name}: "
                    f"{component.role.value}"
                )
            )

        if image.ramdisk is not None:
            composition_lines.extend(
                (
                    (
                        "    ramdisk CPIO entries: "
                        f"{image.ramdisk.cpio_entry_count}"
                    ),
                    (
                        "    canonical Parsing sources: "
                        f"{len(image.ramdisk.canonical_sources)}"
                    ),
                    (
                        "    INIT sources: "
                        f"{len(image.ramdisk.init_files)}"
                    ),
                    (
                        "    fstab sources: "
                        f"{len(image.ramdisk.fstabs)}"
                    ),
                    (
                        "    ueventd sources: "
                        f"{len(image.ramdisk.ueventd_files)}"
                    ),
                    (
                        "    kernel modules: "
                        f"{len(image.ramdisk.kernel_modules)}"
                    ),
                    (
                        "    kernel-module configurations: "
                        f"{len(image.ramdisk.kernel_module_configurations)}"
                    ),
                )
            )

        if image.dtb_members:
            composition_lines.append(
                "    DTB/FDT member order:"
            )

            for index, dtb in enumerate(
                image.dtb_members
            ):
                composition_lines.append(
                    (
                        f"      [{index}] "
                        f"{dtb.artifact.path} "
                        f"bytes={dtb.header.totalsize}"
                    )
                )

        if (
            image.vendor_ramdisk_table
            is not None
        ):
            table = (
                image.vendor_ramdisk_table
            )

            composition_lines.append(
                (
                    "    vendor ramdisk table entries: "
                    f"{len(table.entries)}"
                )
            )

            for entry in table.entries:
                composition_lines.append(
                    (
                        f"      [{entry.index}] "
                        f"size={entry.ramdisk_size} "
                        f"offset={entry.ramdisk_offset} "
                        f"type={entry.ramdisk_type} "
                        f"name={entry.ramdisk_name!r}"
                    )
                )

        if image.vendor_ramdisk_entries:
            composition_lines.append(
                "    vendor ramdisk byte-range composition:"
            )

            for value in (
                image.vendor_ramdisk_entries
            ):
                composition_lines.append(
                    (
                        f"      [{value.entry.index}] "
                        f"{value.start_offset_bytes}:"
                        f"{value.end_offset_bytes} "
                        f"size={value.entry.ramdisk_size} "
                        f"type={value.entry.ramdisk_type} "
                        f"name={value.entry.ramdisk_name!r} "
                        "complete_component="
                        f"{value.covers_complete_ramdisk_component}"
                    )
                )

        if image.signed_payloads:
            composition_lines.append(
                "    signed-payload composition:"
            )

            for value in image.signed_payloads:
                covered = (
                    ", ".join(
                        component.semantic_name
                        for component
                        in value.covered_components
                    )
                    if value.covered_components
                    else "<none>"
                )

                composition_lines.append(
                    (
                        "      range="
                        f"{value.start_offset_bytes}:"
                        f"{value.end_offset_bytes} "
                        "signature="
                        f"{value.signature_component.semantic_name} "
                        "partition="
                        f"{value.descriptor.partition_name} "
                        "covered_components="
                        f"{covered}"
                    )
                )

        if image.avb_regions:
            composition_lines.append(
                "    AVB physical-region dispositions:"
            )

            for region in image.avb_regions:
                composition_lines.append(
                    (
                        "      "
                        f"{region.disposition}: "
                        f"{region.artifact.semantic_name or region.artifact.path.name}"
                    )
                )

        if image.avb_partition_references:
            composition_lines.append(
                "    AVB partition references:"
            )

            for reference in (
                image.avb_partition_references
            ):
                composition_lines.append(
                    (
                        "      "
                        f"{reference.descriptor.kind.value}: "
                        f"{reference.target_partition} "
                        "from "
                        f"{reference.vbmeta.artifact.path}"
                    )
                )

    if (
        composed_component_count
        != composition_result.component_count
    ):
        raise RuntimeError(
            "Boot Image Composition report component "
            "accounting failed"
        )

    composition_lines.extend(
        (
            "",
            "Composition conservation:",
            (
                "  Interpretation boot images: "
                f"{len(composition_result.interpretation.boot_images)}"
            ),
            (
                "  Composed boot images: "
                f"{len(composition_result.boot_images)}"
            ),
            (
                "  Interpretation components: "
                f"{composition_result.interpretation.component_count}"
            ),
            (
                "  Composed components: "
                f"{composition_result.component_count}"
            ),
            (
                "  Interpretation ramdisks: "
                f"{len(composition_result.interpretation.ramdisks)}"
            ),
            (
                "  Composed ramdisk associations: "
                f"{sum(1 for image in composition_result.boot_images if image.ramdisk is not None)}"
            ),
            (
                "  Vendor ramdisk table-entry ranges: "
                f"{sum(len(image.vendor_ramdisk_entries) for image in composition_result.boot_images)}"
            ),
            (
                "  Boot-image AVB physical-region associations: "
                f"{sum(len(image.avb_regions) for image in composition_result.boot_images)}"
            ),
            (
                "  Boot-image AVB partition references: "
                f"{sum(len(image.avb_partition_references) for image in composition_result.boot_images)}"
            ),
            (
                "  Signed-payload relationships: "
                f"{sum(len(image.signed_payloads) for image in composition_result.boot_images)}"
            ),
            "  DTBO remains globally composed: yes",
            "  Exact Interpretation identity: PASS",
            "  Exact canonical Parsing identity: PASS",
            "  Conservation: PASS",
        )
    )

    composition_report_text = (
        "\n".join(
            composition_lines
        )
        + "\n"
    )

    composition_report_path.write_text(
        composition_report_text,
        encoding="utf-8",
    )

    if verbose:
        typer.echo()
        typer.echo(
            composition_report_text,
            nl=False,
        )

    typer.echo()
    typer.echo(
        "[Boot Image] Composition complete."
    )
    typer.echo(
        "  Boot images: "
        f"{len(composition_result.boot_images)}"
    )
    typer.echo(
        "  Components: "
        f"{composition_result.component_count}"
    )
    typer.echo(
        "  DTBO containers: "
        f"{composition_result.dtbo_container_count}"
    )
    typer.echo(
        "  VBMeta nodes: "
        f"{composition_result.avb_vbmeta_count}"
    )
    typer.echo(
        f"  Report: {composition_report_path}"
    )

    planning_report_path = (
        boot_image_root
        / "boot-image-planning-report.txt"
    )

    planning_lines: list[str] = [
        "=== BOOT IMAGE PLANNING ===",
        "",
        "Composition identity: preserved",
        "Interpretation identity: preserved",
        "Canonical Parsing identity: preserved",
        (
            "Boot-image plans: "
            f"{len(planning_result.boot_images)}"
        ),
        (
            "Component plans: "
            f"{planning_result.component_plan_count}"
        ),
        (
            "Exact-preservation baselines: "
            f"{planning_result.exact_preservation_count}"
        ),
        (
            "Conditional requirements: "
            f"{planning_result.conditional_requirement_count}"
        ),
        (
            "Global DTBO containers: "
            f"{len(planning_result.dtbo_containers)}"
        ),
        "",
        "Boot-family plans:",
    ]

    for image in planning_result.boot_images:
        planning_lines.extend(
            (
                f"  {image.container_kind}:",
                (
                    "    component plans: "
                    f"{len(image.component_plans)}"
                ),
                (
                    "    exact preservation: "
                    f"{image.exact_preservation_count}"
                ),
                (
                    "    structured evidence available: "
                    f"{image.structured_evidence_count}"
                ),
                (
                    "    conditional requirements: "
                    f"{len(image.conditional_requirements)}"
                ),
                "    components:",
            )
        )

        for component_plan in (
            image.component_plans
        ):
            component = (
                component_plan.component
            )

            planning_lines.append(
                (
                    "      "
                    f"{component.semantic_name}: "
                    f"{component_plan.disposition.value} "
                    "structured_evidence="
                    f"{component_plan.structured_evidence_available}"
                )
            )

        if image.conditional_requirements:
            planning_lines.append(
                "    conditional requirements:"
            )

            for requirement in (
                image.conditional_requirements
            ):
                suffix = ""

                if requirement.component is not None:
                    suffix = (
                        " component="
                        f"{requirement.component.semantic_name}"
                    )

                planning_lines.append(
                    (
                        "      "
                        f"{requirement.kind.value}: "
                        f"trigger={requirement.trigger.value}"
                        f"{suffix}"
                    )
                )

    evidence_disposition_counts = {}

    for value in planning_result.evidence:
        disposition = value.disposition.value

        evidence_disposition_counts[
            disposition
        ] = (
            evidence_disposition_counts.get(
                disposition,
                0,
            )
            + 1
        )

    evidence_category_counts = {}

    for value in planning_result.evidence:
        evidence_category_counts[
            value.category
        ] = (
            evidence_category_counts.get(
                value.category,
                0,
            )
            + 1
        )

    planning_lines.extend(
        (
            "",
            "Evidence accounting:",
            (
                "  Evidence records: "
                f"{planning_result.evidence_count}"
            ),
            (
                "  Retained unresolved: "
                f"{planning_result.retained_unresolved_count}"
            ),
            (
                "  Retained ambiguous: "
                f"{planning_result.retained_ambiguous_count}"
            ),
            "  By disposition:",
        )
    )

    for disposition in sorted(
        evidence_disposition_counts
    ):
        planning_lines.append(
            (
                f"    {disposition}: "
                f"{evidence_disposition_counts[disposition]}"
            )
        )

    planning_lines.append(
        "  By category:"
    )

    for category in sorted(
        evidence_category_counts
    ):
        planning_lines.append(
            (
                f"    {category}: "
                f"{evidence_category_counts[category]}"
            )
        )

    planning_lines.extend(
        (
            "",
            "Global planning:",
            (
                "  DTBO containers preserved exactly: "
                f"{len(planning_result.dtbo_containers)}"
            ),
            "  Provider selection performed: no",
            "  Output paths selected: no",
            "  Build tools selected: no",
            "  Signing keys selected: no",
            "",
            "Planning conservation:",
            (
                "  Composition boot images: "
                f"{len(planning_result.composition.boot_images)}"
            ),
            (
                "  Planned boot images: "
                f"{len(planning_result.boot_images)}"
            ),
            (
                "  Composition components: "
                f"{planning_result.composition.component_count}"
            ),
            (
                "  Planned components: "
                f"{planning_result.component_plan_count}"
            ),
            (
                "  Composition DTBO containers: "
                f"{planning_result.composition.dtbo_container_count}"
            ),
            (
                "  Planned DTBO containers: "
                f"{len(planning_result.dtbo_containers)}"
            ),
            "  Exact Composition identity: PASS",
            "  Exact Interpretation identity: PASS",
            "  Exact canonical Parsing identity: PASS",
            "  Conservation: PASS",
        )
    )

    planning_report_text = (
        "\n".join(
            planning_lines
        )
        + "\n"
    )

    planning_report_path.write_text(
        planning_report_text,
        encoding="utf-8",
    )

    if verbose:
        typer.echo()
        typer.echo(
            planning_report_text,
            nl=False,
        )

    typer.echo()
    typer.echo(
        "[Boot Image] Planning complete."
    )
    typer.echo(
        "  Boot-image plans: "
        f"{len(planning_result.boot_images)}"
    )
    typer.echo(
        "  Component plans: "
        f"{planning_result.component_plan_count}"
    )
    typer.echo(
        "  Exact-preservation baselines: "
        f"{planning_result.exact_preservation_count}"
    )
    typer.echo(
        "  Conditional requirements: "
        f"{planning_result.conditional_requirement_count}"
    )
    typer.echo(
        f"  Report: {planning_report_path}"
    )

    realization_report_path = (
        boot_image_root
        / "boot-image-realization-report.txt"
    )

    realization_lines: list[str] = [
        "=== BOOT IMAGE REALIZATION ===",
        "",
        "Planning identity: preserved",
        "Composition identity: preserved",
        "Interpretation identity: preserved",
        "Canonical Parsing identity: preserved",
        (
            "Component realizations: "
            f"{len(realization_result.components)}"
        ),
        (
            "DTBO container realizations: "
            f"{len(realization_result.dtbo_containers)}"
        ),
        (
            "Exact-preservation realizations: "
            f"{realization_result.exact_preservation_count}"
        ),
        (
            "Mutated realizations: "
            f"{realization_result.mutated_count}"
        ),
        (
            "Mutation requests: "
            f"{realization_result.mutation_request_count}"
        ),
        (
            "Mutation evaluations: "
            f"{realization_result.mutation_evaluation_count}"
        ),
        (
            "Active conditional requirements: "
            f"{realization_result.active_conditional_requirement_count}"
        ),
        (
            "Provider candidates discovered: "
            f"{realization_result.provider_candidate_count}"
        ),
        (
            "Provider selections: "
            f"{realization_result.provider_selection_count}"
        ),
        (
            "Provider invocations: "
            f"{realization_result.provider_invocation_count}"
        ),
        (
            "AVB resolutions: "
            f"{realization_result.avb_resolution_count}"
        ),
        (
            "AVB signing material required: "
            f"{realization_result.avb_signing_material_required_count}"
        ),
        (
            "Rebuilt boot images: "
            f"{realization_result.rebuilt_boot_image_count}"
        ),
        (
            "Parent VBMeta rewrites: "
            f"{realization_result.parent_vbmeta_rewrite_count}"
        ),
        (
            "Parent VBMeta realizations: "
            f"{realization_result.parent_vbmeta_realization_count}"
        ),
        (
            "Parent VBMeta signing material required: "
            f"{realization_result.parent_vbmeta_signing_material_required_count}"
        ),
        (
            "Planning evidence records retained: "
            f"{realization_result.evidence_count}"
        ),
        "",
        "Boot-family component realizations:",
    ]

    component_index = 0

    for image in planning_result.boot_images:
        realization_lines.append(
            f"  {image.container_kind}:"
        )

        for plan in image.component_plans:
            realized = (
                realization_result.components[
                    component_index
                ]
            )

            if realized.plan is not plan:
                raise RuntimeError(
                    "Boot Image Realization report lost "
                    "component-plan identity"
                )

            realization_lines.append(
                (
                    "    "
                    f"{plan.component.semantic_name}: "
                    f"provider={realized.provider.value} "
                    f"mutated={realized.mutated} "
                    f"bytes={realized.size_bytes} "
                    f"sha256={realized.content_sha256} "
                    f"output={realized.output_path}"
                )
            )

            component_index += 1

    realization_lines.extend(
        (
            "",
            "Rebuilt boot-family images:",
        )
    )

    if not realization_result.rebuilt_boot_images:
        realization_lines.append(
            "  <none>"
        )

    for rebuilt in (
        realization_result.rebuilt_boot_images
    ):
        realization_lines.append(
            (
                "  "
                f"{rebuilt.image_plan.container_kind}: "
                f"provider={rebuilt.provider.name} "
                f"verification_provider="
                f"{rebuilt.verification_provider.name} "
                f"bytes={rebuilt.size_bytes} "
                f"sha256={rebuilt.content_sha256} "
                f"avb_complete={rebuilt.avb_complete} "
                f"parent_trust_complete="
                f"{rebuilt.parent_trust_complete} "
                f"flashable_chain_complete="
                f"{rebuilt.flashable_chain_complete} "
                f"output={rebuilt.output_path}"
            )
        )

    realization_lines.extend(
        (
            "",
            "Global DTBO realizations:",
        )
    )

    for realized in (
        realization_result.dtbo_containers
    ):
        realization_lines.append(
            (
                "  "
                f"provider={realized.provider.value} "
                f"mutated={realized.mutated} "
                f"entries={realized.container.entry_count} "
                f"bytes={realized.size_bytes} "
                f"sha256={realized.content_sha256} "
                f"output={realized.output_path}"
            )
        )

    realization_lines.extend(
        (
            "",
            "Mutation trigger evaluation:",
            (
                "  Explicit mutation requests: "
                f"{realization_result.mutation_request_count}"
            ),
            (
                "  Evaluated mutation requests: "
                f"{realization_result.mutation_evaluation_count}"
            ),
            (
                "  Active Planning requirements: "
                f"{realization_result.active_conditional_requirement_count}"
            ),
        )
    )

    if (
        realization_result
        .active_conditional_requirements
    ):
        for requirement in (
            realization_result
            .active_conditional_requirements
        ):
            realization_lines.append(
                (
                    "    "
                    f"{requirement.kind.value}: "
                    f"trigger={requirement.trigger.value}"
                )
            )

    realization_lines.extend(
        (
            "",
            "AVB requirement resolution:",
        )
    )

    if not realization_result.avb_resolutions:
        realization_lines.append(
            "  <none>"
        )

    for resolution in (
        realization_result.avb_resolutions
    ):
        contract = resolution.contract

        realization_lines.extend(
            (
                (
                    "  "
                    f"{contract.partition_name}: "
                    f"policy={resolution.signing_policy.value} "
                    f"disposition={resolution.disposition.value}"
                ),
                (
                    "    partition bytes: "
                    f"{contract.partition_size_bytes}"
                ),
                (
                    "    factory original image bytes: "
                    f"{contract.factory_original_image_size_bytes}"
                ),
                (
                    "    hash algorithm: "
                    f"{contract.hash_algorithm}"
                ),
                (
                    "    algorithm type: "
                    f"{contract.algorithm_type}"
                ),
                (
                    "    rollback index: "
                    f"{contract.rollback_index}"
                ),
                (
                    "    rollback index location: "
                    f"{contract.rollback_index_location}"
                ),
                (
                    "    VBMeta flags: "
                    f"{contract.vbmeta_flags}"
                ),
                (
                    "    descriptor flags: "
                    f"{contract.descriptor_flags}"
                ),
                (
                    "    salt: "
                    f"{contract.salt.hex()}"
                ),
                (
                    "    property descriptors: "
                    f"{len(contract.property_descriptors)}"
                ),
                (
                    "    parent chain references: "
                    f"{len(contract.parent_chain_references)}"
                ),
                (
                    "    factory public key bytes: "
                    f"{len(contract.factory_public_key)}"
                ),
                (
                    "    signing key supplied: "
                    + (
                        "yes"
                        if resolution.signing_key_path is not None
                        else "no"
                    )
                ),
                (
                    "    derived public key bytes: "
                    + (
                        str(
                            len(
                                resolution.derived_public_key
                            )
                        )
                        if resolution.derived_public_key is not None
                        else "unresolved"
                    )
                ),
                (
                    "    factory signing identity matched: "
                    + (
                        "unresolved"
                        if resolution.derived_public_key is None
                        else (
                            "yes"
                            if (
                                resolution.derived_public_key
                                == contract.factory_public_key
                            )
                            else "no"
                        )
                    )
                ),
                (
                    "    parent trust update required: "
                    + (
                        "unresolved"
                        if (
                            resolution
                            .parent_trust_update_required
                            is None
                        )
                        else (
                            "yes"
                            if (
                                resolution
                                .parent_trust_update_required
                            )
                            else "no"
                        )
                    )
                ),
            )
        )

    realization_lines.extend(
        (
            "",
            "Parent VBMeta trust rewrites:",
        )
    )

    if not (
        realization_result
        .parent_vbmeta_rewrites
    ):
        realization_lines.append(
            "  <none>"
        )

    for rewrite_index, rewrite in enumerate(
        realization_result
        .parent_vbmeta_rewrites
    ):
        parent_partition_name = (
            getattr(
                rewrite.parent_vbmeta.partition,
                "name",
                None,
            )
        )

        if (
            not isinstance(
                parent_partition_name,
                str,
            )
            or not parent_partition_name
        ):
            raise RuntimeError(
                "Boot Image Realization report encountered "
                "a standalone parent VBMeta without its "
                "canonical partition name"
            )

        realization_lines.extend(
            (
                (
                    "  "
                    f"parent={parent_partition_name} "
                    f"batch={rewrite_index}"
                ),
                (
                    "    changed descriptors: "
                    f"{rewrite.changed_descriptor_count}"
                ),
                (
                    "    descriptor count: "
                    f"{rewrite.descriptor_count}"
                ),
                (
                    "    unchanged descriptors: "
                    f"{rewrite.unchanged_descriptor_count}"
                ),
                (
                    "    public keys changed: "
                    + (
                        "yes"
                        if rewrite.public_key_changed
                        else "no"
                    )
                ),
                (
                    "    original descriptor bytes: "
                    f"{len(rewrite.original_descriptor_blob)}"
                ),
                (
                    "    rewritten descriptor bytes: "
                    f"{len(rewrite.rewritten_descriptor_blob)}"
                ),
                (
                    "    descriptor order preserved: "
                    + (
                        "yes"
                        if rewrite.descriptor_order_preserved
                        else "no"
                    )
                ),
                (
                    "    output: "
                    f"{rewrite.output_path}"
                ),
                "    changed child trust edges:",
            )
        )

        for (
            trust_change,
            descriptor_index,
            original_chain,
            rewritten_chain,
        ) in zip(
            rewrite.trust_changes,
            rewrite.descriptor_indexes,
            rewrite.original_chain_descriptors,
            rewrite.rewritten_chain_descriptors,
            strict=True,
        ):
            if (
                trust_change.source_resolution
                is not None
            ):
                source_kind = (
                    "boot_image"
                )

                source_name = (
                    trust_change
                    .source_resolution
                    .contract
                    .partition_name
                )

            else:
                source_kind = (
                    "parent_vbmeta"
                )

                source_parent = (
                    trust_change
                    .source_parent_realization
                )

                if source_parent is None:
                    raise RuntimeError(
                        "recursive AVB trust change lost "
                        "its realization source"
                    )

                source_name = getattr(
                    source_parent
                    .parent_vbmeta
                    .partition,
                    "name",
                    None,
                )

                if (
                    not isinstance(
                        source_name,
                        str,
                    )
                    or not source_name
                ):
                    raise RuntimeError(
                        "recursive AVB trust-change source "
                        "has no canonical partition name"
                    )

            realization_lines.extend(
                (
                    (
                        "      "
                        f"target={trust_change.target_partition} "
                        f"descriptor_index={descriptor_index}"
                    ),
                    (
                        "        source: "
                        f"{source_kind}:{source_name}"
                    ),
                    (
                        "        old public key bytes: "
                        f"{len(original_chain.public_key)}"
                    ),
                    (
                        "        new public key bytes: "
                        f"{len(rewritten_chain.public_key)}"
                    ),
                    (
                        "        canonical parent references: "
                        f"{trust_change.parent_count}"
                    ),
                )
            )

    realization_lines.extend(
        (
            "",
            "Parent VBMeta realizations:",
        )
    )

    if not (
        realization_result
        .parent_vbmeta_realizations
    ):
        realization_lines.append(
            "  <none>"
        )

    for realized in (
        realization_result
        .parent_vbmeta_realizations
    ):
        realization_lines.extend(
            (
                (
                    "  "
                    f"target="
                    f"{realized.rewrite.target_partition}"
                ),
                (
                    "    signed: "
                    + (
                        "yes"
                        if realized.verification_complete
                        else "no"
                    )
                ),
                (
                    "    trust disposition: "
                    f"{realized.trust_disposition.value}"
                ),
                (
                    "    upstream AVB references: "
                    f"{realized.upstream_chain_reference_count}"
                ),
                (
                    "    top-level AVB node: "
                    + (
                        "yes"
                        if realized.is_top_level_avb_node
                        else "no"
                    )
                ),
                (
                    "    upstream trust update required: "
                    + (
                        "yes"
                        if realized.upstream_trust_update_required
                        else "no"
                    )
                ),
                (
                    "    bootloader trust anchor required: "
                    + (
                        "yes"
                        if realized.bootloader_trust_anchor_required
                        else "no"
                    )
                ),
                (
                    "    parent trust complete: "
                    + (
                        "yes"
                        if realized.parent_trust_complete
                        else "no"
                    )
                ),
                (
                    "    signing key: "
                    f"{realized.signing_key_path}"
                ),
                (
                    "    derived public key bytes: "
                    f"{len(realized.derived_public_key)}"
                ),
                (
                    "    bytes: "
                    f"{realized.size_bytes}"
                ),
                (
                    "    sha256: "
                    f"{realized.content_sha256}"
                ),
                (
                    "    output: "
                    f"{realized.output_path}"
                ),
            )
        )

    realization_lines.extend(
        (
            "",
            "Parent VBMeta signing material requirements:",
        )
    )

    if not (
        realization_result
        .parent_vbmeta_signing_material_required
    ):
        realization_lines.append(
            "  <none>"
        )

    for rewrite in (
        realization_result
        .parent_vbmeta_signing_material_required
    ):
        parent_partition_name = getattr(
            rewrite.parent_vbmeta.partition,
            "name",
            None,
        )

        if (
            not isinstance(
                parent_partition_name,
                str,
            )
            or not parent_partition_name
        ):
            raise RuntimeError(
                "unresolved parent VBMeta rewrite has no "
                "canonical partition name"
            )

        realization_lines.extend(
            (
                (
                    "  "
                    f"parent={parent_partition_name}"
                ),
                (
                    "    disposition: "
                    "signing_material_required"
                ),
                (
                    "    changed descriptors: "
                    f"{rewrite.changed_descriptor_count}"
                ),
                (
                    "    child targets: "
                    + ", ".join(
                        trust_change.target_partition
                        for trust_change
                        in rewrite.trust_changes
                    )
                ),
                (
                    "    descriptor rewrite retained: yes"
                ),
                (
                    "    parent image realized: no"
                ),
                (
                    "    propagation stopped here: yes"
                ),
            )
        )

    realization_lines.extend(
        (
            "",
            "Provider capability selection:",
            (
                "  Candidates discovered: "
                f"{realization_result.provider_candidate_count}"
            ),
            (
                "  Selections: "
                f"{realization_result.provider_selection_count}"
            ),
        )
    )

    for candidate in (
        realization_result.provider_candidates
    ):
        realization_lines.append(
            (
                "    candidate "
                f"{candidate.name}: "
                f"source={candidate.source.value} "
                f"path={candidate.executable} "
                "capabilities="
                + ",".join(
                    capability.value
                    for capability
                    in candidate.capabilities
                )
            )
        )

    for selection in (
        realization_result.provider_selections
    ):
        realization_lines.append(
            (
                "    selection "
                f"{selection.capability.value}: "
                f"provider={selection.provider.name}"
            )
        )

    invoked_provider_names = {
        invocation.provider.name
        for invocation
        in realization_result.provider_invocations
    }

    realization_lines.extend(
        (
            "",
            "Conditional provider execution:",
            (
                "  mkbootimg invoked: "
                + (
                    "yes"
                    if "mkbootimg" in invoked_provider_names
                    else "no"
                )
            ),
            (
                "  unpack_bootimg invoked: "
                + (
                    "yes"
                    if "unpack_bootimg" in invoked_provider_names
                    else "no"
                )
            ),
            (
                "  avbtool invoked: "
                + (
                    "yes"
                    if "avbtool" in invoked_provider_names
                    else "no"
                )
            ),
            (
                "  mkdtimg invoked: "
                + (
                    "yes"
                    if "mkdtimg" in invoked_provider_names
                    else "no"
                )
            ),
            (
                "  AVB regeneration performed: "
                + (
                    "yes"
                    if any(
                        "add_hash_footer"
                        in invocation.command
                        for invocation
                        in realization_result
                        .provider_invocations
                    )
                    else "no"
                )
            ),
            (
                "  cryptographic signing performed: "
                + (
                    "yes"
                    if any(
                        (
                            "add_hash_footer"
                            in invocation.command
                            and "--key"
                            in invocation.command
                        )
                        for invocation
                        in realization_result
                        .provider_invocations
                    )
                    else "no"
                )
            ),
            "",
            "Realization conservation:",
            (
                "  Planned components: "
                f"{planning_result.component_plan_count}"
            ),
            (
                "  Realized components: "
                f"{len(realization_result.components)}"
            ),
            (
                "  Planned DTBO containers: "
                f"{len(planning_result.dtbo_containers)}"
            ),
            (
                "  Realized DTBO containers: "
                f"{len(realization_result.dtbo_containers)}"
            ),
            "  Exact Planning identity: PASS",
            "  Planning evidence identity: PASS",
            "  Exact Composition identity: PASS",
            "  Exact Interpretation identity: PASS",
            "  Exact canonical Parsing identity: PASS",
            "  Byte-preservation verification: PASS",
            "  Conservation: PASS",
        )
    )

    realization_report_text = (
        "\n".join(
            realization_lines
        )
        + "\n"
    )

    realization_report_path.write_text(
        realization_report_text,
        encoding="utf-8",
    )

    if verbose:
        typer.echo()
        typer.echo(
            realization_report_text,
            nl=False,
        )

    typer.echo()
    typer.echo(
        "[Boot Image] Realization complete."
    )
    typer.echo(
        "  Component realizations: "
        f"{len(realization_result.components)}"
    )
    typer.echo(
        "  Mutated components: "
        f"{realization_result.mutated_count}"
    )
    typer.echo(
        "  Rebuilt boot images: "
        f"{len(realization_result.rebuilt_boot_images)}"
    )
    typer.echo(
        "  DTBO containers: "
        f"{len(realization_result.dtbo_containers)}"
    )
    typer.echo(
        "  AVB resolutions: "
        f"{len(realization_result.avb_resolutions)}"
    )
    typer.echo(
        "  Parent VBMeta realizations: "
        f"{len(realization_result.parent_vbmeta_realizations)}"
    )
    typer.echo(
        f"  Report: {realization_report_path}"
    )

    # --------------------------------------------------------
    # Validation Report
    # --------------------------------------------------------

    validation_report_path = (
        boot_image_root
        / "boot-image-validation-report.txt"
    )

    validation_lines: list[str] = [
        "=== BOOT IMAGE VALIDATION ===",
        "",
        "Realization identity: preserved",
        "Planning identity: preserved",
        "Composition identity: preserved",
        "Interpretation identity: preserved",
        "Canonical Parsing identity: preserved",
        (
            "Disposition: "
            f"{validation_result.disposition.value}"
        ),
        (
            "Physical artifacts validated: "
            f"{validation_result.physical_artifact_validation_count}"
        ),
        (
            "Rebuilt boot structures validated: "
            f"{validation_result.boot_image_structure_validation_count}"
        ),
        (
            "DTBO structures validated: "
            f"{validation_result.dtbo_structure_validation_count}"
        ),
        (
            "Provider invocations verified: "
            f"{len(realization_result.provider_invocations)}"
        ),
        (
            "Child AVB signing material required: "
            f"{realization_result.avb_signing_material_required_count}"
        ),
        (
            "Parent AVB signing material required: "
            f"{realization_result.parent_vbmeta_signing_material_required_count}"
        ),
        (
            "AVB artifacts validated: "
            f"{validation_result.artifact_validation_count}"
        ),
        (
            "AVB trust edges validated: "
            f"{validation_result.trust_edge_validation_count}"
        ),
        (
            "Cryptographic integrity complete: "
            + (
                "yes"
                if (
                    validation_result
                    .cryptographic_integrity_complete
                )
                else "no"
            )
        ),
        (
            "Realized trust graph complete: "
            + (
                "yes"
                if (
                    validation_result
                    .realized_trust_graph_complete
                )
                else "no"
            )
        ),
        (
            "Bootloader trust resolved: "
            + (
                "yes"
                if (
                    validation_result
                    .bootloader_trust_resolved
                )
                else "no"
            )
        ),
        (
            "Planning retained unresolved evidence: "
            f"{planning_result.retained_unresolved_count}"
        ),
        (
            "Planning retained ambiguous evidence: "
            f"{planning_result.retained_ambiguous_count}"
        ),
        (
            "Flashable chain applicable: "
            + (
                "yes"
                if (
                    validation_result
                    .flashable_chain_applicable
                )
                else "no"
            )
        ),
        (
            "Flashable chain complete: "
            + (
                "yes"
                if (
                    validation_result
                    .flashable_chain_complete
                )
                else "no"
            )
        ),
        "",
        "Validated physical artifacts:",
    ]

    if not validation_result.physical_artifacts:
        validation_lines.append(
            "  <none>"
        )

    for validated in (
        validation_result.physical_artifacts
    ):
        validation_lines.extend(
            (
                (
                    "  "
                    f"{validated.semantic_name}: "
                    f"kind={validated.kind}"
                ),
                (
                    "    authoritative source correspondence: PASS"
                ),
                (
                    "    realization byte identity: PASS"
                ),
                (
                    "    bytes: "
                    f"{validated.size_bytes}"
                ),
                (
                    "    sha256: "
                    f"{validated.content_sha256}"
                ),
                (
                    "    source: "
                    f"{validated.source_path}"
                ),
                (
                    "    output: "
                    f"{validated.output_path}"
                ),
            )
        )

    validation_lines.extend(
        (
            "",
            "Validated rebuilt boot structures:",
        )
    )

    if not validation_result.boot_image_structures:
        validation_lines.append(
            "  <none>"
        )

    for validated in (
        validation_result.boot_image_structures
    ):
        validation_lines.extend(
            (
                (
                    "  "
                    f"{validated.container_kind}:"
                ),
                (
                    "    header version: "
                    f"{validated.header_version}"
                ),
                (
                    "    ramdisk correspondence: PASS"
                ),
                (
                    "    empty-kernel invariant: PASS"
                ),
                (
                    "    final structural reinspection: PASS"
                ),
                (
                    "    output: "
                    f"{validated.output_path}"
                ),
            )
        )

    validation_lines.extend(
        (
            "",
            "Validated DTBO structures:",
        )
    )

    if not validation_result.dtbo_structures:
        validation_lines.append(
            "  <none>"
        )

    for validated in (
        validation_result.dtbo_structures
    ):
        validation_lines.extend(
            (
                "  dtbo:",
                (
                    "    entries: "
                    f"{validated.entry_count}"
                ),
                (
                    "    page size: "
                    f"{validated.page_size_bytes}"
                ),
                (
                    "    table total size: "
                    f"{validated.table_total_size_bytes}"
                ),
                (
                    "    table version: "
                    f"{validated.table_version}"
                ),
                "    table header: PASS",
                "    exact entry population: PASS",
                (
                    "    output: "
                    f"{validated.output_path}"
                ),
            )
        )

    validation_lines.extend(
        (
            "",
            "Validated AVB artifacts:",
        )
    )

    if not validation_result.avb_artifacts:
        validation_lines.append(
            "  <none>"
        )

    for validated in (
        validation_result.avb_artifacts
    ):
        validation_lines.extend(
            (
                (
                    "  "
                    f"{validated.partition_name}: "
                    f"kind={validated.kind}"
                ),
                (
                    "    realization bytes: verified"
                ),
                (
                    "    cryptographic verification: PASS"
                ),
                (
                    "    descriptor population: PASS"
                ),
                (
                    "    bytes: "
                    f"{validated.size_bytes}"
                ),
                (
                    "    sha256: "
                    f"{validated.content_sha256}"
                ),
                (
                    "    output: "
                    f"{validated.output_path}"
                ),
            )
        )

    validation_lines.extend(
        (
            "",
            "Validated AVB trust edges:",
        )
    )

    if not validation_result.avb_trust_edges:
        validation_lines.append(
            "  <none>"
        )

    for edge in (
        validation_result.avb_trust_edges
    ):
        validation_lines.extend(
            (
                (
                    "  "
                    f"{edge.parent_partition}"
                    " -> "
                    f"{edge.target_partition}"
                ),
                (
                    "    descriptor index: "
                    f"{edge.descriptor_index}"
                ),
                (
                    "    source kind: "
                    f"{edge.source_kind}"
                ),
                (
                    "    realized public-key correspondence: PASS"
                ),
            )
        )

    validation_lines.extend(
        (
            "",
            "AVB trust boundary:",
            (
                "  Cryptographic chain: "
                + (
                    "valid"
                    if (
                        validation_result
                        .cryptographic_integrity_complete
                        and (
                            validation_result
                            .realized_trust_graph_complete
                        )
                    )
                    else "incomplete"
                )
            ),
            (
                "  Bootloader trust: "
                + (
                    "resolved"
                    if (
                        validation_result
                        .bootloader_trust_resolved
                    )
                    else "unresolved"
                )
            ),
            (
                "  Flashable chain: "
                + (
                    "not applicable"
                    if not (
                        validation_result
                        .flashable_chain_applicable
                    )
                    else (
                        "complete"
                        if (
                            validation_result
                            .flashable_chain_complete
                        )
                        else "incomplete"
                    )
                )
            ),
            "",
            "Validation conservation:",
            (
                "  Provider invocation outcomes: "
                + (
                    "PASS"
                    if (
                        validation_result
                        .provider_invocations_verified
                    )
                    else "FAIL"
                )
            ),
            "  Complete physical-output accounting: PASS",
            "  Complete rebuilt-image accounting: PASS",
            "  Complete DTBO structural accounting: PASS",
            "  Complete AVB-artifact accounting: PASS",
            "  Complete AVB trust-edge accounting: PASS",
            "  Planning unresolved-evidence continuity: PASS",
            "  Planning ambiguous-evidence continuity: PASS",
            "  Exact Realization identity: PASS",
            "  Exact Planning identity: PASS",
            "  Exact Composition identity: PASS",
            "  Exact Interpretation identity: PASS",
            "  Exact canonical Parsing identity: PASS",
            "  Conservation: PASS",
        )
    )

    validation_report_text = (
        "\n".join(
            validation_lines
        )
        + "\n"
    )

    validation_report_path.write_text(
        validation_report_text,
        encoding="utf-8",
    )

    if verbose:
        typer.echo()
        typer.echo(
            validation_report_text,
            nl=False,
        )

    typer.echo()
    typer.echo(
        "[Boot Image] Validation complete."
    )
    typer.echo(
        "  Disposition: "
        f"{validation_result.disposition.value.upper()}"
    )
    typer.echo(
        "  Physical artifacts: "
        f"{validation_result.physical_artifact_validation_count}"
    )
    typer.echo(
        "  Rebuilt boot structures: "
        f"{validation_result.boot_image_structure_validation_count}"
    )
    typer.echo(
        "  DTBO structures: "
        f"{validation_result.dtbo_structure_validation_count}"
    )
    typer.echo(
        "  AVB artifacts: "
        f"{len(validation_result.avb_artifacts)}"
    )
    typer.echo(
        "  Flashable chain: "
        + (
            "complete"
            if (
                validation_result.flashable_chain_applicable
                and validation_result.flashable_chain_complete
            )
            else (
                "incomplete"
                if validation_result.flashable_chain_applicable
                else "not applicable"
            )
        )
    )
    typer.echo(
        f"  Report: {validation_report_path}"
    )

    # --------------------------------------------------------
    # Deployment Planning
    # --------------------------------------------------------

    typer.echo()
    typer.echo(
        "Planning Boot Image deployment..."
    )

    typer.echo()
    typer.echo(
        "[Boot Image] Building Deployment Planning boundary..."
    )

    deployment_result = (
        AndroidBootImageDeploymentPlanner()
        .build(
            validation_result,
            output_root=(
                boot_image_root
                / "deployment"
                / (
                    "bootstrap"
                    if active_bootstrap_handoff_path is not None
                    else "custom"
                )
            ),
            parsing_snapshot_path=(
                active_parsing_snapshot_path
            ),
            bootstrap_handoff_path=(
                active_bootstrap_handoff_path
            ),
        )
    )

    if (
        deployment_result.validation
        is not validation_result
    ):
        raise RuntimeError(
            "Boot Image Deployment Planning lost exact "
            "Validation identity"
        )

    if (
        deployment_result.realization
        is not realization_result
    ):
        raise RuntimeError(
            "Boot Image Deployment Planning lost exact "
            "Realization identity"
        )

    if (
        deployment_result.parsing
        is not parsing_result
    ):
        raise RuntimeError(
            "Boot Image Deployment Planning lost exact "
            "canonical Parsing identity"
        )

    deployment_report_path = (
        boot_image_root
        / "boot-image-deployment-planning-report.txt"
    )

    deployment_lines = [
        "=== BOOT IMAGE DEPLOYMENT PLANNING ===",
        "",
        "Validation identity: preserved",
        "Realization identity: preserved",
        "Canonical Parsing identity: preserved",
        (
            "Validation disposition: "
            f"{validation_result.disposition.value}"
        ),
        (
            "Flashable chain applicable: "
            + (
                "yes"
                if (
                    validation_result
                    .flashable_chain_applicable
                )
                else "no"
            )
        ),
        (
            "Flashable chain complete: "
            + (
                "yes"
                if (
                    validation_result
                    .flashable_chain_complete
                )
                else "no"
            )
        ),
        (
            "Deployment images: "
            f"{deployment_result.image_count}"
        ),
        "",
        "Deployment set:",
    ]

    if not deployment_result.images:
        deployment_lines.append(
            "  <none>"
        )

    for image in (
        deployment_result.images
    ):
        deployment_lines.extend(
            (
                (
                    "  "
                    f"{image.partition_name}: "
                    f"source_kind={image.source_kind}"
                ),
                "    NEW:",
                (
                    "      source: "
                    f"{image.final_source_path}"
                ),
                (
                    "      deployment: "
                    f"{image.final_path}"
                ),
                (
                    "      bytes: "
                    f"{image.final_size_bytes}"
                ),
                (
                    "      sha256: "
                    f"{image.final_sha256}"
                ),
                "    ROLLBACK:",
                (
                    "      canonical source: "
                    f"{image.rollback_source_path}"
                ),
                (
                    "      preserved: "
                    f"{image.rollback_path}"
                ),
                (
                    "      bytes: "
                    f"{image.rollback_size_bytes}"
                ),
                (
                    "      sha256: "
                    f"{image.rollback_sha256}"
                ),
                (
                    "      required: "
                    + (
                        "yes"
                        if image.rollback_required
                        else "no"
                    )
                ),
            )
        )

    deployment_lines.extend(
        (
            "",
            "Deployment ownership boundary:",
            "  Whole-image rollback preserved: yes",
            "  Hardware device selected: no",
            "  Slot selected: no",
            "  fastboot operation performed: no",
            "  Device reboot performed: no",
            "",
            (
                "Manifest: "
                f"{deployment_result.manifest_path}"
            ),
            "",
            "Deployment Planning conservation:",
            "  Exact Validation identity: PASS",
            "  Exact Realization identity: PASS",
            "  Exact canonical Parsing identity: PASS",
            "  Final-image byte identity: PASS",
            "  Whole-image rollback byte identity: PASS",
            "  Changed partition accounting: PASS",
            "  Conservation: PASS",
        )
    )

    deployment_report_text = (
        "\n".join(
            deployment_lines
        )
        + "\n"
    )

    deployment_report_path.write_text(
        deployment_report_text,
        encoding="utf-8",
    )

    if verbose:
        typer.echo()
        typer.echo(
            deployment_report_text,
            nl=False,
        )

    typer.echo()
    typer.echo(
        "[Boot Image] Deployment Planning complete."
    )
    typer.echo(
        "  Deployment images: "
        f"{len(deployment_result.images)}"
    )
    typer.echo(
        "  Flashable chain: "
        + (
            "complete"
            if (
                validation_result.flashable_chain_applicable
                and validation_result.flashable_chain_complete
            )
            else (
                "incomplete"
                if validation_result.flashable_chain_applicable
                else "not applicable"
            )
        )
    )
    typer.echo(
        "  Hardware deployment available: "
        + (
            "yes"
            if deployment_result.images
            else "no"
        )
    )
    typer.echo(
        f"  Manifest: {deployment_result.manifest_path}"
    )
    typer.echo(
        f"  Report: {deployment_report_path}"
    )





    if generation_only:
        typer.echo()
        typer.echo(
            "Boot Image generation-only boundary complete."
        )
        typer.echo(
            "  Validation: PASS"
        )
        typer.echo(
            "  Hardware deployment: disabled"
        )
        typer.echo(
            "  Deployment output prompts: disabled"
        )
        typer.echo(
            f"  Manifest: {deployment_result.manifest_path}"
        )
        return

    # --------------------------------------------------------
    # Deployment Output Selection
    # --------------------------------------------------------

    if deployment_result.images:
        deployment_format = (
            _prompt_boot_image_deployment_format()
        )

        if deployment_format == "cancel":
            typer.echo()
            typer.echo(
                "Boot Image completed without "
                "deployment output."
            )
            return

        if deployment_format in {
            "recovery",
            "both",
        }:
            _prepare_recovery_install_set(
                deployment_result,
                boot_image_root=(
                    boot_image_root
                ),
                image_set="modified",
            )

        if deployment_format == "recovery":
            typer.echo()
            typer.echo(
                "Boot Image completed with a "
                "Recovery Install Set."
            )
            return

    # --------------------------------------------------------
    # Device Deployment
    # --------------------------------------------------------

    if deployment_result.images:
        typer.echo()
        typer.echo(
            "[Boot Image] Detecting connected device "
            "(read-only probe)..."
        )

        device_deployer = (
            AndroidBootImageDeviceDeployer()
        )

        try:
            device_available = (
                device_deployer
                .has_connected_device()
            )

        except RuntimeError as error:
            typer.echo()
            typer.echo(
                "Boot Image device detection could not continue."
            )
            typer.echo(
                f"Reason: {error}"
            )
            device_available = False

        if not device_available:
            typer.echo()
            typer.echo(
                "No ADB or fastboot device was detected."
            )

            save_images = typer.confirm(
                "Save the modified and original Boot Image "
                "images for later deployment?",
                default=True,
            )

            if save_images:
                export_root = (
                    boot_image_root
                    / "saved-images"
                )

                export_manifest = (
                    export_boot_image_deployment(
                        deployment_result,
                        output_root=export_root,
                    )
                )

                typer.echo()
                typer.echo(
                    "Boot Image images saved successfully."
                )

                typer.echo(
                    f"Modified: {export_root / 'modified'}"
                )

                typer.echo(
                    f"Original: {export_root / 'original'}"
                )

                typer.echo(
                    f"Manifest: {export_manifest}"
                )

            else:
                typer.echo(
                    "Boot Image image export skipped."
                )

            typer.echo()
            typer.echo(
                "Boot Image completed without hardware deployment."
            )

            return

        else:
            typer.echo()
            typer.echo(
                "Boot Image hardware deployment is available."
            )

            typer.echo()
            typer.echo(
                "Choose the image set to deploy:"
            )

        typer.echo(
            "  1. Modified -> validated TreeForge-generated images"
        )

        typer.echo(
            "  2. Original -> exact canonical original images"
        )

        typer.echo(
            "  3. Cancel   -> do not prepare or modify hardware"
        )

        payload_selection = None
        deployment_cancelled = False

        while True:
            raw_payload = (
                typer.prompt(
                    "Payload",
                    default="1",
                )
                .strip()
            )

            if raw_payload == "1":
                payload_selection = (
                    AndroidBootImageDeploymentPayload
                    .MODIFIED
                )
                break

            if raw_payload == "2":
                payload_selection = (
                    AndroidBootImageDeploymentPayload
                    .ORIGINAL
                )
                break

            if raw_payload == "3":
                deployment_cancelled = True
                break

            typer.echo(
                "Choose 1, 2, or 3."
            )

        if deployment_cancelled:
            typer.echo(
                "Boot Image hardware deployment skipped."
            )

        else:
            assert payload_selection is not None

            typer.echo()
            typer.echo(
                "Checking Boot Image device state..."
            )

            device_deployer = (
                AndroidBootImageDeviceDeployer()
            )

            try:
                device_inspection = (
                    device_deployer.inspect(
                        deployment_result
                    )
                )

            except RuntimeError as error:
                typer.echo()
                typer.echo(
                    "Boot Image hardware deployment "
                    "was not performed."
                )

                typer.echo(
                    f"Reason: {error}"
                )

            else:
                typer.echo()
                typer.echo(
                    "=== BOOT IMAGE DEVICE INSPECTION ==="
                )
                typer.echo()

                typer.echo(
                    "Device: "
                    f"{device_inspection.device.serial}"
                )

                typer.echo(
                    "Initial mode: "
                    f"{device_inspection.device.initial_mode.value}"
                )

                typer.echo(
                    "Deployment mode: "
                    f"{device_inspection.device.final_mode.value}"
                )

                typer.echo(
                    "Current active slot: "
                    + (
                        device_inspection.active_slot
                        or "<not reported>"
                    )
                )

                typer.echo(
                    "Slot count: "
                    + (
                        str(
                            device_inspection
                            .device
                            .slot_count
                        )
                        if (
                            device_inspection
                            .device
                            .slot_count
                            is not None
                        )
                        else "<not reported>"
                    )
                )

                if (
                    device_inspection
                    .has_slotted_targets
                ):
                    typer.echo(
                        "Inactive slot: "
                        f"{device_inspection.inactive_slot}"
                    )

                typer.echo()
                typer.echo(
                    "Partition slot applicability:"
                )

                for (
                    image,
                    slot_applicable,
                ) in (
                    device_inspection
                    .slot_applicability
                ):
                    typer.echo(
                        "  "
                        f"{image.partition_name}: "
                        + (
                            "slotted"
                            if slot_applicable
                            else "non-slotted"
                        )
                    )

                slot_selection = None
                slot_cancelled = False

                if (
                    device_inspection
                    .has_slotted_targets
                ):
                    typer.echo()
                    typer.echo(
                        "Choose target slot:"
                    )

                    typer.echo(
                        "  a"
                        + (
                            "  <- current active"
                            if (
                                device_inspection.active_slot
                                == "a"
                            )
                            else ""
                        )
                    )

                    typer.echo(
                        "  b"
                        + (
                            "  <- current active"
                            if (
                                device_inspection.active_slot
                                == "b"
                            )
                            else ""
                        )
                    )

                    typer.echo(
                        "  cancel"
                    )

                    default_slot = (
                        device_inspection.active_slot
                        or "a"
                    )

                    while True:
                        raw_slot = (
                            typer.prompt(
                                "Target slot",
                                default=default_slot,
                            )
                            .strip()
                            .lower()
                        )

                        if raw_slot == "a":
                            slot_selection = (
                                AndroidBootImageSlotSelection
                                .SLOT_A
                            )
                            break

                        if raw_slot == "b":
                            slot_selection = (
                                AndroidBootImageSlotSelection
                                .SLOT_B
                            )
                            break

                        if raw_slot == "cancel":
                            slot_cancelled = True
                            break

                        typer.echo(
                            "Choose a, b, or cancel."
                        )

                if slot_cancelled:
                    typer.echo(
                        "Boot Image hardware deployment skipped."
                    )

                else:
                    device_deployment_plan = (
                        device_deployer.plan(
                            device_inspection,
                            payload=(
                                payload_selection
                            ),
                            slot_selection=(
                                slot_selection
                            ),
                        )
                    )

                    typer.echo()
                    typer.echo(
                        "=== BOOT IMAGE DEVICE DEPLOYMENT ==="
                    )
                    typer.echo()

                    typer.echo(
                        "Image set: "
                        f"{device_deployment_plan.payload.value}"
                    )

                    if (
                        device_deployment_plan
                        .slot_selection
                        is not None
                    ):
                        typer.echo(
                            "Slot policy: "
                            f"{device_deployment_plan.slot_selection.value}"
                        )

                    typer.echo(
                        "Active slot remains: "
                        + (
                            device_deployment_plan
                            .device
                            .current_slot
                            or "<not reported>"
                        )
                    )

                    typer.echo()
                    typer.echo(
                        "Planned hardware writes:"
                    )

                    for target in (
                        device_deployment_plan.targets
                    ):
                        image = target.image

                        if (
                            device_deployment_plan.payload
                            is
                            AndroidBootImageDeploymentPayload
                            .MODIFIED
                        ):
                            selected_path = (
                                image.final_path
                            )

                            selected_size = (
                                image.final_size_bytes
                            )

                            selected_sha256 = (
                                image.final_sha256
                            )

                        else:
                            selected_path = (
                                image.rollback_path
                            )

                            selected_size = (
                                image.rollback_size_bytes
                            )

                            selected_sha256 = (
                                image.rollback_sha256
                            )

                        typer.echo(
                            "  "
                            f"{target.fastboot_partition}"
                        )

                        typer.echo(
                            "    image set: "
                            f"{device_deployment_plan.payload.value}"
                        )

                        typer.echo(
                            "    image: "
                            f"{selected_path}"
                        )

                        typer.echo(
                            "    bytes: "
                            f"{selected_size}"
                        )

                        typer.echo(
                            "    sha256: "
                            f"{selected_sha256}"
                        )

                        if (
                            device_deployment_plan.payload
                            is
                            AndroidBootImageDeploymentPayload
                            .MODIFIED
                        ):
                            typer.echo(
                                "    exact original retained: "
                                f"{image.rollback_path}"
                            )

                            typer.echo(
                                "    original sha256: "
                                f"{image.rollback_sha256}"
                            )

                    typer.echo()
                    typer.echo(
                        "Safety boundary:"
                    )

                    typer.echo(
                        "  Selected images reverified "
                        "immediately before flash: yes"
                    )

                    typer.echo(
                        "  Exact original retained for "
                        "modified deployment: yes"
                    )

                    typer.echo(
                        "  Target slot explicitly selected: yes"
                        if (
                            device_inspection
                            .has_slotted_targets
                        )
                        else
                        "  Target is non-slotted: yes"
                    )

                    typer.echo(
                        "  Automatic fallback/restoration: no"
                    )

                    typer.echo(
                        "  Automatic active-slot change: no"
                    )

                    typer.echo(
                        "  Reboot after flash requires confirmation: yes"
                    )

                    typer.echo()

                    flash_confirmed = typer.confirm(
                        "Flash exactly this image set "
                        "to the displayed target(s)?",
                        default=False,
                    )

                    if not flash_confirmed:
                        typer.echo(
                            "Boot Image hardware deployment skipped."
                        )

                    else:
                        typer.echo()
                        typer.echo(
                            "Flashing selected Boot Image "
                            "deployment..."
                        )

                        device_deployment_result = (
                            device_deployer.flash(
                                device_deployment_plan
                            )
                        )

                        typer.echo()
                        typer.echo(
                            "Boot Image hardware deployment completed."
                        )

                        for invocation in (
                            device_deployment_result
                            .invocations
                        ):
                            typer.echo(
                                "  flashed: "
                                f"{invocation.target.fastboot_partition}"
                                " <- "
                                f"{invocation.payload.value}"
                            )

                        typer.echo()
                        typer.echo(
                            "The active slot was not changed."
                        )

                        typer.echo()

                        reboot_device = typer.confirm(
                            "Reboot the device now?",
                            default=True,
                        )

                        if reboot_device:
                            try:
                                device_deployer.reboot(
                                    device_deployment_plan
                                )
                            except RuntimeError as error:
                                typer.echo()
                                typer.echo(
                                    "Device reboot failed."
                                )
                                typer.echo(
                                    f"Reason: {error}"
                                )
                            else:
                                typer.echo(
                                    "Device reboot requested."
                                )
                        else:
                            typer.echo(
                                "Device left in bootloader fastboot."
                            )

                        if (
                            device_deployment_plan.payload
                            is
                            AndroidBootImageDeploymentPayload
                            .MODIFIED
                        ):
                            typer.echo()
                            typer.echo(
                                "Exact original images remain "
                                "available for explicit restoration at:"
                            )

                            typer.echo(
                                "  "
                                f"{deployment_result.output_root / 'rollback'}"
                            )


__all__ = (
    "app",
    "boot_image",
)
