from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import typer

from treeforge.android.install.stage import (
    AndroidInstallBuild,
    AndroidInstallDeviceController,
    AndroidInstallError,
    AndroidInstallSelection,
    build_plan_payload,
    render_install_fastboot_info,
    render_preflight_report,
    resolve_install_build,
    validate_install_preflight,
    _write_json,
)
from treeforge.android.install.full_ab import (
    STOCK_LAYOUT,
    TREEFORGE_LAYOUT,
    build_full_ab_install_plan_payload,
    build_full_ab_plan,
    detect_install_layout,
    render_full_ab_fastboot_info,
    render_full_ab_preflight_report,
    validate_full_ab_preflight,
    validate_full_ab_manifest,
)

from treeforge.cli.repository_root import AOSP_ROOT


app = typer.Typer(
    help=(
        "Install one source-faithful Android image set "
        "with A/B physical boot-chain redundancy."
    ),
)


def _known_aosp_install_builds(
) -> tuple[
    tuple[str, AndroidInstallBuild],
    ...,
]:
    """
    Discover only TreeForge-managed/known AOSP product outputs.

    Factory-image inputs and arbitrary external product outputs are never
    searched for automatically. They remain explicit user-provided paths.
    """

    roots = (
        (
            "TreeForge AOSP",
            AOSP_ROOT
            / "out-treeforge"
            / "target"
            / "product",
        ),
        (
            "Google canonical AOSP",
            AOSP_ROOT
            / "out"
            / "target"
            / "product",
        ),
    )

    builds: list[
        tuple[str, AndroidInstallBuild]
    ] = []

    seen: set[Path] = set()

    for label, product_root in roots:
        if not product_root.is_dir():
            continue

        for product_out in sorted(
            (
                path
                for path in product_root.iterdir()
                if path.is_dir()
            ),
            key=lambda path: path.name,
        ):
            resolved = (
                product_out
                .expanduser()
                .resolve()
            )

            if resolved in seen:
                continue

            if not (
                resolved
                / "fastboot-info.txt"
            ).is_file():
                continue

            try:
                build = resolve_install_build(
                    resolved,
                    allow_discovery=False,
                )

            except (
                AndroidInstallError,
                FileNotFoundError,
                OSError,
            ):
                #
                # Do not advertise incomplete/invalid build outputs as
                # selectable Install sources.
                #
                continue

            seen.add(
                resolved
            )

            source_label = (
                "TreeForge AOSP"
                if (
                    label == "TreeForge AOSP"
                    or resolved.name.startswith(
                        "treeforge_"
                    )
                )
                else label
            )

            builds.append(
                (
                    source_label,
                    build,
                )
            )

    return tuple(
        builds
    )


def _select_install_build(
) -> AndroidInstallBuild:
    """
    Select one Install source when --input was omitted.

    Known AOSP outputs are discovered automatically. Factory images,
    copied builds, and arbitrary external product outputs are supplied
    through "Provide another input path".
    """

    candidates = (
        _known_aosp_install_builds()
    )

    typer.echo(
        "Detected install sources:"
    )
    typer.echo()

    for index, (
        label,
        build,
    ) in enumerate(
        candidates,
        1,
    ):
        typer.echo(
            f"  {index}. {label}"
        )
        typer.echo(
            f"     Device: {build.target_device}"
        )
        typer.echo(
            f"     {build.product_out}"
        )
        typer.echo()

    other_index = (
        len(candidates)
        + 1
    )

    typer.echo(
        f"  {other_index}. Provide another input path"
    )
    typer.echo(
        "     Factory image, image-*.zip, or another "
        "AOSP product output"
    )
    typer.echo()

    default_choice = (
        1
        if candidates
        else other_index
    )

    while True:
        raw = typer.prompt(
            "Select install source",
            default=str(
                default_choice
            ),
        ).strip()

        try:
            choice = int(
                raw,
                10,
            )

        except ValueError:
            typer.echo(
                "Enter one of the numbered choices.",
                err=True,
            )
            continue

        if (
            1
            <= choice
            <= other_index
        ):
            break

        typer.echo(
            "Enter one of the numbered choices.",
            err=True,
        )

    if choice <= len(
        candidates
    ):
        label, build = (
            candidates[
                choice - 1
            ]
        )

        typer.echo()
        typer.echo(
            f"Selected: {label}"
        )

        return build

    typer.echo()

    supplied = typer.prompt(
        "Install input path"
    ).strip()

    if not supplied:
        raise AndroidInstallError(
            "Install input path cannot be empty"
        )

    return resolve_install_build(
        Path(
            supplied
        ),
        allow_discovery=False,
    )


