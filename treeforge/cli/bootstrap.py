from __future__ import annotations

from pathlib import Path
import logging
import sys

import typer

from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
    parsing_snapshot_path,
)
from treeforge.android.bootstrap.early_dispatch import (
    AndroidBootstrapEarlyDispatcherBuilder,
)
from treeforge.android.bootstrap.recovery_manifest import (
    AndroidBootstrapRecoveryPartitionManifestBuilder,
)
from treeforge.android.bootstrap.recovery_usb import (
    AndroidBootstrapRecoveryUsbIdentityBuilder,
)
from treeforge.android.bootstrap.recovery_runtime import (
    AndroidBootstrapRecoveryRuntimeBuilder,
)
from treeforge.android.bootstrap.handoff import (
    AndroidBootstrapBootImageHandoffManifest,
    AndroidBootstrapBootImageReplacement,
    sha256_file,
)
from treeforge.android.bootstrap.pipeline import (
    AndroidBootstrapPipeline,
)
from treeforge.android.bootstrap.runtime_provider_bundle import (
    AndroidBootstrapRuntimeProviderBundleLoader,
)
from treeforge.android.recovery.runtime_composition import (
    compose_recovery_runtime,
)
from treeforge.android.boot_image.ramdisk_packaging import (
    AndroidBootImageRamdiskPackager,
)
from treeforge.android.extraction.cpio.extractor import (
    CpioNewcEntry,
)
from treeforge.android.format.compression import (
    CompressionFormat,
)
from treeforge.cli.bootstrap_report import (
    render_bootstrap_reports,
)
from treeforge.cli.progress import (
    configure_live_progress_logging,
    render_progress,
)
from treeforge.workspace.workspace import (
    Workspace,
)
from treeforge.android.bootstrap.runtime_provider_bundle import bootstrap_runtime_provider_bundle_root


app = typer.Typer(
    help=(
        "Derive and prepare TreeForge's Bootstrap environment from the "
        "canonical Parsing handoff."
    )
)


@app.callback(
    invoke_without_command=True,
)
def bootstrap(
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Bootstrap artifacts are written under "
            "OUTPUT/bootstrap. Defaults to ./output."
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
            "Optional explicit canonical Parsing snapshot. When omitted, "
            "Bootstrap uses OUTPUT/parsing's canonical snapshot."
        ),
    ),
    hardware: str | None = typer.Option(
        None,
        "--hardware",
        help=(
            "Optional explicit ro.hardware value for Bootstrap environment "
            "planning. When omitted, the planner's configured default is used."
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help=(
            "Show additional TreeForge diagnostic logging. Canonical "
            "Bootstrap phase progress is shown by default."
        ),
    ),
) -> None:
    """
    Run Bootstrap from canonical Parsing through Deployment Planning.

    Bootstrap prepares the recovery/bootstrap environment and replacement
    Boot Image component artifact. It does not rebuild boot-family images,
    perform AVB signing, choose a device slot, or invoke fastboot.

    The generated handoff is consumed explicitly by:

      treeforge boot-image
    """

    typer.echo(
        "TreeForge Bootstrap"
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

    bootstrap_root = (
        output
        / "bootstrap"
    )

    rootfs = (
        bootstrap_root
        / "environment"
        / "rootfs"
    )

    deployment_root = (
        bootstrap_root
        / "deployment"
    )

    replacement_path = (
        deployment_root
        / "ramdisk"
    )

    cpio_path = (
        deployment_root
        / "ramdisk.cpio"
    )

    init_boot_replacement_path = (
        deployment_root
        / "init_boot.ramdisk"
    )

    init_boot_cpio_path = (
        deployment_root
        / "init_boot.ramdisk.cpio"
    )

    early_dispatch_root = (
        bootstrap_root
        / "early-dispatch"
    )

    recovery_runtime_root = (
        bootstrap_root
        / "recovery-runtime"
    )

    # Android's canonical force-debuggable payload is bundled with
    # TreeForge after provider generation and factory-policy acceptance.
    #
    # Provider release directories preserve provenance. Selection is based
    # on canonical factory Android platform evidence, not device identity
    # or an AOSP checkout.
    debug_root_data_root = (
        Path(__file__)
        .resolve()
        .parents[1]
        / "data"
        / "android"
        / "debug-root"
    )

    handoff_path = (
        deployment_root
        / "boot-image-replacements.json"
    )

    parsing_workspace = Workspace(
        output
        / "parsing"
    )

    snapshot_path = (
        parsing_snapshot.expanduser().resolve()
        if parsing_snapshot is not None
        else parsing_snapshot_path(
            parsing_workspace
        )
    )

    if not snapshot_path.is_file():
        typer.echo(
            (
                "Canonical Parsing snapshot not found: "
                f"{snapshot_path}"
            ),
            err=True,
        )
        typer.echo(
            (
                "Run the Parsing stage first, or provide "
                "--parsing-snapshot."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    typer.echo()
    typer.echo(
        "Using canonical Parsing snapshot:"
    )
    typer.echo(
        f"  {snapshot_path}"
    )

    try:
        snapshot = (
            AndroidParsingSnapshotStore()
            .load(
                snapshot_path
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Unable to load canonical Parsing snapshot: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    parsing = snapshot.parsing

    canonical_sdk_declarations = tuple(
        declaration
        for property_file
        in parsing.filesystem.property_files
        for declaration
        in property_file.declarations
        if declaration.key == "ro.build.version.sdk"
    )

    canonical_sdk_values = tuple(
        dict.fromkeys(
            declaration.value
            for declaration
            in canonical_sdk_declarations
        )
    )

    if (
        len(canonical_sdk_values) != 1
        or not canonical_sdk_values[0]
    ):
        raise RuntimeError(
            "Bootstrap debug-root provider selection requires exactly "
            "one concordant canonical ro.build.version.sdk value; "
            f"found {canonical_sdk_values!r}"
        )

    canonical_sdk_level = canonical_sdk_values[0]

    debug_root_provider_registry = {
        "35": "android-15.0.0_r36",
    }

    debug_root_provider_release = (
        debug_root_provider_registry.get(
            canonical_sdk_level
        )
    )

    if debug_root_provider_release is None:
        raise RuntimeError(
            "TreeForge does not bundle a debug-root provider for "
            "canonical Android SDK level "
            f"{canonical_sdk_level!r}"
        )

    debug_root_provider_root = (
        debug_root_data_root
        / debug_root_provider_release
    )

    adb_debug_prop_provider_path = (
        debug_root_provider_root
        / "adb_debug.prop"
    )

    userdebug_plat_sepolicy_provider_path = (
        debug_root_provider_root
        / "userdebug_plat_sepolicy.cil"
    )

    # Recovery ADB implementation provider.
    #
    # Canonical requirements remain derived entirely from
    # Parsing/Planning. TreeForge's bundled provider supplies
    # implementation bytes only.
    runtime_provider_registry = {
        "35": "android-15.0.0_r36-arm64",
    }

    runtime_provider_release = (
        runtime_provider_registry.get(
            canonical_sdk_level
        )
    )

    if runtime_provider_release is None:
        raise RuntimeError(
            "TreeForge does not bundle a Recovery ADB runtime "
            "provider for canonical Android SDK level "
            f"{canonical_sdk_level!r}"
        )

    runtime_provider_root = (
        bootstrap_runtime_provider_bundle_root(name='aosp-adbd-recovery', release=runtime_provider_release)
    )

    runtime_provider = (
        AndroidBootstrapRuntimeProviderBundleLoader
        .load(
            runtime_provider_root
        )
    )

    if (
        runtime_provider.canonical_sdk_level
        != canonical_sdk_level
    ):
        raise RuntimeError(
            "Bootstrap ADB runtime provider SDK does not match "
            "canonical factory SDK: provider="
            f"{runtime_provider.canonical_sdk_level!r}, "
            f"canonical={canonical_sdk_level!r}"
        )

    if runtime_provider.architecture != "arm64":
        raise RuntimeError(
            "Bootstrap ADB runtime provider architecture is not "
            "the current canonical arm64 provider: "
            f"{runtime_provider.architecture!r}"
        )

    bootstrap_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    typer.echo()
    typer.echo(
        "ADB runtime provider:"
    )
    typer.echo(
        f"  {runtime_provider.name}"
    )
    typer.echo(
        f"  {runtime_provider.release}"
    )

    typer.echo()
    typer.echo(
        "Running Bootstrap..."
    )

    try:
        deployment = (
            AndroidBootstrapPipeline()
            .execute_deployment_planning(
                parsing,
                rootfs=rootfs,
                replacement_path=(
                    replacement_path
                ),
                runtime_provider=(
                    runtime_provider
                ),
                progress_callback=(
                    render_progress
                ),
                hardware=hardware,
            )
        )
    except Exception as error:
        typer.echo()
        typer.echo(
            (
                "Bootstrap failed: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    if deployment.parsing is not parsing:
        typer.echo(
            "Bootstrap lost exact canonical Parsing identity.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    environment = (
        deployment
        .environment_realization
    )

    plan = environment.plan

    population = plan.population
    elf_closure = plan.elf_closure
    candidate = (
        plan
        .environment_root
        .candidate
    )

    if (
        population is None
        or elf_closure is None
        or candidate is None
    ):
        typer.echo(
            "Bootstrap completed without a fully resolved environment.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    compression_facts = tuple(
        fact
        for fact
        in candidate
        .ramdisk
        .ramdisk
        .ramdisk_cpio
        .facts
        if fact.name == "compression"
    )

    if len(
        compression_facts
    ) != 1:
        typer.echo(
            (
                "Bootstrap selected ramdisk does not retain exactly one "
                "canonical compression fact."
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    try:
        compression = CompressionFormat(
            compression_facts[
                0
            ].value
        )
    except ValueError as error:
        typer.echo(
            (
                "Bootstrap selected ramdisk uses an unsupported "
                "compression value: "
                f"{compression_facts[0].value!r}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    # ------------------------------------------------------------
    # TreeForge early init dispatcher
    # ------------------------------------------------------------
    #
    # init_boot owns the earliest canonical /init on this boot topology.
    # Bootstrap therefore prepares a second complete ramdisk replacement:
    #
    #   init
    #       TreeForge freestanding PID-1 dispatcher
    #
    #   init.treeforge-original
    #       exact canonical /init payload
    #
    #   init.treeforge-first-stage
    #       canonical /init with only the unique final
    #       /system/bin/init transition redirected to
    #       /proc/self/fd/99
    #
    # Every other canonical init_boot CPIO entry remains the exact
    # caller-owned CpioNewcEntry object and stays in canonical order.
    #
    init_boot_ramdisks = tuple(
        value
        for value
        in plan.boot_image_interpretation.ramdisks
        if value.boot_family_name == "init_boot"
    )

    if len(init_boot_ramdisks) != 1:
        raise RuntimeError(
            "Bootstrap early dispatcher requires exactly one "
            "canonical init_boot ramdisk interpretation; "
            f"found {len(init_boot_ramdisks)}"
        )

    init_boot_ramdisk = (
        init_boot_ramdisks[
            0
        ]
    )

    init_boot_interpretations = (
        init_boot_ramdisk.cpio_entries
    )

    canonical_init_boot_entries = tuple(
        value.entry
        for value
        in init_boot_interpretations
    )

    if not canonical_init_boot_entries:
        raise RuntimeError(
            "canonical init_boot ramdisk CPIO population is empty"
        )

    canonical_init_matches = tuple(
        entry
        for entry
        in canonical_init_boot_entries
        if entry.path.lstrip("/") == "init"
    )

    if len(canonical_init_matches) != 1:
        raise RuntimeError(
            "Bootstrap early dispatcher requires exactly one "
            "canonical init_boot /init entry; "
            f"found {len(canonical_init_matches)}"
        )

    canonical_init_entry = (
        canonical_init_matches[
            0
        ]
    )

    if (
        canonical_init_entry
        .entry_type
        .value
        != "file"
    ):
        raise RuntimeError(
            "canonical init_boot /init is not a regular file"
        )

    if canonical_init_entry.nlink != 1:
        raise RuntimeError(
            "Bootstrap early dispatcher currently requires canonical "
            "init_boot /init to have link count 1"
        )

    # ------------------------------------------------------------
    # TreeForge retained Recovery runtime population
    # ------------------------------------------------------------
    #
    # Recovery owns runtime-provider selection and composition.
    # Bootstrap receives only the resulting neutral file population.
    #
    # Files already supplied by Bootstrap's existing aosp-adbd-recovery
    # realization retain their proven canonical source paths.
    #
    # Files introduced only by Recovery are injected into a private
    # TreeForge staging namespace in the ramdisk and retained from
    # there. This avoids replacing or colliding with canonical factory
    # paths merely to preserve a Recovery-only implementation.
    recovery_runtime_composition = (
        compose_recovery_runtime(
            canonical_sdk_level=(
                canonical_sdk_level
            ),
            architecture="arm64",
        )
    )

    bootstrap_runtime_by_path = {
        value.android_path: value
        for value
        in runtime_provider.files
    }

    retained_runtime_values = []
    staged_recovery_runtime_files = []

    for runtime_file in (
        recovery_runtime_composition.files
    ):
        bootstrap_file = (
            bootstrap_runtime_by_path.get(
                runtime_file.android_path
            )
        )

        if bootstrap_file is not None:
            if (
                bootstrap_file.content_sha256
                != runtime_file.content_sha256
            ):
                raise RuntimeError(
                    "Bootstrap and Recovery runtime providers "
                    "disagree on retained implementation bytes for "
                    f"{runtime_file.android_path}"
                )

            source_runtime_path = (
                runtime_file
                .android_path
                .as_posix()
            )

        else:
            source_runtime_path = (
                runtime_file
                .staging_path
                .as_posix()
            )

            staged_recovery_runtime_files.append(
                runtime_file
            )

        retained_runtime_values.append(
            (
                source_runtime_path,
                runtime_file
                .destination_path
                .as_posix(),
                runtime_file.mode,
            )
        )

    retained_runtime_files = tuple(
        retained_runtime_values
    )

    staged_recovery_runtime_files = tuple(
        staged_recovery_runtime_files
    )

    if not retained_runtime_files:
        raise RuntimeError(
            "Recovery-owned runtime composition produced no "
            "retained files"
        )

    if len(retained_runtime_files) > 32:
        raise RuntimeError(
            "Recovery-owned runtime composition exceeds the "
            "32-descriptor retained runtime capacity: "
            f"{len(retained_runtime_files)}"
        )

    typer.echo()
    typer.echo(
        "Recovery runtime composition:"
    )

    typer.echo(
        "  providers: "
        + ", ".join(
            recovery_runtime_composition
            .providers
        )
    )

    typer.echo(
        "  retained files: "
        f"{len(retained_runtime_files)}/32"
    )

    typer.echo(
        "  new ramdisk staging files: "
        f"{len(staged_recovery_runtime_files)}"
    )

    dispatcher = (
        AndroidBootstrapEarlyDispatcherBuilder()
        .build(
            canonical_init=(
                canonical_init_entry.data
            ),
            retained_runtime_files=(
                retained_runtime_files
            ),
            output_root=(
                early_dispatch_root
            ),
        )
    )

    dispatcher_data = (
        dispatcher
        .executable_path
        .read_bytes()
    )

    recovery_partition_manifest = (
        AndroidBootstrapRecoveryPartitionManifestBuilder
        .build(
            parsing
        )
    )

    recovery_usb_identity = (
        AndroidBootstrapRecoveryUsbIdentityBuilder
        .build(
            parsing
        )
    )

    if (
        recovery_usb_identity.parsing
        is not parsing
    ):
        raise RuntimeError(
            "Bootstrap Recovery USB identity lost exact "
            "canonical Parsing identity"
        )

    recovery_runtime = (
        AndroidBootstrapRecoveryRuntimeBuilder()
        .build(
            canonical_init=(
                canonical_init_entry.data
            ),
            partition_manifest=(
                recovery_partition_manifest
            ),
            usb_identity=(
                recovery_usb_identity
            ),
            output_root=(
                recovery_runtime_root
            ),
        )
    )

    recovery_runtime_data = (
        recovery_runtime
        .executable_path
        .read_bytes()
    )

    if not adb_debug_prop_provider_path.is_file():
        raise RuntimeError(
            "Bootstrap root payload requires the bundled Android "
            "adb_debug.prop provider for "
            f"{debug_root_provider_release}: "
            f"{adb_debug_prop_provider_path}"
        )

    if not userdebug_plat_sepolicy_provider_path.is_file():
        raise RuntimeError(
            "Bootstrap root payload requires the bundled Android "
            "userdebug_plat_sepolicy.cil provider for "
            f"{debug_root_provider_release}: "
            f"{userdebug_plat_sepolicy_provider_path}"
        )

    adb_debug_prop_data = (
        adb_debug_prop_provider_path
        .read_bytes()
    )

    userdebug_plat_sepolicy_data = (
        userdebug_plat_sepolicy_provider_path
        .read_bytes()
    )

    if not adb_debug_prop_data:
        raise RuntimeError(
            "Android adb_debug.prop provider is empty"
        )

    required_debug_properties = (
        b"ro.adb.secure=0",
        b"ro.debuggable=1",
        b"ro.force.debuggable=1",
    )

    missing_debug_properties = tuple(
        value
        for value
        in required_debug_properties
        if value not in adb_debug_prop_data
    )

    if missing_debug_properties:
        raise RuntimeError(
            "Android adb_debug.prop provider does not expose the "
            "canonical force-debuggable property contract: "
            + ", ".join(
                value.decode(
                    "ascii",
                    errors="replace",
                )
                for value
                in missing_debug_properties
            )
        )

    if not userdebug_plat_sepolicy_data:
        raise RuntimeError(
            "Android userdebug platform SELinux policy provider is empty"
        )

    dispatcher_entry = CpioNewcEntry(
        path=canonical_init_entry.path,
        ino=canonical_init_entry.ino,
        mode=canonical_init_entry.mode,
        uid=canonical_init_entry.uid,
        gid=canonical_init_entry.gid,
        nlink=canonical_init_entry.nlink,
        mtime=canonical_init_entry.mtime,
        filesize=len(
            dispatcher_data
        ),
        devmajor=canonical_init_entry.devmajor,
        devminor=canonical_init_entry.devminor,
        rdevmajor=canonical_init_entry.rdevmajor,
        rdevminor=canonical_init_entry.rdevminor,
        namesize=canonical_init_entry.namesize,
        check=canonical_init_entry.check,
        data=dispatcher_data,
    )

    original_init_path = (
        "init.treeforge-original"
    )

    first_stage_init_path = (
        "init.treeforge-first-stage"
    )

    adb_debug_prop_path = (
        "adb_debug.prop"
    )

    userdebug_plat_sepolicy_path = (
        "userdebug_plat_sepolicy.cil"
    )

    recovery_runtime_path = (
        "treeforge-recovery"
    )

    reserved_init_paths = (
        original_init_path,
        first_stage_init_path,
        adb_debug_prop_path,
        userdebug_plat_sepolicy_path,
        recovery_runtime_path,
    )

    for reserved_path in reserved_init_paths:
        if any(
            entry.path.lstrip("/")
            == reserved_path
            for entry
            in canonical_init_boot_entries
        ):
            raise RuntimeError(
                "canonical init_boot already contains reserved "
                f"{reserved_path!r}"
            )

    transition_source = (
        b"/system/bin/init\x00"
    )

    transition_target = (
        b"/proc/self/fd/99\x00"
    )

    if (
        len(transition_source)
        != len(transition_target)
    ):
        raise RuntimeError(
            "TreeForge first-stage transition replacement must "
            "preserve the canonical literal allocation length"
        )

    transition_count = (
        canonical_init_entry
        .data
        .count(
            transition_source
        )
    )

    if transition_count != 1:
        raise RuntimeError(
            "Bootstrap first-stage transition interposition requires "
            "exactly one canonical /system/bin/init literal; "
            f"found {transition_count}"
        )

    if (
        transition_target
        in canonical_init_entry.data
    ):
        raise RuntimeError(
            "canonical init already contains TreeForge's reserved "
            "first-stage transition target"
        )

    transition_offset = (
        canonical_init_entry
        .data
        .index(
            transition_source
        )
    )

    first_stage_init_data = (
        canonical_init_entry
        .data
        .replace(
            transition_source,
            transition_target,
            1,
        )
    )

    if (
        len(first_stage_init_data)
        != len(canonical_init_entry.data)
    ):
        raise RuntimeError(
            "TreeForge first-stage init mutation changed canonical "
            "init byte length"
        )

    if (
        first_stage_init_data.count(
            transition_target
        )
        != 1
        or first_stage_init_data.count(
            transition_source
        )
        != 0
    ):
        raise RuntimeError(
            "TreeForge first-stage transition mutation did not "
            "produce exactly one redirected transition"
        )

    changed_offsets = tuple(
        index
        for index, (
            canonical_byte,
            generated_byte,
        )
        in enumerate(
            zip(
                canonical_init_entry.data,
                first_stage_init_data,
                strict=True,
            )
        )
        if canonical_byte
        != generated_byte
    )

    transition_end = (
        transition_offset
        + len(transition_source)
    )

    if (
        not changed_offsets
        or any(
            offset < transition_offset
            or offset >= transition_end
            for offset
            in changed_offsets
        )
    ):
        raise RuntimeError(
            "TreeForge first-stage init mutation changed bytes "
            "outside the unique transition literal"
        )

    maximum_inode = max(
        entry.ino
        for entry
        in canonical_init_boot_entries
    )

    required_extra_inodes = 5

    if (
        maximum_inode
        > (
            0xFFFFFFFF
            - required_extra_inodes
        )
    ):
        raise RuntimeError(
            "canonical init_boot CPIO inode population has no "
            "available deterministic inodes for TreeForge "
            "generated entries"
        )

    original_init_entry = CpioNewcEntry(
        path=original_init_path,
        ino=maximum_inode + 1,
        mode=canonical_init_entry.mode,
        uid=canonical_init_entry.uid,
        gid=canonical_init_entry.gid,
        nlink=canonical_init_entry.nlink,
        mtime=canonical_init_entry.mtime,
        filesize=canonical_init_entry.filesize,
        devmajor=canonical_init_entry.devmajor,
        devminor=canonical_init_entry.devminor,
        rdevmajor=canonical_init_entry.rdevmajor,
        rdevminor=canonical_init_entry.rdevminor,
        namesize=(
            len(
                original_init_path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )
            + 1
        ),
        check=canonical_init_entry.check,
        data=canonical_init_entry.data,
    )

    first_stage_init_entry = CpioNewcEntry(
        path=first_stage_init_path,
        ino=maximum_inode + 2,
        mode=canonical_init_entry.mode,
        uid=canonical_init_entry.uid,
        gid=canonical_init_entry.gid,
        nlink=canonical_init_entry.nlink,
        mtime=canonical_init_entry.mtime,
        filesize=len(
            first_stage_init_data
        ),
        devmajor=canonical_init_entry.devmajor,
        devminor=canonical_init_entry.devminor,
        rdevmajor=canonical_init_entry.rdevmajor,
        rdevminor=canonical_init_entry.rdevminor,
        namesize=(
            len(
                first_stage_init_path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )
            + 1
        ),
        check=canonical_init_entry.check,
        data=first_stage_init_data,
    )

    adb_debug_prop_entry = CpioNewcEntry(
        path=adb_debug_prop_path,
        ino=maximum_inode + 3,
        mode=0o100644,
        uid=0,
        gid=0,
        nlink=1,
        mtime=canonical_init_entry.mtime,
        filesize=len(
            adb_debug_prop_data
        ),
        devmajor=0,
        devminor=0,
        rdevmajor=0,
        rdevminor=0,
        namesize=(
            len(
                adb_debug_prop_path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )
            + 1
        ),
        check=0,
        data=adb_debug_prop_data,
    )

    userdebug_plat_sepolicy_entry = CpioNewcEntry(
        path=userdebug_plat_sepolicy_path,
        ino=maximum_inode + 4,
        mode=0o100644,
        uid=0,
        gid=0,
        nlink=1,
        mtime=canonical_init_entry.mtime,
        filesize=len(
            userdebug_plat_sepolicy_data
        ),
        devmajor=0,
        devminor=0,
        rdevmajor=0,
        rdevminor=0,
        namesize=(
            len(
                userdebug_plat_sepolicy_path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )
            + 1
        ),
        check=0,
        data=userdebug_plat_sepolicy_data,
    )

    recovery_runtime_entry = CpioNewcEntry(
        path=recovery_runtime_path,
        ino=maximum_inode + 5,
        mode=0o100755,
        uid=0,
        gid=0,
        nlink=1,
        mtime=canonical_init_entry.mtime,
        filesize=len(
            recovery_runtime_data
        ),
        devmajor=0,
        devminor=0,
        rdevmajor=0,
        rdevminor=0,
        namesize=(
            len(
                recovery_runtime_path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )
            + 1
        ),
        check=0,
        data=recovery_runtime_data,
    )

    modified_init_boot_entries = []

    for entry in canonical_init_boot_entries:
        if entry is canonical_init_entry:
            modified_init_boot_entries.append(
                dispatcher_entry
            )

            modified_init_boot_entries.append(
                original_init_entry
            )

            modified_init_boot_entries.append(
                first_stage_init_entry
            )

            modified_init_boot_entries.append(
                adb_debug_prop_entry
            )

            modified_init_boot_entries.append(
                userdebug_plat_sepolicy_entry
            )

            modified_init_boot_entries.append(
                recovery_runtime_entry
            )

            continue

        modified_init_boot_entries.append(
            entry
        )

    modified_init_boot_entries = tuple(
        modified_init_boot_entries
    )

    generated_init_boot_entry_count = 5

    if (
        len(modified_init_boot_entries)
        != len(canonical_init_boot_entries)
        + generated_init_boot_entry_count
    ):
        raise RuntimeError(
            "Bootstrap early dispatcher init_boot population "
            "accounting failed"
        )

    untouched_expected = tuple(
        entry
        for entry
        in canonical_init_boot_entries
        if entry is not canonical_init_entry
    )

    untouched_actual = tuple(
        entry
        for entry
        in modified_init_boot_entries
        if (
            entry is not dispatcher_entry
            and entry is not original_init_entry
            and entry is not first_stage_init_entry
            and entry is not adb_debug_prop_entry
            and entry is not userdebug_plat_sepolicy_entry
            and entry is not recovery_runtime_entry
        )
    )

    if (
        tuple(
            id(value)
            for value
            in untouched_actual
        )
        != tuple(
            id(value)
            for value
            in untouched_expected
        )
    ):
        raise RuntimeError(
            "Bootstrap early dispatcher changed canonical "
            "init_boot entries outside /init"
        )

    init_boot_compression_facts = tuple(
        fact
        for fact
        in (
            init_boot_ramdisk
            .ramdisk
            .ramdisk_cpio
            .facts
        )
        if fact.name == "compression"
    )

    if (
        len(
            init_boot_compression_facts
        )
        != 1
    ):
        raise RuntimeError(
            "canonical init_boot ramdisk does not retain "
            "exactly one compression fact"
        )

    try:
        init_boot_compression = (
            CompressionFormat(
                init_boot_compression_facts[
                    0
                ].value
            )
        )
    except ValueError as error:
        raise RuntimeError(
            "canonical init_boot ramdisk uses an unsupported "
            "compression format: "
            f"{init_boot_compression_facts[0].value!r}"
        ) from error

    try:
        init_boot_package = (
            AndroidBootImageRamdiskPackager()
            .package(
                modified_init_boot_entries,
                compression=(
                    init_boot_compression
                ),
                cpio_path=(
                    init_boot_cpio_path
                ),
                ramdisk_path=(
                    init_boot_replacement_path
                ),
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Unable to package Bootstrap init_boot "
                "early-dispatch ramdisk: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    canonical_init_boot_component = (
        init_boot_ramdisk
        .ramdisk
        .ramdisk_component
    )

    canonical_init_boot_component_path = (
        canonical_init_boot_component
        .path
    )

    if not canonical_init_boot_component_path.is_file():
        raise FileNotFoundError(
            "canonical init_boot ramdisk component is unavailable: "
            f"{canonical_init_boot_component_path}"
        )

    init_boot_replacement = (
        AndroidBootstrapBootImageReplacement(
            container_kind="init_boot",
            semantic_name="ramdisk",
            replacement_path=(
                init_boot_package
                .ramdisk_path
            ),
            replacement_size_bytes=(
                init_boot_package
                .ramdisk_size_bytes
            ),
            replacement_sha256=(
                init_boot_package
                .ramdisk_sha256
            ),
            original_component_path=(
                canonical_init_boot_component_path
            ),
            original_component_size_bytes=(
                canonical_init_boot_component_path
                .stat()
                .st_size
            ),
            original_component_sha256=(
                sha256_file(
                    canonical_init_boot_component_path
                )
            ),
            cpio_path=(
                init_boot_package
                .cpio_path
            ),
            cpio_size_bytes=(
                init_boot_package
                .cpio_size_bytes
            ),
            cpio_sha256=(
                init_boot_package
                .cpio_sha256
            ),
            compression=(
                init_boot_package
                .compression
                .value
            ),
            rollback_required=True,
        )
    )

    # A Bootstrap environment may select a minimal semantic/runtime
    # population, but Deployment replaces the complete ramdisk component.
    #
    # Therefore every non-selected canonical CPIO entry must remain present
    # unchanged in the replacement archive. "Preserved" means conserved in
    # the whole-ramdisk replacement, not omitted from it.
    canonical_interpretations = (
        population.ramdisk.cpio_entries
    )

    selected_ids = {
        id(value.entry)
        for value
        in population.entries
    }

    preserved_ids = {
        id(value)
        for value
        in population.preserved_entries
    }

    canonical_ids = tuple(
        id(value)
        for value
        in canonical_interpretations
    )

    if len(
        canonical_ids
    ) != population.accounted_count:
        raise RuntimeError(
            "Bootstrap whole-ramdisk packaging lost canonical "
            "CPIO population accounting"
        )

    if set(
        canonical_ids
    ) != (
        selected_ids
        | preserved_ids
    ):
        raise RuntimeError(
            "Bootstrap whole-ramdisk packaging population does not "
            "match selected + preserved Planning evidence"
        )

    #
    # Environment Realization may intentionally substitute implementation
    # provider bytes for selected canonical regular files.
    #
    # Whole-ramdisk packaging must preserve the canonical CPIO structure,
    # metadata, path ordering, and non-provider payloads while carrying those
    # exact validated provider substitutions forward into the physical
    # replacement ramdisk.
    #
    # Do not package directly from the canonical CpioNewcEntry population:
    # doing so would silently discard Environment Realization substitutions.
    #
    realization_by_interpretation_id = {
        id(
            value.population_entry.entry
        ): value
        for value
        in deployment.environment_realization.entries
    }

    expected_provider_substitutions = sum(
        1
        for value
        in deployment.environment_realization.entries
        if value.runtime_provider_name is not None
    )

    packaged_entries = []
    packaged_provider_substitutions = 0

    for interpretation in canonical_interpretations:
        canonical_entry = interpretation.entry

        realization = (
            realization_by_interpretation_id.get(
                id(
                    interpretation
                )
            )
        )

        if (
            realization is None
            or realization.runtime_provider_name is None
        ):
            packaged_entries.append(
                canonical_entry
            )
            continue

        if (
            canonical_entry
            .entry_type
            .value
            != "file"
        ):
            raise RuntimeError(
                "Bootstrap runtime-provider substitution reached "
                "a non-regular CPIO entry: "
                f"{canonical_entry.path!r}"
            )

        if (
            realization.output_path is None
            or not realization.output_path.is_file()
        ):
            raise RuntimeError(
                "Bootstrap runtime-provider realization has no "
                "materialized regular file for packaging: "
                f"{canonical_entry.path!r}"
            )

        provider_data = (
            realization
            .output_path
            .read_bytes()
        )

        provider_digest = sha256_file(
            realization.output_path
        )

        if (
            realization.content_sha256 is None
            or provider_digest
            != realization.content_sha256
        ):
            raise RuntimeError(
                "Bootstrap runtime-provider realization changed "
                "before ramdisk packaging: "
                f"{canonical_entry.path!r}"
            )

        if (
            realization.runtime_provider_content_sha256 is None
            or provider_digest
            != realization.runtime_provider_content_sha256
        ):
            raise RuntimeError(
                "Bootstrap runtime-provider packaged payload does "
                "not match provider identity: "
                f"{canonical_entry.path!r}"
            )

        packaged_entries.append(
            CpioNewcEntry(
                path=canonical_entry.path,
                ino=canonical_entry.ino,
                mode=canonical_entry.mode,
                uid=canonical_entry.uid,
                gid=canonical_entry.gid,
                nlink=canonical_entry.nlink,
                mtime=canonical_entry.mtime,
                filesize=len(
                    provider_data
                ),
                devmajor=canonical_entry.devmajor,
                devminor=canonical_entry.devminor,
                rdevmajor=canonical_entry.rdevmajor,
                rdevminor=canonical_entry.rdevminor,
                namesize=canonical_entry.namesize,
                check=canonical_entry.check,
                data=provider_data,
            )
        )

        packaged_provider_substitutions += 1

    if (
        packaged_provider_substitutions
        != expected_provider_substitutions
    ):
        raise RuntimeError(
            "Bootstrap whole-ramdisk packaging did not carry every "
            "runtime-provider substitution forward: expected "
            f"{expected_provider_substitutions}, packaged "
            f"{packaged_provider_substitutions}"
        )

    # TREEFORGE_RECOVERY_RUNTIME_COMPOSITION_V1
    #
    # Provider files already represented by canonical Bootstrap
    # population entries were handled above. Recovery-only files are
    # appended under a private staging namespace solely so the early
    # dispatcher can retain their exact bytes through FreeRamdisk().
    existing_packaged_paths = {
        entry.path
        for entry in packaged_entries
    }

    next_runtime_ino = (
        max(
            (
                entry.ino
                for entry
                in packaged_entries
            ),
            default=0,
        )
        + 1
    )

    # RECOVERY_RUNTIME_STAGING_DIRECTORY_SPINE_V1
    #
    # The provider files live under a private initramfs staging tree.
    # CPIO newc does not imply parent-directory creation for regular-file
    # entries, so materialize the complete directory spine explicitly
    # before emitting any provider file.
    recovery_runtime_directory_paths = (
        "treeforge-recovery-provider",
        "treeforge-recovery-provider/system",
        "treeforge-recovery-provider/system/bin",
        "treeforge-recovery-provider/system/lib64",
    )

    staged_recovery_runtime_directory_count = 0

    for runtime_directory_path in (
        recovery_runtime_directory_paths
    ):
        if (
            runtime_directory_path
            in existing_packaged_paths
        ):
            continue

        ino = (
            next_runtime_ino
            + staged_recovery_runtime_directory_count
        )

        if ino > 0xffffffff:
            raise RuntimeError(
                "Recovery runtime staging directory inode "
                "exceeds CPIO newc range"
            )

        packaged_entries.append(
            CpioNewcEntry(
                path=runtime_directory_path,
                ino=ino,
                mode=0o040755,
                uid=0,
                gid=0,
                nlink=2,
                mtime=0,
                filesize=0,
                devmajor=0,
                devminor=0,
                rdevmajor=0,
                rdevminor=0,
                namesize=(
                    len(
                        runtime_directory_path.encode(
                            "utf-8"
                        )
                    )
                    + 1
                ),
                check=0,
                data=b"",
            )
        )

        existing_packaged_paths.add(
            runtime_directory_path
        )

        staged_recovery_runtime_directory_count += 1

    next_runtime_ino += (
        staged_recovery_runtime_directory_count
    )

    for index, runtime_file in enumerate(
        staged_recovery_runtime_files
    ):
        runtime_cpio_path = (
            runtime_file
            .staging_path
            .as_posix()
            .lstrip("/")
        )

        if runtime_cpio_path in existing_packaged_paths:
            raise RuntimeError(
                "Recovery runtime staging path collides with "
                "an existing ramdisk entry: "
                f"{runtime_cpio_path!r}"
            )

        provider_digest = sha256_file(
            runtime_file.source_path
        )

        if (
            provider_digest
            != runtime_file.content_sha256
        ):
            raise RuntimeError(
                "Recovery runtime provider changed before "
                "ramdisk packaging: "
                f"{runtime_file.android_path}"
            )

        provider_data = (
            runtime_file
            .source_path
            .read_bytes()
        )

        ino = (
            next_runtime_ino
            + index
        )

        if ino > 0xffffffff:
            raise RuntimeError(
                "Recovery runtime staging inode exceeds "
                "CPIO newc range"
            )

        packaged_entries.append(
            CpioNewcEntry(
                path=runtime_cpio_path,
                ino=ino,
                mode=(
                    0o100000
                    | runtime_file.mode
                ),
                uid=0,
                gid=0,
                nlink=1,
                mtime=0,
                filesize=len(
                    provider_data
                ),
                devmajor=0,
                devminor=0,
                rdevmajor=0,
                rdevminor=0,
                namesize=(
                    len(
                        runtime_cpio_path.encode(
                            "utf-8"
                        )
                    )
                    + 1
                ),
                check=0,
                data=provider_data,
            )
        )

        existing_packaged_paths.add(
            runtime_cpio_path
        )

    packaged_entries = tuple(
        packaged_entries
    )

    expected_packaged_entry_count = (
        len(
            canonical_interpretations
        )
        + staged_recovery_runtime_directory_count
        + len(
            staged_recovery_runtime_files
        )
    )

    if (
        len(packaged_entries)
        != expected_packaged_entry_count
    ):
        raise RuntimeError(
            "Bootstrap provider-aware whole-ramdisk packaging "
            "lost Recovery runtime composition entries: "
            f"expected {expected_packaged_entry_count}, "
            f"got {len(packaged_entries)}"
        )

    try:
        package = (
            AndroidBootImageRamdiskPackager()
            .package(
                packaged_entries,
                compression=compression,
                cpio_path=cpio_path,
                ramdisk_path=(
                    replacement_path
                ),
            )
        )
    except Exception as error:
        typer.echo(
            (
                "Unable to package Bootstrap replacement ramdisk: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    if not deployment.handoff.replacement_ready:
        typer.echo(
            "Bootstrap replacement ramdisk was not materialized.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    replacement = AndroidBootstrapBootImageReplacement(
        container_kind=(
            deployment
            .handoff
            .container_kind
        ),
        semantic_name=(
            deployment
            .handoff
            .semantic_name
        ),
        replacement_path=(
            package.ramdisk_path
        ),
        replacement_size_bytes=(
            package.ramdisk_size_bytes
        ),
        replacement_sha256=(
            package.ramdisk_sha256
        ),
        original_component_path=(
            deployment
            .handoff
            .original_component_path
        ),
        original_component_size_bytes=(
            deployment
            .handoff
            .original_component_size_bytes
        ),
        original_component_sha256=(
            deployment
            .handoff
            .original_component_sha256
        ),
        cpio_path=(
            package.cpio_path
        ),
        cpio_size_bytes=(
            package.cpio_size_bytes
        ),
        cpio_sha256=(
            package.cpio_sha256
        ),
        compression=(
            package
            .compression
            .value
        ),
        rollback_required=(
            deployment
            .handoff
            .rollback_required
        ),
    )

    manifest = (
        AndroidBootstrapBootImageHandoffManifest(
            parsing_snapshot_path=(
                snapshot_path
            ),
            parsing_snapshot_sha256=(
                sha256_file(
                    snapshot_path
                )
            ),
            replacements=(
                init_boot_replacement,
                replacement,
            ),
        )
    )

    try:
        manifest.validate_artifacts()

        manifest.write(
            handoff_path
        )
    except Exception as error:
        typer.echo(
            (
                "Unable to preserve Bootstrap Boot Image handoff: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    reports = render_bootstrap_reports(
        deployment,
        package=package,
        handoff_path=handoff_path,
    )

    report_paths = {}

    try:
        for filename, content in reports.items():
            report_path = (
                bootstrap_root
                / filename
            )

            report_path.write_text(
                content,
                encoding="utf-8",
            )

            report_paths[
                filename
            ] = report_path
    except OSError as error:
        typer.echo(
            (
                "Unable to preserve Bootstrap reports: "
                f"{error}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo()
    typer.echo(
        "Bootstrap environment:"
    )
    typer.echo(
        (
            "  Source: "
            f"{candidate.ramdisk.filesystem_source.source_name}"
        )
    )
    typer.echo(
        f"  Selected entries: {population.selected_count}"
    )
    typer.echo(
        f"  Preserved entries: {population.preserved_count}"
    )
    typer.echo(
        f"  ELF roots: {len(elf_closure.roots)}"
    )
    typer.echo(
        f"  ELFs: {len(elf_closure.elfs)}"
    )
    typer.echo(
        f"  ELF dependencies: {len(elf_closure.dependencies)}"
    )
    typer.echo(
        (
            "  ELF unresolved/ambiguous: "
            f"{elf_closure.unresolved_dependency_count}/"
            f"{elf_closure.ambiguous_dependency_count}"
        )
    )
    typer.echo(
        (
            "  Materialized entries: "
            f"{environment.materialized_count}"
        )
    )
    typer.echo(
        f"  Rootfs: {environment.rootfs}"
    )

    typer.echo()
    typer.echo(
        "Bootstrap early dispatcher:"
    )
    typer.echo(
        (
            "  Compiler: "
            f"{dispatcher.compiler_path}"
        )
    )
    typer.echo(
        (
            "  Target: "
            f"{dispatcher.target_triple}"
        )
    )
    typer.echo(
        (
            "  Executable: "
            f"{dispatcher.executable_path}"
        )
    )
    typer.echo(
        (
            "  init_boot replacement: "
            f"{init_boot_replacement.replacement_path}"
        )
    )
    typer.echo(
        (
            "  init_boot replacement SHA-256: "
            f"{init_boot_replacement.replacement_sha256}"
        )
    )

    typer.echo()
    typer.echo(
        "Bootstrap Boot Image handoff:"
    )
    typer.echo(
        (
            "  Target: "
            f"{replacement.container_kind}:"
            f"{replacement.semantic_name}"
        )
    )
    typer.echo(
        (
            "  Compression: "
            f"{replacement.compression}"
        )
    )
    typer.echo(
        (
            "  Replacement: "
            f"{replacement.replacement_path}"
        )
    )
    typer.echo(
        (
            "  Replacement SHA-256: "
            f"{replacement.replacement_sha256}"
        )
    )
    typer.echo(
        (
            "  Rollback required: "
            f"{str(replacement.rollback_required).lower()}"
        )
    )
    typer.echo(
        f"  Manifest: {handoff_path}"
    )

    typer.echo()
    typer.echo(
        "Bootstrap phase status:"
    )
    typer.echo(
        "  Intake: complete"
    )
    typer.echo(
        "  Environment Planning: complete"
    )
    typer.echo(
        "  Environment Realization: complete"
    )
    typer.echo(
        "  Deployment Planning: complete"
    )
    typer.echo(
        "  Device Deployment: pending Boot Image execution"
    )
    typer.echo(
        "  Hardware Validation / Rollback: pending"
    )

    typer.echo()
    typer.echo(
        "Bootstrap preparation completed successfully."
    )
    typer.echo(
        (
            "Report: "
            f"{report_paths['bootstrap-report.txt']}"
        )
    )
    typer.echo(
        (
            "Next: treeforge boot-image"
        )
    )


__all__ = (
    "app",
)