def _install_selection(
    *,
    device,
    wipe_userdata: bool,
) -> AndroidInstallSelection:
    if (
        device.slot_count != 2
        or device.current_slot
        not in {
            "a",
            "b",
        }
    ):
        raise AndroidInstallError(
            "Install requires exactly two A/B slots; "
            f"current-slot={device.current_slot!r}, "
            f"slot-count={device.slot_count!r}"
        )

    return AndroidInstallSelection(
        slot_argument=(
            device.current_slot
        ),
        display_name=(
            "Source-faithful A/B install"
        ),
        final_active_slot=(
            device.current_slot
        ),
        wipe_userdata=wipe_userdata,
    )


def _run_treeforge_full_ab_install(
    *,
    build: AndroidInstallBuild,
    controller: AndroidInstallDeviceController,
    device,
    super_size_bytes: int,
    install_root: Path,
    plan_path: Path,
    manifest_path: Path,
    preflight_path: Path,
    report_path: Path,
) -> None:
    typer.echo()
    typer.echo(
        "=== TREEFORGE FULL A/B INSTALL ==="
    )
    typer.echo(
        f"Layout: {TREEFORGE_LAYOUT}"
    )
    typer.echo(
        f"Physical super: {super_size_bytes:,} bytes"
    )
    typer.echo(
        "Physical boot-chain: MIRROR A + B"
    )
    typer.echo(
        "Dynamic logical partitions: COMPLETE A + B"
    )
    typer.echo(
        "Post-install active-slot change: NO"
    )
    typer.echo(
        "Post-install Android reboot: ASK"
    )

    wipe_userdata = typer.confirm(
        "Wipe userdata and metadata?",
        default=False,
    )

    if wipe_userdata:
        conditional_wipe_partitions = {
            operation.partition
            for operation in build.operations
            if (
                operation.conditional
                and operation.partition
                is not None
            )
        }

        required = {
            "userdata",
            "metadata",
        }

        missing = (
            required
            - conditional_wipe_partitions
        )

        if missing:
            raise AndroidInstallError(
                "selected source does not declare "
                "required conditional wipe operations "
                "for: "
                + ", ".join(
                    sorted(missing)
                )
            )

    selection = _install_selection(
        device=device,
        wipe_userdata=wipe_userdata,
    )

    slot_applicability: dict[
        str,
        bool | None,
    ] = {}

    for image in build.images:
        if (
            image.partition
            in slot_applicability
        ):
            continue

        slot_applicability[
            image.partition
        ] = controller.has_slot(
            serial=device.serial,
            partition=image.partition,
        )

    full_ab_root = (
        install_root
        / "full-ab-v1"
    )

    plan = build_full_ab_plan(
        repository_root=Path.cwd(),
        build=build,
        super_size_bytes=super_size_bytes,
        output_root=full_ab_root,
    )

    preflight = validate_full_ab_preflight(
        build=build,
        device=device,
        slot_applicability=(
            slot_applicability
        ),
        plan=plan,
    )

    fastboot_info_text = (
        render_full_ab_fastboot_info(
            build=build,
            slot_applicability=(
                slot_applicability
            ),
        )
    )

    manifest_validation = (
        validate_full_ab_manifest(
            build=build,
            slot_applicability=(
                slot_applicability
            ),
            fastboot_info_text=(
                fastboot_info_text
            ),
        )
    )

    preflight[
        "manifest_validation"
    ] = manifest_validation

    manifest_path.write_text(
        fastboot_info_text,
        encoding="utf-8",
    )

    preflight_path.write_text(
        render_full_ab_preflight_report(
            build=build,
            device=device,
            selection=selection,
            slot_applicability=(
                slot_applicability
            ),
            preflight=preflight,
            plan=plan,
        ),
        encoding="utf-8",
    )

    _write_json(
        plan_path,
        build_full_ab_install_plan_payload(
            build=build,
            device=device,
            selection=selection,
            slot_applicability=(
                slot_applicability
            ),
            preflight=preflight,
            plan=plan,
            manifest_path=manifest_path,
        ),
    )

    data_action = (
        "WIPE"
        if wipe_userdata
        else "PRESERVE"
    )

    typer.echo()
    typer.echo(
        "=== FINAL INSTALL PLAN ==="
    )
    typer.echo(
        "Storage layout: TREEFORGE FULL A/B V1"
    )
    typer.echo(
        f"Super: {plan.super_size_bytes:,} bytes"
    )
    typer.echo(
        f"Group A: {plan.group_size_bytes:,} bytes"
    )
    typer.echo(
        f"Group B: {plan.group_size_bytes:,} bytes"
    )
    typer.echo(
        f"Per-slot payload: "
        f"{plan.slot_payload_bytes:,} bytes"
    )
    typer.echo(
        f"Per-slot headroom: "
        f"{plan.slot_headroom_bytes:,} bytes"
    )
    typer.echo(
        "Full dynamic slot A: YES"
    )
    typer.echo(
        "Full dynamic slot B: YES"
    )
    typer.echo(
        "Physical slotted images: A + B"
    )
    typer.echo(
        "Shared super realizations: 1"
    )
    typer.echo(
        f"Userdata: {data_action}"
    )
    typer.echo(
        f"Metadata: {data_action}"
    )
    typer.echo(
        "Post-install active-slot change: NO"
    )
    typer.echo(
        "Post-install Android reboot: ASK"
    )

    typer.echo()
    typer.echo(
        "Dynamic images:"
    )

    for partition in plan.partitions:
        typer.echo(
            "  "
            f"{partition.base_name}_a + "
            f"{partition.base_name}_b <- "
            f"{partition.image.image_name}"
        )

    typer.echo()
    typer.echo(
        "Projection validation:"
    )
    typer.echo(
        "  Snapshot state safe: YES"
    )
    typer.echo(
        "  Full logical partitions: "
        f"{preflight['full_dynamic_partition_count']}"
    )
    typer.echo(
        "  Synthetic secondary images: "
        f"{preflight['synthetic_secondary_dynamic_images']}"
    )
    typer.echo(
        "  Mirrored physical images: "
        f"{preflight['mirrored_physical_image_count']}"
    )
    typer.echo(
        "  update-super operations: 1"
    )
    typer.echo(
        "  Source flash semantics: PASS"
    )

    typer.echo()
    typer.echo(
        "Execution topology:"
    )
    typer.echo(
        "  1. Flash selected-slot physical images"
    )
    typer.echo(
        "  2. Mirror slotted physical images to other slot"
    )
    typer.echo(
        "  3. Enter fastbootd"
    )
    typer.echo(
        "  4. Apply TreeForge full-A/B super metadata once"
    )
    typer.echo(
        "  5. Flash six complete logical images to slot A"
    )
    typer.echo(
        "  6. Flash six complete logical images to slot B"
    )
    typer.echo(
        "  7. Stop in fastboot/fastbootd"
    )
    typer.echo(
        "  8. Offer Android reboot"
    )

    typer.echo()
    typer.echo(
        f"Generated manifest: {manifest_path}"
    )
    typer.echo(
        f"Generated super metadata: "
        f"{plan.super_empty_path}"
    )
    typer.echo(
        f"Plan: {plan_path}"
    )
    typer.echo(
        f"Preflight: {preflight_path}"
    )

    confirmed = typer.confirm(
        "Proceed with TreeForge full A/B flash?",
        default=False,
    )

    if not confirmed:
        report_path.write_text(
            (
                "TreeForge Install\n\n"
                "Status: CANCELLED\n"
                f"Mode: {TREEFORGE_LAYOUT}\n"
                "Flash performed: NO\n"
                f"Wipe requested: "
                f"{'YES' if wipe_userdata else 'NO'}\n"
                "Automatic Android reboot: NO\n"
            ),
            encoding="utf-8",
        )

        typer.echo(
            "Install cancelled. "
            "No partitions were flashed."
        )
        return

    #
    # The executor already knows how to stage super_empty.img,
    # execute flashall, preserve slot selection, and traverse
    # bootloader-fastboot <-> fastbootd.
    #
    # Substitute only TreeForge's generated LP metadata.
    #
    execution_build = replace(
        build,
        super_empty_path=(
            plan.super_empty_path
        ),
    )

    typer.echo()
    typer.echo(
        "Starting TreeForge full A/B install..."
    )

    try:
        result = controller.execute(
            build=execution_build,
            device=device,
            selection=selection,
            fastboot_info_text=(
                fastboot_info_text
            ),
        )

    except Exception as error:
        report_path.write_text(
            (
                "TreeForge Install\n\n"
                "Status: FAILED\n"
                f"Mode: {TREEFORGE_LAYOUT}\n"
                f"Build: {build.product_out}\n"
                f"Device: {device.serial}\n"
                f"Error: {error}\n"
                f"Wipe requested: "
                f"{'YES' if wipe_userdata else 'NO'}\n"
                "Automatic Android reboot: NO\n"
            ),
            encoding="utf-8",
        )

        typer.echo()
        typer.echo(
            f"Install failed: {error}",
            err=True,
        )
        typer.echo(
            "Device intentionally left in the "
            "fastboot domain where execution stopped.",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo()
    typer.echo(
        "TreeForge full A/B install "
        "completed successfully."
    )
    typer.echo(
        "Physical slotted images mirrored: A + B"
    )
    typer.echo(
        "Full logical slot A populated: YES"
    )
    typer.echo(
        "Full logical slot B populated: YES"
    )
    typer.echo(
        "Active slot preserved: "
        f"{result.final_active_slot.upper()}"
    )

    reboot_requested = typer.confirm(
        "Reboot to Android now?",
        default=False,
    )

    reboot_status = "NOT REQUESTED"
    reboot_error = None

    if reboot_requested:
        try:
            controller.reboot_android(
                serial=device.serial,
            )

            reboot_status = "REQUESTED"

        except Exception as error:
            reboot_status = "FAILED"
            reboot_error = str(error)

    report_lines = [
        "TreeForge Install",
        "",
        "Status: SUCCESS",
        f"Mode: {TREEFORGE_LAYOUT}",
        f"Build: {build.product_out}",
        f"Device: {device.serial}",
        (
            "Physical slotted images mirrored: YES"
        ),
        "Full dynamic slot A populated: YES",
        "Full dynamic slot B populated: YES",
        (
            "Independent A/B logical population: YES"
        ),
        (
            "Userdata preserved: "
            + (
                "NO"
                if wipe_userdata
                else "YES"
            )
        ),
        (
            "Metadata preserved: "
            + (
                "NO"
                if wipe_userdata
                else "YES"
            )
        ),
        (
            "Post-install active-slot change: NO"
        ),
        (
            "Active slot preserved: "
            f"{result.final_active_slot}"
        ),
        "Automatic Android reboot: NO",
        (
            "Post-install Android reboot requested: "
            + (
                "YES"
                if reboot_requested
                else "NO"
            )
        ),
        (
            "Post-install Android reboot command: "
            f"{reboot_status}"
        ),
    ]

    if reboot_error is not None:
        report_lines.append(
            "Post-install Android reboot error: "
            + reboot_error
        )

    report_path.write_text(
        "\n".join(
            report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    if reboot_error is not None:
        typer.echo(
            f"Android reboot failed: {reboot_error}",
            err=True,
        )
        raise typer.Exit(
            code=1
        )

    if not reboot_requested:
        typer.echo(
            "Device remains in fastboot/fastbootd."
        )

    typer.echo(
        f"Report: {report_path}"
    )


@app.callback(
    invoke_without_command=True,
)
def install(
    ctx: typer.Context,
    input_path: Path | None = typer.Option(
        None,
        "--input",
        file_okay=True,
        dir_okay=True,
        resolve_path=True,
        help=(
            "Explicit Android install input. May identify "
            "an AOSP product output, an extracted Google "
            "factory directory containing image-*.zip, or "
            "the inner image-*.zip directly. Without "
            "--input, TreeForge discovers known AOSP "
            "product outputs and presents an install-source "
            "selection."
        ),
    ),
) -> None:
    """
    Install one source-faithful Android image set.

    Slotted physical boot-chain images are mirrored to A and B.
    Dynamic-partition semantics remain source-defined.
    Shared super is realized exactly once when required.
    Userdata and metadata may be wiped by explicit user choice.
    The current slot remains selected.
    Android reboot is offered after a successful install.
    """

    if ctx.invoked_subcommand is not None:
        return

    install_root = (
        Path.cwd()
        / "output"
        / "install"
    ).resolve()

    install_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    plan_path = (
        install_root
        / "install-plan.json"
    )

    manifest_path = (
        install_root
        / "install-fastboot-info.txt"
    )

    stale_manifest_path = (
        install_root
        / "dual-slot-fastboot-info.txt"
    )

    if stale_manifest_path.exists():
        stale_manifest_path.unlink()

    preflight_path = (
        install_root
        / "device-preflight-report.txt"
    )

    report_path = (
        install_root
        / "install-report.txt"
    )

    typer.echo(
        "TreeForge Install"
    )
    typer.echo(
        "Mode: automatic storage-layout policy"
    )
    typer.echo(
        "Physical boot-chain: mirror A + B"
    )
    typer.echo(
        "Dynamic partitions: selected after "
        "device geometry admission"
    )
    typer.echo(
        "Userdata / metadata: ASK before flash"
    )
    typer.echo(
        "Post-install Android reboot: ASK after success"
    )
    typer.echo()

    try:
        if input_path is not None:
            build = resolve_install_build(
                input_path,
                allow_discovery=False,
            )

        else:
            build = (
                _select_install_build()
            )

    except Exception as error:
        typer.echo(
            f"Install build resolution failed: {error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo(
        f"Product output: {build.product_out}"
    )
    typer.echo(
        f"Target device: {build.target_device}"
    )
    typer.echo(
        f"Source manifest: {build.fastboot_info_path}"
    )
    typer.echo(
        f"Referenced images: {len(build.images)}"
    )
    typer.echo(
        "Update super: "
        + (
            "yes — exactly once"
            if build.uses_update_super
            else "no"
        )
    )

    typer.echo()
    typer.echo(
        "Detecting connected device..."
    )

    try:
        controller = (
            AndroidInstallDeviceController()
        )

        device = (
            controller.enter_bootloader()
        )

    except Exception as error:
        typer.echo(
            f"Device preflight failed: {error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo()
    typer.echo(
        "=== INSTALL DEVICE PREFLIGHT ==="
    )
    typer.echo(
        f"Device: {device.serial}"
    )
    typer.echo(
        f"Fastboot: {controller.fastboot}"
    )
    typer.echo(
        "Fastboot version:"
    )

    for line in (
        controller.fastboot_version
        .splitlines()
    ):
        typer.echo(
            f"  {line}"
        )

    typer.echo(
        f"Product: {device.product}"
    )
    typer.echo(
        f"Current slot: {device.current_slot}"
    )
    typer.echo(
        f"Slot count: {device.slot_count}"
    )
    typer.echo(
        f"Unlocked: {device.unlocked}"
    )
    typer.echo(
        "Snapshot update status: "
        + (
            device.snapshot_update_status
            or "<not reported>"
        )
    )

    try:
        android_info_passed = (
            controller.validate_android_info(
                build=build,
                device=device,
            )
        )

    except Exception as error:
        typer.echo()
        typer.echo(
            "Install blocked by android-info.txt "
            f"admission requirements: {error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo(
        "android-info.txt admission: PASS"
    )

    for requirement in (
        android_info_passed
    ):
        typer.echo(
            f"  {requirement}"
        )

    typer.echo()

    live_super_size = (
        controller.partition_size_bytes(
            serial=device.serial,
            partition="super",
        )
    )

    install_layout = (
        detect_install_layout(
            repository_root=Path.cwd(),
            super_size_bytes=(
                live_super_size
            ),
        )
    )

    typer.echo()
    typer.echo(
        "=== STORAGE LAYOUT ADMISSION ==="
    )
    typer.echo(
        "Physical super: "
        f"{live_super_size:,} bytes"
    )
    typer.echo(
        "Selected storage layout: "
        f"{install_layout}"
    )

    if install_layout == TREEFORGE_LAYOUT:
        _run_treeforge_full_ab_install(
            build=build,
            controller=controller,
            device=device,
            super_size_bytes=(
                live_super_size
            ),
            install_root=install_root,
            plan_path=plan_path,
            manifest_path=manifest_path,
            preflight_path=preflight_path,
            report_path=report_path,
        )
        return

    if install_layout != STOCK_LAYOUT:
        raise AndroidInstallError(
            "Install reached an unsupported "
            f"storage layout: {install_layout}"
        )

    typer.echo(
        "Install policy: existing "
        "source-faithful Virtual A/B"
    )
    typer.echo()

    wipe_userdata = typer.confirm(
        "Wipe userdata and metadata?",
        default=False,
    )

    if wipe_userdata:
        conditional_wipe_partitions = {
            operation.partition
            for operation in build.operations
            if (
                operation.conditional
                and operation.partition
                is not None
            )
        }

        required_wipe_partitions = {
            "userdata",
            "metadata",
        }

        missing_wipe_partitions = (
            required_wipe_partitions
            - conditional_wipe_partitions
        )

        if missing_wipe_partitions:
            typer.echo()
            typer.echo(
                "Install blocked: selected source does not "
                "declare the required conditional wipe "
                "operations for: "
                + ", ".join(
                    sorted(
                        missing_wipe_partitions
                    )
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            )

    selection = (
        _install_selection(
            device=device,
            wipe_userdata=wipe_userdata,
        )
    )

    data_action = (
        "WIPE"
        if selection.wipe_userdata
        else "PRESERVE"
    )

    slot_applicability: dict[
        str,
        bool | None,
    ] = {}

    for image in build.images:
        if (
            image.partition
            in slot_applicability
        ):
            continue

        slot_applicability[
            image.partition
        ] = controller.has_slot(
            serial=device.serial,
            partition=image.partition,
        )

    try:
        preflight = (
            validate_install_preflight(
                build=build,
                device=device,
                slot_applicability=(
                    slot_applicability
                ),
            )
        )

        fastboot_info_text = (
            render_install_fastboot_info(
                build=build,
                slot_applicability=(
                    slot_applicability
                ),
            )
        )

    except Exception as error:
        typer.echo(
            f"Install plan generation failed: {error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    manifest_path.write_text(
        fastboot_info_text,
        encoding="utf-8",
    )

    preflight_path.write_text(
        render_preflight_report(
            build=build,
            device=device,
            selection=selection,
            slot_applicability=(
                slot_applicability
            ),
            preflight=preflight,
        ),
        encoding="utf-8",
    )

    _write_json(
        plan_path,
        build_plan_payload(
            build=build,
            device=device,
            selection=selection,
            slot_applicability=(
                slot_applicability
            ),
            preflight=preflight,
        ),
    )

    other_slot = (
        "b"
        if device.current_slot == "a"
        else "a"
    )

    typer.echo()
    typer.echo(
        "=== FINAL INSTALL PLAN ==="
    )
    typer.echo(
        "Selected/full dynamic slot: "
        f"{device.current_slot.upper()}"
    )
    typer.echo(
        f"Other slot: {other_slot.upper()}"
    )
    typer.echo(
        "Physical slotted images: A + B"
    )
    typer.echo(
        "Dynamic partition layout: SOURCE-DEFINED"
    )
    typer.echo(
        "Other-slot independent bootability: NOT CLAIMED"
    )
    typer.echo(
        "Shared super realizations: "
        + (
            "1"
            if build.uses_update_super
            else "0"
        )
    )
    typer.echo(
        f"Userdata: {data_action}"
    )
    typer.echo(
        f"Metadata: {data_action}"
    )
    typer.echo(
        "Post-install active-slot change: NO"
    )
    typer.echo(
        "Post-install Android reboot: ASK (default NO)"
    )

    typer.echo()
    typer.echo(
        "Projection validation:"
    )
    typer.echo(
        "  Snapshot state safe: YES"
    )
    typer.echo(
        "  Dynamic topology: SOURCE-DEFINED"
    )
    typer.echo(
        "  Dynamic primary images: "
        f"{preflight['dynamic_primary_image_count']}"
    )
    typer.echo(
        "  Dynamic secondary images: "
        f"{preflight['dynamic_secondary_image_count']}"
    )
    typer.echo(
        "  Synthetic secondary dynamic images: 0"
    )
    typer.echo(
        "  Mirrored physical images: "
        f"{preflight['mirrored_physical_image_count']}"
    )

    typer.echo()
    typer.echo(
        "Images:"
    )

    for image in build.images:
        applicable = (
            slot_applicability.get(
                image.partition
            )
        )

        if image.domain == "bootloader-fastboot":
            if image.slot_other:
                target = (
                    f"{image.partition}_{other_slot}"
                    if applicable is True
                    else image.partition
                )

                role = (
                    "source secondary physical"
                )

            elif applicable is True:
                target = (
                    f"{image.partition}_a + "
                    f"{image.partition}_b"
                )

                role = (
                    "mirrored physical"
                )

            else:
                target = (
                    image.partition
                )

                role = (
                    "shared physical"
                )

        else:
            if image.slot_other:
                target = (
                    f"{image.partition}_{other_slot}"
                    if applicable is True
                    else image.partition
                )

                role = (
                    "source secondary dynamic"
                )

            else:
                target = (
                    f"{image.partition}_{device.current_slot}"
                    if applicable is True
                    else image.partition
                )

                role = (
                    "source primary dynamic"
                )

        typer.echo(
            f"  {target} <- {image.image_name} "
            f"[{role}]"
        )

    typer.echo()
    typer.echo(
        "Execution topology:"
    )
    typer.echo(
        "  1. Selected-slot physical images"
    )
    typer.echo(
        "  2. Mirror slotted physical images to the other slot"
    )
    typer.echo(
        "  3. Enter fastbootd once"
    )

    if build.uses_update_super:
        typer.echo(
            "  4. update-super exactly once"
        )
        typer.echo(
            "  5. Source primary logical images -> selected slot"
        )
        typer.echo(
            "  6. Source secondary logical images -> other slot"
        )
        typer.echo(
            "  7. Stop in fastboot/fastbootd"
        )
        typer.echo(
            "  8. Offer Android reboot"
        )

    else:
        typer.echo(
            "  4. Apply remaining source-defined operations"
        )
        typer.echo(
            "  5. Stop in fastboot"
        )
        typer.echo(
            "  6. Offer Android reboot"
        )

    typer.echo()
    typer.echo(
        f"Generated manifest: {manifest_path}"
    )
    typer.echo(
        f"Plan: {plan_path}"
    )
    typer.echo(
        f"Preflight: {preflight_path}"
    )
    typer.echo()

    confirmed = typer.confirm(
        "Proceed with source-faithful A/B flash?",
        default=False,
    )

    if not confirmed:
        report_path.write_text(
            (
                "TreeForge Install\n\n"
                "Status: CANCELLED\n"
                "Mode: source-faithful A/B\n"
                "Flash performed: NO\n"
                f"Wipe requested: "
                f"{'YES' if selection.wipe_userdata else 'NO'}\n"
                "Automatic Android reboot: NO\n"
            ),
            encoding="utf-8",
        )

        typer.echo(
            "Install cancelled. No partitions were flashed."
        )
        return

    typer.echo()
    typer.echo(
        "Starting source-faithful A/B install..."
    )

    try:
        result = controller.execute(
            build=build,
            device=device,
            selection=selection,
            fastboot_info_text=(
                fastboot_info_text
            ),
        )

    except Exception as error:
        report_path.write_text(
            (
                "TreeForge Install\n\n"
                "Status: FAILED\n"
                "Mode: source-faithful A/B\n"
                f"Build: {build.product_out}\n"
                f"Device: {device.serial}\n"
                f"Error: {error}\n"
                f"Wipe requested: "
                f"{'YES' if selection.wipe_userdata else 'NO'}\n"
                "Automatic Android reboot: NO\n"
            ),
            encoding="utf-8",
        )

        typer.echo()
        typer.echo(
            f"Install failed: {error}",
            err=True,
        )
        typer.echo(
            "Device intentionally left in the fastboot "
            "domain where execution stopped.",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo()
    typer.echo(
        "TreeForge Install completed successfully."
    )
    typer.echo(
        "Physical slotted images mirrored: A + B"
    )
    typer.echo(
        "Dynamic layout applied exactly as declared "
        "by the source manifest."
    )
    typer.echo(
        "Independent bootability of the other dynamic "
        "slot is not claimed by this direct Install."
    )
    typer.echo(
        "Active slot preserved: "
        f"{result.final_active_slot.upper()}"
    )
    typer.echo(
        f"Userdata / metadata: {data_action}"
    )
    typer.echo()

    reboot_requested = typer.confirm(
        "Reboot to Android now?",
        default=False,
    )

    reboot_status = (
        "NOT REQUESTED"
    )

    reboot_error = None

    if reboot_requested:
        try:
            controller.reboot_android(
                serial=device.serial,
            )

            reboot_status = "REQUESTED"

        except Exception as error:
            reboot_status = "FAILED"
            reboot_error = str(
                error
            )

    report_lines = [
        "TreeForge Install",
        "",
        "Status: SUCCESS",
        "Mode: source-faithful A/B",
        f"Build: {build.product_out}",
        f"Device: {device.serial}",
        f"Device product: {device.product}",
        "Physical slotted images mirrored: YES",
        f"Full dynamic slot: {device.current_slot}",
        (
            "Other dynamic slot: source-defined "
            f"({other_slot})"
        ),
        (
            "Other-slot independent bootability "
            "claimed: NO"
        ),
        (
            "Userdata preserved: "
            + (
                "NO"
                if selection.wipe_userdata
                else "YES"
            )
        ),
        (
            "Metadata preserved: "
            + (
                "NO"
                if selection.wipe_userdata
                else "YES"
            )
        ),
        (
            "Wipe requested: "
            + (
                "YES"
                if selection.wipe_userdata
                else "NO"
            )
        ),
        "Post-install active-slot change: NO",
        (
            "Active slot preserved: "
            f"{result.final_active_slot}"
        ),
        "Automatic Android reboot: NO",
        (
            "Post-install Android reboot requested: "
            + (
                "YES"
                if reboot_requested
                else "NO"
            )
        ),
        (
            "Post-install Android reboot command: "
            f"{reboot_status}"
        ),
    ]

    if reboot_error is not None:
        report_lines.append(
            "Post-install Android reboot error: "
            + reboot_error
        )

    report_path.write_text(
        "\n".join(
            report_lines
        )
        + "\n",
        encoding="utf-8",
    )

    typer.echo()

    if reboot_error is not None:
        typer.echo(
            "Install succeeded, but the requested "
            "Android reboot failed:",
            err=True,
        )
        typer.echo(
            f"  {reboot_error}",
            err=True,
        )
        typer.echo(
            "Device remains in the fastboot domain.",
            err=True,
        )
        typer.echo(
            f"Report: {report_path}"
        )

        raise typer.Exit(
            code=1
        )

    if reboot_requested:
        typer.echo(
            "Reboot to Android requested successfully."
        )

    else:
        typer.echo(
            "Device remains in fastboot/fastbootd."
        )

    typer.echo(
        f"Report: {report_path}"
    )
