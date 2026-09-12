from __future__ import annotations

from contextlib import redirect_stdout
from pathlib import Path
import io
import logging
import os
import shutil
import sys

import typer

from treeforge.android.application.parse_factory_image import (
    ParseFactoryImageRequest,
    ParseFactoryImageService,
)
from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
    parsing_snapshot_path,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceKind,
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
    build_extraction_stage_report_lines,
)
from treeforge.android.parsing.bootloader import (
    AndroidParsedBootFirmwarePayload,
)
from treeforge.android.parsing.sflb import (
    AndroidParsedSflbEntry,
)


app = typer.Typer(
    help=(
        "Run an Android factory image through TreeForge's canonical "
        "pipeline and stop after Parsing."
    )
)


@app.callback(
    invoke_without_command=True,
)
def parse(
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
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. Parsing workspace artifacts are "
            "preserved under OUTPUT/parsing. Defaults to ./output."
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
            "enrichment before Parsing."
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
    Run a factory image through TreeForge and stop at AndroidParsingResult.
    """

    typer.echo(
        "TreeForge Factory Image Parsing"
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

    parsing_root = (
        output
        / "parsing"
    )

    if (
        parsing_root.exists()
        and not parsing_root.is_dir()
    ):
        typer.echo(
            (
                "Parsing workspace exists but is not "
                f"a directory: {parsing_root}"
            ),
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    workspace = Workspace(
        parsing_root
    )

    canonical_snapshot = (
        parsing_snapshot_path(
            workspace
        )
    )

    restored_snapshot = None
    reparse = False

    if parsing_root.exists():
        typer.echo()
        typer.echo(
            "Existing Parsing snapshot was found:"
        )
        typer.echo(
            str(
                parsing_root
            )
        )
        typer.echo()

        if canonical_snapshot.is_file():
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
                            canonical_snapshot
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
                    "Using existing Parsing snapshot."
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

        else:
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
                    "Parsing cancelled. Existing output was preserved."
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

    if restored_snapshot is not None:
        parsing_result = (
            restored_snapshot.parsing
        )
        result = None

    else:
        if reparse and parsing_root.exists():
            try:
                shutil.rmtree(
                    parsing_root
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

        workspace = Workspace(
            parsing_root
        )

    if restored_snapshot is None:
        host_tools = AndroidHostTools()

        typer.echo()
        typer.echo(
            "Running factory image through TreeForge..."
        )

        try:
            result = (
                ParseFactoryImageService(
                    host_tools=host_tools,
                    progress_callback=render_progress,
                )
                .parse(
                    ParseFactoryImageRequest(
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
            typer.echo(
                (
                    "Factory-image Parsing failed: "
                    f"{error}"
                ),
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

        parsing_result = (
            result.parsing
        )

    source_inventory = (
        parsing_result.source_inventory
    )

    filesystem = (
        parsing_result.filesystem
    )

    elf = (
        parsing_result.elf
    )

    art_runtime = (
        parsing_result.art_runtime
    )

    standalone_dex = (
        parsing_result.dex
    )

    java_archive = (
        parsing_result.java_archive
    )

    apk = (
        parsing_result.apk
    )

    avf_vm_config = (
        parsing_result.avf_vm_config
    )

    kernel_modules = (
        parsing_result.kernel_modules
    )

    kernel_module_configurations = tuple(
        parsing_result.kernel_module_configurations
    )

    ramdisks = tuple(
        parsing_result.ramdisks
    )

    kernels = tuple(
        parsing_result.kernels
    )

    boot_images = tuple(
        parsing_result.boot_images
    )

    apex = tuple(
        sorted(
            parsing_result.apex,
            key=lambda parsed: (
                parsed.metadata.apex_name,
                parsed.metadata.version,
                parsed.metadata.artifact.path.as_posix(),
            ),
        )
    )

    bmp = tuple(
        sorted(
            parsing_result.bmp,
            key=lambda parsed: (
                parsed.artifact.path.as_posix()
            ),
        )
    )

    sflb = tuple(
        sorted(
            parsing_result.sflb,
            key=lambda parsed: (
                parsed.artifact.path.as_posix()
            ),
        )
    )

    property_sources = (
        source_inventory.sources_for(
            AndroidModelSourceKind.PROPERTY
        )
    )

    fstab_sources = (
        source_inventory.sources_for(
            AndroidModelSourceKind.FSTAB
        )
    )

    init_sources = (
        source_inventory.sources_for(
            AndroidModelSourceKind.INIT
        )
    )

    ueventd_sources = (
        source_inventory.sources_for(
            AndroidModelSourceKind.UEVENTD
        )
    )

    vintf_sources = (
        source_inventory.sources_for(
            AndroidModelSourceKind.VINTF
        )
    )

    property_declarations = sum(
        value.property_count
        for value in filesystem.property_files
    )

    fstab_entries = sum(
        value.entry_count
        for value in filesystem.fstabs
    )

    init_imports = sum(
        len(
            value.imports
        )
        for value in filesystem.init_files
    )

    init_services = sum(
        value.service_count
        for value in filesystem.init_files
    )

    init_actions = sum(
        value.action_count
        for value in filesystem.init_files
    )

    ueventd_declarations = sum(
        len(
            value.declarations
        )
        for value in filesystem.ueventd_files
    )

    linker_configurations = (
        parsing_result.linker_configurations
    )

    linker_sections = sum(
        len(
            source.sections
        )
        for source in linker_configurations
    )

    linker_assignments = sum(
        len(
            source.assignments
        )
        for source in linker_configurations
    )

    linker_unparsed_lines = sum(
        len(
            source.unparsed_lines
        )
        for source in linker_configurations
    )

    linker_protobuf_configurations = (
        parsing_result.linker_protobuf_configurations
    )

    linker_protobuf_permitted_paths = sum(
        len(
            source.permitted_paths
        )
        for source
        in linker_protobuf_configurations
    )

    linker_protobuf_visible_present = sum(
        1
        for source
        in linker_protobuf_configurations
        if source.visible_present
    )

    linker_protobuf_visible_true = sum(
        1
        for source
        in linker_protobuf_configurations
        if source.visible
    )

    linker_protobuf_provide_libs = sum(
        len(
            source.provide_libs
        )
        for source
        in linker_protobuf_configurations
    )

    linker_protobuf_require_libs = sum(
        len(
            source.require_libs
        )
        for source
        in linker_protobuf_configurations
    )

    linker_protobuf_contributions = sum(
        len(
            source.contributions
        )
        for source
        in linker_protobuf_configurations
    )

    linker_protobuf_unknown_fields = sum(
        len(
            source.unknown_fields
        )
        for source
        in linker_protobuf_configurations
    )

    linker_protobuf_unknown_contribution_fields = sum(
        len(
            contribution.unknown_fields
        )
        for source
        in linker_protobuf_configurations
        for contribution
        in source.contributions
    )

    classpath = (
        parsing_result.classpath
    )

    aconfig = (
        parsing_result.aconfig
    )

    native_library_configurations = (
        parsing_result.native_library_configurations
    )

    native_library_declarations = sum(
        len(
            source.declarations
        )
        for source
        in native_library_configurations
    )

    native_library_source_names = {
        source.source.source_name
        for source
        in native_library_configurations
    }

    report_buffer = io.StringIO()

    with redirect_stdout(
        report_buffer
    ):
        typer.echo()
        typer.echo(
            "Parsing completed successfully."
        )

        typer.echo()
        typer.echo(
            f"Factory image: {factory_image}"
        )
        typer.echo(
            f"Parsing workspace: {parsing_root}"
        )

        typer.echo()
        typer.echo(
            "Upstream pipeline:"
        )
        typer.echo(
            "  Discovery: complete"
        )
        typer.echo(
            "  Knowledge enrichment: "
            + (
                "skipped"
                if generic_only
                else "complete"
            )
        )
        typer.echo(
            "  Partition Layout: complete"
        )
        typer.echo(
            "  Extraction: complete"
        )
        typer.echo(
            "  Partition Inventory: complete"
        )
        typer.echo(
            "  Filesystem Metadata: complete"
        )
        typer.echo(
            "  Parsing: complete"
        )
        typer.echo(
            "  Parsing Snapshot: complete (schema 1)"
        )

        typer.echo()
        typer.echo(
            "Canonical upstream state:"
        )

        if result is not None:
            typer.echo(
                (
                    "  Discovered provider results: "
                    f"{len(result.discovery.discovery.provider_collection)}"
                )
            )
            typer.echo(
                (
                    "  Layout partitions: "
                    f"{len(result.partition_layout.partitions)}"
                )
            )

            context = (
                result.discovery.context
            )

            if context.android_extraction is not None:
                typer.echo(
                    (
                        "  Extraction artifacts: "
                        f"{len(context.android_extraction.artifacts)}"
                    )
                )

            if context.partition_inventory is not None:
                typer.echo(
                    (
                        "  Inventory partitions: "
                        f"{len(context.partition_inventory.partitions)}"
                    )
                )

            if context.filesystem_inventory is not None:
                typer.echo(
                    (
                        "  Filesystem metadata entries: "
                        f"{len(context.filesystem_inventory.entries)}"
                    )
                )

        else:
            typer.echo(
                (
                    "  Live upstream run state: "
                    "not present in Parsing snapshot"
                )
            )

        if (
            result is not None
            and context.android_extraction is not None
        ):
            typer.echo()

            for line in (
                build_extraction_stage_report_lines(
                    context.android_extraction
                )
            ):
                typer.echo(
                    line
                )

        typer.echo()
        selinux_sources = (
            filesystem.selinux_sources
        )

        selinux_source_paths = {
            source.source_path
            for source in selinux_sources
        }

        selinux_kind_counts: dict[
            str,
            int,
        ] = {}

        for source in selinux_sources:
            kind = source.parsed.kind.value

            selinux_kind_counts[kind] = (
                selinux_kind_counts.get(
                    kind,
                    0,
                )
                + 1
            )

        selinux_context_declarations = sum(
            len(
                source.parsed.context_declarations
            )
            for source in selinux_sources
        )

        selinux_seapp_declarations = sum(
            len(
                source.parsed.seapp_declarations
            )
            for source in selinux_sources
        )

        selinux_cil_forms = tuple(
            form
            for source in selinux_sources
            for form in source.parsed.cil_forms
        )

        selinux_cil_form_names = {
            form.name
            for form in selinux_cil_forms
        }

        selinux_metadata_text_lines = sum(
            len(
                source.parsed.text_lines
            )
            for source in selinux_sources
        )

        selinux_unparsed_lines = sum(
            len(
                source.parsed.unparsed_lines
            )
            for source in selinux_sources
        )

        selinux_opaque_sources = tuple(
            source
            for source in selinux_sources
            if source.parsed.is_opaque
        )

        selinux_ramdisk_sources = tuple(
            source
            for source in source_inventory.sources
            if (
                source.host_path
                in selinux_source_paths
                and source.filesystem_source.partition
                is None
            )
        )

        typer.echo(
            "Filesystem Parsing:"
        )
        typer.echo(
            (
                "  Property sources: "
                f"{len(property_sources)}"
            )
        )
        typer.echo(
            (
                "  Property declarations: "
                f"{property_declarations}"
            )
        )
        typer.echo(
            (
                "  Fstab sources: "
                f"{len(fstab_sources)}"
            )
        )
        typer.echo(
            (
                "  Fstab entries: "
                f"{fstab_entries}"
            )
        )
        typer.echo(
            (
                "  Init RC sources: "
                f"{len(init_sources)}"
            )
        )
        typer.echo(
            (
                "  Init imports: "
                f"{init_imports}"
            )
        )
        typer.echo(
            (
                "  Init services: "
                f"{init_services}"
            )
        )
        typer.echo(
            (
                "  Init actions: "
                f"{init_actions}"
            )
        )
        typer.echo(
            (
                "  Ueventd sources: "
                f"{len(ueventd_sources)}"
            )
        )
        typer.echo(
            (
                "  Ueventd declarations: "
                f"{ueventd_declarations}"
            )
        )
        typer.echo(
            (
                "  VINTF sources: "
                f"{len(vintf_sources)}"
            )
        )
        typer.echo(
            (
                "  VINTF documents: "
                f"{len(filesystem.vintf_documents)}"
            )
        )

        typer.echo()
        typer.echo(
            "Linker Configuration Parsing:"
        )
        typer.echo(
            (
                "  ld.config.txt sources: "
                f"{len(linker_configurations)}"
            )
        )
        typer.echo(
            (
                "  Sections: "
                f"{linker_sections}"
            )
        )
        typer.echo(
            (
                "  Assignments: "
                f"{linker_assignments}"
            )
        )
        typer.echo(
            (
                "  Meaningful unparsed lines: "
                f"{linker_unparsed_lines}"
            )
        )

        if linker_configurations:
            typer.echo(
                "  Parsed sources:"
            )

            for source in linker_configurations:
                typer.echo(
                    (
                        "    "
                        f"{source.source.source_name}:"
                        f"{source.source.android_path.as_posix()} "
                        f"sections={source.section_count} "
                        f"assignments={source.assignment_count} "
                        f"unparsed={len(source.unparsed_lines)}"
                    )
                )

        typer.echo()
        typer.echo(
            (
                "  linker.config.pb sources: "
                f"{len(linker_protobuf_configurations)}"
            )
        )
        typer.echo(
            (
                "  Protobuf permitted paths: "
                f"{linker_protobuf_permitted_paths}"
            )
        )
        typer.echo(
            (
                "  Protobuf visible field present: "
                f"{linker_protobuf_visible_present}"
            )
        )
        typer.echo(
            (
                "  Protobuf visible true: "
                f"{linker_protobuf_visible_true}"
            )
        )
        typer.echo(
            (
                "  Protobuf provide libs: "
                f"{linker_protobuf_provide_libs}"
            )
        )
        typer.echo(
            (
                "  Protobuf require libs: "
                f"{linker_protobuf_require_libs}"
            )
        )
        typer.echo(
            (
                "  Protobuf contributions: "
                f"{linker_protobuf_contributions}"
            )
        )
        typer.echo(
            (
                "  Protobuf unknown top-level fields: "
                f"{linker_protobuf_unknown_fields}"
            )
        )
        typer.echo(
            (
                "  Protobuf unknown contribution fields: "
                f"{linker_protobuf_unknown_contribution_fields}"
            )
        )

        if linker_protobuf_configurations:
            typer.echo(
                "  Parsed protobuf sources:"
            )

            for source in linker_protobuf_configurations:
                nested_unknown = sum(
                    len(
                        contribution.unknown_fields
                    )
                    for contribution
                    in source.contributions
                )

                typer.echo(
                    (
                        "    "
                        f"{source.source.source_name}:"
                        f"{source.source.android_path.as_posix()} "
                        f"permitted={len(source.permitted_paths)} "
                        f"visible={source.visible} "
                        "visible_present="
                        f"{source.visible_present} "
                        f"provides={len(source.provide_libs)} "
                        f"requires={len(source.require_libs)} "
                        f"contributions={len(source.contributions)} "
                        f"unknown={len(source.unknown_fields)} "
                        f"nested_unknown={nested_unknown}"
                    )
                )

        typer.echo()

        typer.echo(
            "Native-Library Configuration Parsing:"
        )
        typer.echo(
            (
                "  Sources: "
                f"{len(native_library_configurations)}"
            )
        )
        typer.echo(
            (
                "  Declarations: "
                f"{native_library_declarations}"
            )
        )
        typer.echo(
            (
                "  Canonical source roots: "
                f"{len(native_library_source_names)}"
            )
        )

        if native_library_configurations:
            typer.echo(
                "  Parsed sources:"
            )

            for source in native_library_configurations:
                typer.echo(
                    (
                        "    "
                        f"{source.source.source_name}:"
                        f"{source.source.android_path.as_posix()} "
                        "declarations="
                        f"{source.declaration_count}"
                    )
                )

        typer.echo()

        typer.echo(
            "ELF Parsing:"
        )
        typer.echo(
            (
                "  ELF files: "
                f"{elf.count}"
            )
        )
        typer.echo(
            (
                "  Filesystem ELF files: "
                f"{elf.filesystem_elf_count}"
            )
        )
        typer.echo(
            (
                "  Extraction ELF files: "
                f"{elf.extraction_elf_count}"
            )
        )
        typer.echo(
            (
                "  ELF32: "
                f"{elf.elf32_count}"
            )
        )
        typer.echo(
            (
                "  ELF64: "
                f"{elf.elf64_count}"
            )
        )
        typer.echo(
            (
                "  Machines: "
                + (
                    ", ".join(
                        elf.machines
                    )
                    if elf.machines
                    else "none"
                )
            )
        )

        elf_files_with_soong_intermediate_components = sum(
            1
            for parsed_elf in elf.elf_files
            if parsed_elf.soong_intermediate_components
        )

        soong_build_tuple_observations = sum(
            len(
                parsed_elf.soong_intermediate_components
            )
            for parsed_elf in elf.elf_files
        )

        distinct_soong_intermediate_components = {
            value
            for parsed_elf in elf.elf_files
            for value in parsed_elf.soong_intermediate_components
        }

        typer.echo(
            (
                "  ELFs with Soong intermediate components: "
                f"{elf_files_with_soong_intermediate_components}"
            )
        )
        typer.echo(
            (
                "  Soong intermediate component observations: "
                f"{soong_build_tuple_observations}"
            )
        )
        typer.echo(
            (
                "  Distinct Soong intermediate components: "
                f"{len(distinct_soong_intermediate_components)}"
            )
        )

        elf_files_with_comments = sum(
            1
            for parsed_elf in elf.elf_files
            if parsed_elf.comments
        )

        elf_note_sections = sum(
            len(
                parsed_elf.note_sections
            )
            for parsed_elf in elf.elf_files
        )

        elf_note_records = sum(
            len(
                section.notes
            )
            for parsed_elf in elf.elf_files
            for section in parsed_elf.note_sections
        )

        elf_attribute_sections = sum(
            len(
                parsed_elf.attribute_sections
            )
            for parsed_elf in elf.elf_files
        )

        elf_attribute_records = sum(
            len(
                section.attributes
            )
            for parsed_elf in elf.elf_files
            for section in parsed_elf.attribute_sections
        )

        typer.echo(
            (
                "  ELFs with comments: "
                f"{elf_files_with_comments}"
            )
        )
        typer.echo(
            (
                "  ELF note sections: "
                f"{elf_note_sections}"
            )
        )
        typer.echo(
            (
                "  ELF note records: "
                f"{elf_note_records}"
            )
        )
        typer.echo(
            (
                "  ELF attribute sections: "
                f"{elf_attribute_sections}"
            )
        )
        typer.echo(
            (
                "  ELF attribute records: "
                f"{elf_attribute_records}"
            )
        )

        if elf.extraction_elf_files:
            typer.echo(
                "  Extraction ELF lineage:"
            )

            for parsed_elf in (
                elf.extraction_elf_files
            ):
                source = (
                    parsed_elf.source
                )

                artifact = (
                    source.extraction_artifact
                )

                assert artifact is not None

                parent = (
                    artifact.parent
                )

                typer.echo(
                    (
                        "    "
                        f"{artifact.semantic_name or artifact.path.name}: "
                        f"{parsed_elf.elf_class.value} "
                        f"{parsed_elf.machine} "
                        f"{parsed_elf.elf_type}"
                    )
                )

                typer.echo(
                    (
                        "      parent: "
                        f"{parent.semantic_name or parent.path.name}"
                        if parent is not None
                        else "      parent: none"
                    )
                )

                typer.echo(
                    (
                        "      artifact: "
                        f"{artifact.path}"
                    )
                )

        typer.echo()
        typer.echo(
            "ART Runtime Parsing:"
        )

        typer.echo(
            (
                "  ART-runtime observations: "
                f"{art_runtime.count}"
            )
        )

        typer.echo(
            (
                "  OAT files: "
                f"{art_runtime.oat_count}"
            )
        )

        typer.echo(
            (
                "  VDEX files: "
                f"{art_runtime.vdex_count}"
            )
        )

        typer.echo(
            (
                "  ART images: "
                f"{art_runtime.art_image_count}"
            )
        )

        #
        # VDEX-contained DEX structural observations.
        #
        # These summarize only physical DEX payloads carried by supported
        # VDEX layouts. VDEX checksum-table entries remain separate identity
        # evidence and are not treated as physical DEX payloads by themselves.
        #
        vdex_with_dex_section = tuple(
            parsed
            for parsed
            in art_runtime.vdex_files
            if (
                parsed.vdex_027 is not None
                and parsed.vdex_027.has_dex_section
            )
        )

        vdex_contained_dex = tuple(
            dex
            for parsed
            in vdex_with_dex_section
            for dex
            in parsed.vdex_027.dex_files
        )

        vdex_contained_dex_expected = sum(
            parsed.vdex_027.dex_file_count
            for parsed
            in vdex_with_dex_section
        )

        vdex_contained_dex_unresolved = (
            vdex_contained_dex_expected
            - len(
                vdex_contained_dex
            )
        )

        typer.echo(
            (
                "  VDEX files with physical DEX section: "
                f"{len(vdex_with_dex_section)}"
            )
        )

        typer.echo(
            (
                "  VDEX-contained DEX expected: "
                f"{vdex_contained_dex_expected}"
            )
        )

        typer.echo(
            (
                "  VDEX-contained DEX decoded: "
                f"{len(vdex_contained_dex)}"
            )
        )

        typer.echo(
            (
                "  VDEX-contained DEX unresolved: "
                f"{vdex_contained_dex_unresolved}"
            )
        )

        #
        # OatDexFile structural observations.
        #
        # These are presentation-only summaries over exact Parsing evidence.
        # Do not canonicalize locations or resolve them against artifacts here.
        #
        oat_dex_files = tuple(
            oat_dex_file
            for parsed
            in art_runtime.oat_files
            if parsed.header is not None
            for oat_dex_file
            in parsed.oat_dex_files
        )

        oat_dex_file_external_dex = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if (
                oat_dex_file.dex_storage_disposition.value
                == "external_dex"
            )
        )

        oat_dex_file_dex_region_offset = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if (
                oat_dex_file.dex_storage_disposition.value
                == "dex_region_offset"
            )
        )

        dex_layout_sections_required = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if oat_dex_file.dex_layout_sections_offset != 0
        )

        dex_layout_sections_decoded = tuple(
            oat_dex_file
            for oat_dex_file
            in dex_layout_sections_required
            if oat_dex_file.dex_layout_sections is not None
        )

        dex_layout_sections_unresolved = tuple(
            oat_dex_file
            for oat_dex_file
            in dex_layout_sections_required
            if oat_dex_file.dex_layout_sections is None
        )

        class_offsets_required = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if oat_dex_file.class_offsets_offset != 0
        )

        lookup_tables_required = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if oat_dex_file.lookup_table_offset != 0
        )

        oat_bss_mapping_pairs = tuple(
            (
                offset,
                mapping,
            )
            for oat_dex_file
            in oat_dex_files
            for offset, mapping
            in (
                (
                    oat_dex_file.method_bss_mapping_offset,
                    oat_dex_file.method_bss_mapping,
                ),
                (
                    oat_dex_file.type_bss_mapping_offset,
                    oat_dex_file.type_bss_mapping,
                ),
                (
                    oat_dex_file.public_type_bss_mapping_offset,
                    oat_dex_file.public_type_bss_mapping,
                ),
                (
                    oat_dex_file.package_type_bss_mapping_offset,
                    oat_dex_file.package_type_bss_mapping,
                ),
                (
                    oat_dex_file.string_bss_mapping_offset,
                    oat_dex_file.string_bss_mapping,
                ),
                (
                    oat_dex_file.method_type_bss_mapping_offset,
                    oat_dex_file.method_type_bss_mapping,
                ),
            )
            if offset not in {
                None,
                0,
            }
        )

        oat_bss_mappings_required = len(
            oat_bss_mapping_pairs
        )

        oat_bss_mappings_decoded = tuple(
            mapping
            for _, mapping
            in oat_bss_mapping_pairs
            if mapping is not None
        )

        oat_bss_mapping_entries = sum(
            mapping.entry_count
            for mapping
            in oat_bss_mappings_decoded
        )

        bcp_bss_headers = tuple(
            parsed.header
            for parsed
            in art_runtime.oat_files
            if (
                parsed.header is not None
                and parsed.header.bcp_bss_info_offset != 0
            )
        )

        bcp_bss_decoded = tuple(
            header.bcp_bss_info
            for header
            in bcp_bss_headers
            if header.bcp_bss_info is not None
        )

        bcp_bss_records = tuple(
            record
            for info
            in bcp_bss_decoded
            for record
            in info.records
        )

        bcp_bss_mapping_pairs = tuple(
            (
                offset,
                mapping,
            )
            for record
            in bcp_bss_records
            for offset, mapping
            in (
                (
                    record.method_bss_mapping_offset,
                    record.method_bss_mapping,
                ),
                (
                    record.type_bss_mapping_offset,
                    record.type_bss_mapping,
                ),
                (
                    record.public_type_bss_mapping_offset,
                    record.public_type_bss_mapping,
                ),
                (
                    record.package_type_bss_mapping_offset,
                    record.package_type_bss_mapping,
                ),
                (
                    record.string_bss_mapping_offset,
                    record.string_bss_mapping,
                ),
                (
                    record.method_type_bss_mapping_offset,
                    record.method_type_bss_mapping,
                ),
            )
            if offset not in {
                None,
                0,
            }
        )

        bcp_bss_mappings_decoded = tuple(
            mapping
            for _, mapping
            in bcp_bss_mapping_pairs
            if mapping is not None
        )

        bcp_bss_mapping_entries = sum(
            mapping.entry_count
            for mapping
            in bcp_bss_mappings_decoded
        )

        oat_dex_file_locations = tuple(
            oat_dex_file.dex_file_location
            for oat_dex_file
            in oat_dex_files
        )

        oat_dex_file_unique_locations = {
            location
            for location
            in oat_dex_file_locations
        }

        oat_dex_file_multidex = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if "!" in oat_dex_file.dex_file_location
        )

        oat_dex_file_primary = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if "!" not in oat_dex_file.dex_file_location
        )

        oat_dex_file_zero_offset = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if oat_dex_file.dex_file_offset == 0
        )

        oat_dex_file_nonzero_offset = tuple(
            oat_dex_file
            for oat_dex_file
            in oat_dex_files
            if oat_dex_file.dex_file_offset != 0
        )

        oat_dex_file_magic_counts: dict[
            bytes,
            int,
        ] = {}

        for oat_dex_file in oat_dex_files:
            magic = (
                oat_dex_file.dex_file_magic
            )

            oat_dex_file_magic_counts[
                magic
            ] = (
                oat_dex_file_magic_counts.get(
                    magic,
                    0,
                )
                + 1
            )

        typer.echo(
            (
                "  OatDexFile records: "
                f"{len(oat_dex_files)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile external DEX storage: "
                f"{len(oat_dex_file_external_dex)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile DEX-region offsets: "
                f"{len(oat_dex_file_dex_region_offset)}"
            )
        )

        typer.echo(
            (
                "  DexLayoutSections required: "
                f"{len(dex_layout_sections_required)}"
            )
        )

        typer.echo(
            (
                "  DexLayoutSections decoded: "
                f"{len(dex_layout_sections_decoded)}"
            )
        )

        typer.echo(
            (
                "  DexLayoutSections unresolved: "
                f"{len(dex_layout_sections_unresolved)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile class-offset tables requiring "
                "proven DEX dimensions: "
                f"{len(class_offsets_required)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile lookup tables requiring "
                "proven DEX dimensions: "
                f"{len(lookup_tables_required)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile BSS mappings required: "
                f"{oat_bss_mappings_required}"
            )
        )

        typer.echo(
            (
                "  OatDexFile BSS mappings decoded: "
                f"{len(oat_bss_mappings_decoded)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile BSS mapping entries: "
                f"{oat_bss_mapping_entries}"
            )
        )

        typer.echo(
            (
                "  BCP BSS info pointers present: "
                f"{len(bcp_bss_headers)}"
            )
        )

        typer.echo(
            (
                "  BCP BSS info decoded: "
                f"{len(bcp_bss_decoded)}"
            )
        )

        typer.echo(
            (
                "  BCP BSS info deferred pending proven "
                "serialized target contract: "
                f"{len(bcp_bss_headers) - len(bcp_bss_decoded)}"
            )
        )

        typer.echo(
            (
                "  BCP BSS records: "
                f"{len(bcp_bss_records)}"
            )
        )

        typer.echo(
            (
                "  BCP BSS mappings required: "
                f"{len(bcp_bss_mapping_pairs)}"
            )
        )

        typer.echo(
            (
                "  BCP BSS mappings decoded: "
                f"{len(bcp_bss_mappings_decoded)}"
            )
        )

        typer.echo(
            (
                "  BCP BSS mapping entries: "
                f"{bcp_bss_mapping_entries}"
            )
        )

        typer.echo(
            (
                "  OatDexFile unique locations: "
                f"{len(oat_dex_file_unique_locations)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile primary locations: "
                f"{len(oat_dex_file_primary)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile multidex locations: "
                f"{len(oat_dex_file_multidex)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile zero DEX offsets: "
                f"{len(oat_dex_file_zero_offset)}"
            )
        )

        typer.echo(
            (
                "  OatDexFile nonzero DEX offsets: "
                f"{len(oat_dex_file_nonzero_offset)}"
            )
        )

        if oat_dex_file_magic_counts:
            typer.echo(
                "  OatDexFile DEX magic:"
            )

            for magic, count in sorted(
                oat_dex_file_magic_counts.items(),
                key=lambda item: (
                    item[0]
                ),
            ):
                if magic.startswith(
                    b"dex\n"
                ):
                    version = (
                        magic[4:]
                        .rstrip(
                            b"\x00"
                        )
                        .decode(
                            "ascii",
                            errors="replace",
                        )
                    )

                    label = (
                        "dex\\n"
                        + version
                    )

                elif magic.startswith(
                    b"cdex"
                ):
                    version = (
                        magic[4:]
                        .rstrip(
                            b"\x00"
                        )
                        .decode(
                            "ascii",
                            errors="replace",
                        )
                    )

                    label = (
                        "cdex"
                        + version
                    )

                else:
                    label = (
                        "0x"
                        + magic.hex()
                    )

                typer.echo(
                    (
                        "    "
                        f"{label}: "
                        f"{count}"
                    )
                )

        supported_oat = sum(
            1
            for parsed
            in art_runtime.oat_files
            if parsed.layout_supported
        )

        supported_vdex = sum(
            1
            for parsed
            in art_runtime.vdex_files
            if parsed.layout_supported
        )

        supported_art_images = sum(
            1
            for parsed
            in art_runtime.art_images
            if parsed.layout_supported
        )

        typer.echo(
            (
                "  Supported OAT layouts: "
                f"{supported_oat}"
            )
        )

        typer.echo(
            (
                "  Supported VDEX layouts: "
                f"{supported_vdex}"
            )
        )

        typer.echo(
            (
                "  Supported ART image layouts: "
                f"{supported_art_images}"
            )
        )

        oat_versions: dict[
            str,
            int,
        ] = {}

        vdex_versions: dict[
            str,
            int,
        ] = {}

        art_image_versions: dict[
            str,
            int,
        ] = {}

        for parsed in art_runtime.oat_files:
            version = (
                parsed.version
                .rstrip(b"\x00")
                .decode(
                    "ascii",
                    errors="replace",
                )
            )

            oat_versions[
                version
            ] = (
                oat_versions.get(
                    version,
                    0,
                )
                + 1
            )

        for parsed in art_runtime.vdex_files:
            version = (
                parsed.version
                .rstrip(b"\x00")
                .decode(
                    "ascii",
                    errors="replace",
                )
            )

            vdex_versions[
                version
            ] = (
                vdex_versions.get(
                    version,
                    0,
                )
                + 1
            )

        for parsed in art_runtime.art_images:
            version = (
                parsed.version
                .rstrip(b"\x00")
                .decode(
                    "ascii",
                    errors="replace",
                )
            )

            art_image_versions[
                version
            ] = (
                art_image_versions.get(
                    version,
                    0,
                )
                + 1
            )

        if oat_versions:
            typer.echo(
                "  OAT versions:"
            )

            for version in sorted(
                oat_versions
            ):
                typer.echo(
                    (
                        "    "
                        f"{version}: "
                        f"{oat_versions[version]}"
                    )
                )

        if vdex_versions:
            typer.echo(
                "  VDEX versions:"
            )

            for version in sorted(
                vdex_versions
            ):
                typer.echo(
                    (
                        "    "
                        f"{version}: "
                        f"{vdex_versions[version]}"
                    )
                )

        if art_image_versions:
            typer.echo(
                "  ART image versions:"
            )

            for version in sorted(
                art_image_versions
            ):
                typer.echo(
                    (
                        "    "
                        f"{version}: "
                        f"{art_image_versions[version]}"
                    )
                )

        oat_source_counts: dict[
            str,
            int,
        ] = {}

        vdex_source_counts: dict[
            str,
            int,
        ] = {}

        art_image_source_counts: dict[
            str,
            int,
        ] = {}

        for parsed in art_runtime.oat_files:
            source_name = (
                parsed.elf.source
                .source_name
            )

            oat_source_counts[
                source_name
            ] = (
                oat_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

        for parsed in art_runtime.vdex_files:
            source_name = (
                parsed.source
                .source_name
            )

            vdex_source_counts[
                source_name
            ] = (
                vdex_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

        for parsed in art_runtime.art_images:
            source_name = (
                parsed.source
                .source_name
            )

            art_image_source_counts[
                source_name
            ] = (
                art_image_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

        source_names = sorted(
            set(
                oat_source_counts
            )
            | set(
                vdex_source_counts
            )
            | set(
                art_image_source_counts
            )
        )

        if source_names:
            typer.echo(
                "  Canonical ART-runtime source roots:"
            )

            for source_name in source_names:
                typer.echo(
                    (
                        "    "
                        f"{source_name}: "
                        "oat="
                        f"{oat_source_counts.get(source_name, 0)} "
                        "vdex="
                        f"{vdex_source_counts.get(source_name, 0)} "
                        "art="
                        f"{art_image_source_counts.get(source_name, 0)}"
                    )
                )

        oat_key_values = sum(
            len(
                parsed.header.key_values
            )
            for parsed
            in art_runtime.oat_files
            if parsed.header is not None
        )

        vdex_dex_checksums = sum(
            len(
                parsed.vdex_027.dex_checksums
            )
            for parsed
            in art_runtime.vdex_files
            if parsed.vdex_027 is not None
        )

        art_image_sections = sum(
            len(
                parsed.image_111.sections
            )
            for parsed
            in art_runtime.art_images
            if parsed.image_111 is not None
        )

        typer.echo(
            (
                "  OAT key/value entries: "
                f"{oat_key_values}"
            )
        )

        typer.echo(
            (
                "  VDEX DEX checksums: "
                f"{vdex_dex_checksums}"
            )
        )

        typer.echo(
            (
                "  ART image sections: "
                f"{art_image_sections}"
            )
        )

        typer.echo()
        typer.echo(
            "Classpath Configuration Parsing:"
        )

        typer.echo(
            (
                "  Sources: "
                f"{classpath.source_count}"
            )
        )

        typer.echo(
            (
                "  JAR declarations: "
                f"{classpath.jar_count}"
            )
        )

        typer.echo(
            (
                "  Unknown protobuf fields: "
                f"{classpath.unknown_field_count}"
            )
        )

        classpath_kind_counts: dict[
            str,
            int,
        ] = {}

        classpath_unknown_kind_counts: dict[
            int,
            int,
        ] = {}

        classpath_filename_counts: dict[
            str,
            int,
        ] = {}

        classpath_source_counts: dict[
            str,
            int,
        ] = {}

        min_sdk_count = 0
        max_sdk_count = 0

        for parsed in classpath.configurations:
            filename = (
                parsed.source.android_path.name
            )

            classpath_filename_counts[
                filename
            ] = (
                classpath_filename_counts.get(
                    filename,
                    0,
                )
                + 1
            )

            source_name = (
                parsed.source.source_name
            )

            classpath_source_counts[
                source_name
            ] = (
                classpath_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

            for jar in parsed.jars:
                if jar.min_sdk_version_present:
                    min_sdk_count += 1

                if jar.max_sdk_version_present:
                    max_sdk_count += 1

                known = (
                    jar.known_classpath
                )

                if known is None:
                    classpath_unknown_kind_counts[
                        jar.classpath_value
                    ] = (
                        classpath_unknown_kind_counts.get(
                            jar.classpath_value,
                            0,
                        )
                        + 1
                    )
                else:
                    classpath_kind_counts[
                        known.name
                    ] = (
                        classpath_kind_counts.get(
                            known.name,
                            0,
                        )
                        + 1
                    )

        if classpath_kind_counts:
            typer.echo(
                "  Classpath kinds:"
            )

            for kind in sorted(
                classpath_kind_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{kind}: "
                        f"{classpath_kind_counts[kind]}"
                    )
                )

        if classpath_unknown_kind_counts:
            typer.echo(
                "  Unknown classpath enum values:"
            )

            for value in sorted(
                classpath_unknown_kind_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{value}: "
                        f"{classpath_unknown_kind_counts[value]}"
                    )
                )

        typer.echo(
            (
                "  JARs with min_sdk_version: "
                f"{min_sdk_count}"
            )
        )

        typer.echo(
            (
                "  JARs with max_sdk_version: "
                f"{max_sdk_count}"
            )
        )

        if classpath_filename_counts:
            typer.echo(
                "  Source files:"
            )

            for filename in sorted(
                classpath_filename_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{filename}: "
                        f"{classpath_filename_counts[filename]}"
                    )
                )

        if classpath_source_counts:
            typer.echo(
                "  Canonical classpath source roots:"
            )

            for source_name in sorted(
                classpath_source_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{source_name}: "
                        f"{classpath_source_counts[source_name]}"
                    )
                )

        typer.echo()
        typer.echo(
            "Aconfig Parsing:"
        )

        typer.echo(
            (
                "  Sources: "
                f"{aconfig.source_count}"
            )
        )

        typer.echo(
            (
                "  Parsed flags: "
                f"{aconfig.flag_count}"
            )
        )

        typer.echo(
            (
                "  Tracepoints: "
                f"{aconfig.tracepoint_count}"
            )
        )

        typer.echo(
            (
                "  Unknown protobuf fields: "
                f"{aconfig.unknown_field_count}"
            )
        )

        aconfig_state_counts: dict[
            str,
            int,
        ] = {}

        aconfig_unknown_state_counts: dict[
            int,
            int,
        ] = {}

        aconfig_permission_counts: dict[
            str,
            int,
        ] = {}

        aconfig_unknown_permission_counts: dict[
            int,
            int,
        ] = {}

        aconfig_purpose_counts: dict[
            str,
            int,
        ] = {}

        aconfig_unknown_purpose_counts: dict[
            int,
            int,
        ] = {}

        aconfig_source_counts: dict[
            str,
            int,
        ] = {}

        aconfig_container_counts: dict[
            str,
            int,
        ] = {}

        aconfig_empty_source_count = 0

        package_present_count = 0
        name_present_count = 0
        namespace_present_count = 0
        description_present_count = 0
        state_present_count = 0
        permission_present_count = 0
        fixed_read_only_present_count = 0
        fixed_read_only_true_count = 0
        exported_present_count = 0
        exported_true_count = 0
        container_present_count = 0
        metadata_present_count = 0

        for parsed in aconfig.configurations:
            source_name = (
                parsed.source.source_name
            )

            aconfig_source_counts[
                source_name
            ] = (
                aconfig_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

            if not parsed.flags:
                aconfig_empty_source_count += 1

            for flag in parsed.flags:
                if flag.package_present:
                    package_present_count += 1

                if flag.name_present:
                    name_present_count += 1

                if flag.namespace_present:
                    namespace_present_count += 1

                if flag.description_present:
                    description_present_count += 1

                if flag.state_present:
                    state_present_count += 1

                    known_state = (
                        flag.known_state
                    )

                    if known_state is None:
                        aconfig_unknown_state_counts[
                            flag.state_value
                        ] = (
                            aconfig_unknown_state_counts.get(
                                flag.state_value,
                                0,
                            )
                            + 1
                        )
                    else:
                        aconfig_state_counts[
                            known_state.name
                        ] = (
                            aconfig_state_counts.get(
                                known_state.name,
                                0,
                            )
                            + 1
                        )

                if flag.permission_present:
                    permission_present_count += 1

                    known_permission = (
                        flag.known_permission
                    )

                    if known_permission is None:
                        aconfig_unknown_permission_counts[
                            flag.permission_value
                        ] = (
                            aconfig_unknown_permission_counts.get(
                                flag.permission_value,
                                0,
                            )
                            + 1
                        )
                    else:
                        aconfig_permission_counts[
                            known_permission.name
                        ] = (
                            aconfig_permission_counts.get(
                                known_permission.name,
                                0,
                            )
                            + 1
                        )

                if flag.is_fixed_read_only_present:
                    fixed_read_only_present_count += 1

                    if flag.is_fixed_read_only:
                        fixed_read_only_true_count += 1

                if flag.is_exported_present:
                    exported_present_count += 1

                    if flag.is_exported:
                        exported_true_count += 1

                if flag.container_present:
                    container_present_count += 1

                    aconfig_container_counts[
                        flag.container
                    ] = (
                        aconfig_container_counts.get(
                            flag.container,
                            0,
                        )
                        + 1
                    )

                if flag.metadata_present:
                    metadata_present_count += 1

                    metadata = (
                        flag.metadata
                    )

                    if (
                        metadata is not None
                        and metadata.purpose_present
                    ):
                        known_purpose = (
                            metadata.known_purpose
                        )

                        if known_purpose is None:
                            aconfig_unknown_purpose_counts[
                                metadata.purpose_value
                            ] = (
                                aconfig_unknown_purpose_counts.get(
                                    metadata.purpose_value,
                                    0,
                                )
                                + 1
                            )
                        else:
                            aconfig_purpose_counts[
                                known_purpose.name
                            ] = (
                                aconfig_purpose_counts.get(
                                    known_purpose.name,
                                    0,
                                )
                                + 1
                            )

        if aconfig_state_counts:
            typer.echo(
                "  Flag states:"
            )

            for name in sorted(
                aconfig_state_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{name}: "
                        f"{aconfig_state_counts[name]}"
                    )
                )

        if aconfig_unknown_state_counts:
            typer.echo(
                "  Unknown flag state values:"
            )

            for value in sorted(
                aconfig_unknown_state_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{value}: "
                        f"{aconfig_unknown_state_counts[value]}"
                    )
                )

        if aconfig_permission_counts:
            typer.echo(
                "  Flag permissions:"
            )

            for name in sorted(
                aconfig_permission_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{name}: "
                        f"{aconfig_permission_counts[name]}"
                    )
                )

        if aconfig_unknown_permission_counts:
            typer.echo(
                "  Unknown flag permission values:"
            )

            for value in sorted(
                aconfig_unknown_permission_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{value}: "
                        f"{aconfig_unknown_permission_counts[value]}"
                    )
                )

        if aconfig_purpose_counts:
            typer.echo(
                "  Metadata purposes:"
            )

            for name in sorted(
                aconfig_purpose_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{name}: "
                        f"{aconfig_purpose_counts[name]}"
                    )
                )

        if aconfig_unknown_purpose_counts:
            typer.echo(
                "  Unknown metadata purpose values:"
            )

            for value in sorted(
                aconfig_unknown_purpose_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{value}: "
                        f"{aconfig_unknown_purpose_counts[value]}"
                    )
                )

        typer.echo(
            (
                "  Empty sources: "
                f"{aconfig_empty_source_count}"
            )
        )

        typer.echo(
            (
                "  package present: "
                f"{package_present_count}"
            )
        )

        typer.echo(
            (
                "  name present: "
                f"{name_present_count}"
            )
        )

        typer.echo(
            (
                "  namespace present: "
                f"{namespace_present_count}"
            )
        )

        typer.echo(
            (
                "  description present: "
                f"{description_present_count}"
            )
        )

        typer.echo(
            (
                "  state present: "
                f"{state_present_count}"
            )
        )

        typer.echo(
            (
                "  permission present: "
                f"{permission_present_count}"
            )
        )

        typer.echo(
            (
                "  is_fixed_read_only present: "
                f"{fixed_read_only_present_count}"
            )
        )

        typer.echo(
            (
                "  is_fixed_read_only true: "
                f"{fixed_read_only_true_count}"
            )
        )

        typer.echo(
            (
                "  is_exported present: "
                f"{exported_present_count}"
            )
        )

        typer.echo(
            (
                "  is_exported true: "
                f"{exported_true_count}"
            )
        )

        typer.echo(
            (
                "  container present: "
                f"{container_present_count}"
            )
        )

        typer.echo(
            (
                "  metadata present: "
                f"{metadata_present_count}"
            )
        )

        if aconfig_container_counts:
            typer.echo(
                "  Declared containers:"
            )

            for container in sorted(
                aconfig_container_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{container}: "
                        f"{aconfig_container_counts[container]}"
                    )
                )

        if aconfig_source_counts:
            typer.echo(
                "  Canonical aconfig source roots:"
            )

            for source_name in sorted(
                aconfig_source_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{source_name}: "
                        f"{aconfig_source_counts[source_name]}"
                    )
                )

        apk_packages = (
            apk.packages
        )

        apk_overlay_packages = tuple(
            parsed
            for parsed in apk_packages
            if parsed.overlay is not None
        )

        apk_version_code_present = sum(
            1
            for parsed in apk_packages
            if parsed.version_code is not None
        )

        apk_version_code_literal = sum(
            1
            for parsed in apk_packages
            if (
                parsed.version_code is not None
                and parsed.version_code.literal is not None
            )
        )

        apk_version_name_present = sum(
            1
            for parsed in apk_packages
            if parsed.version_name is not None
        )

        apk_version_name_literal = sum(
            1
            for parsed in apk_packages
            if (
                parsed.version_name is not None
                and parsed.version_name.literal is not None
            )
        )

        apk_overlay_target_present = sum(
            1
            for parsed in apk_overlay_packages
            if (
                parsed.overlay is not None
                and parsed.overlay.target_package is not None
            )
        )

        apk_overlay_target_literal = sum(
            1
            for parsed in apk_overlay_packages
            if (
                parsed.overlay is not None
                and parsed.overlay.target_package is not None
                and parsed.overlay.target_package.literal is not None
            )
        )

        apk_overlay_priority_present = sum(
            1
            for parsed in apk_overlay_packages
            if (
                parsed.overlay is not None
                and parsed.overlay.priority is not None
            )
        )

        apk_overlay_priority_literal = sum(
            1
            for parsed in apk_overlay_packages
            if (
                parsed.overlay is not None
                and parsed.overlay.priority is not None
                and parsed.overlay.priority.literal is not None
            )
        )

        apk_overlay_static_present = sum(
            1
            for parsed in apk_overlay_packages
            if (
                parsed.overlay is not None
                and parsed.overlay.is_static is not None
            )
        )

        apk_overlay_static_literal = sum(
            1
            for parsed in apk_overlay_packages
            if (
                parsed.overlay is not None
                and parsed.overlay.is_static is not None
                and parsed.overlay.is_static.literal is not None
            )
        )

        apk_source_counts: dict[
            str,
            int,
        ] = {}

        for parsed in apk_packages:
            source_name = (
                parsed.source.source_name
            )

            apk_source_counts[
                source_name
            ] = (
                apk_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

        typer.echo()
        typer.echo(
            "Standalone DEX Parsing:"
        )

        typer.echo(
            (
                "  Sources: "
                f"{standalone_dex.source_count}"
            )
        )

        typer.echo(
            (
                "  Standard DEX decoded: "
                f"{standalone_dex.parsed_count}"
            )
        )

        typer.echo(
            (
                "  CompactDex preserved unsupported: "
                f"{standalone_dex.compact_dex_count}"
            )
        )

        typer.echo(
            (
                "  Unresolved: "
                f"{standalone_dex.unresolved_count}"
            )
        )

        typer.echo()
        typer.echo(
            "Java Archive Parsing:"
        )

        typer.echo(
            (
                "  Archives: "
                f"{java_archive.source_count}"
            )
        )

        typer.echo(
            (
                "  Members: "
                f"{java_archive.member_count}"
            )
        )

        typer.echo(
            (
                "  DEX members discovered: "
                f"{java_archive.dex_member_count}"
            )
        )

        typer.echo(
            (
                "  DEX files decoded: "
                f"{java_archive.dex_count}"
            )
        )

        typer.echo(
            (
                "  DEX unresolved: "
                f"{java_archive.unresolved_dex_count}"
            )
        )

        typer.echo(
            (
                "  Multidex archives: "
                f"{java_archive.multidex_count}"
            )
        )

        typer.echo(
            (
                "  Manifests: "
                f"{java_archive.manifest_count}"
            )
        )

        typer.echo()
        typer.echo(
            "APK Package Identity Parsing:"
        )

        typer.echo(
            (
                "  Packages: "
                f"{len(apk_packages)}"
            )
        )

        typer.echo(
            (
                "  ZIP members: "
                f"{apk.member_count}"
            )
        )

        typer.echo(
            (
                "  DEX members discovered: "
                f"{apk.dex_member_count}"
            )
        )

        typer.echo(
            (
                "  DEX files decoded: "
                f"{apk.dex_count}"
            )
        )

        typer.echo(
            (
                "  DEX unresolved: "
                f"{apk.unresolved_dex_count}"
            )
        )

        typer.echo(
            (
                "  APKs containing DEX: "
                f"{apk.dex_package_count}"
            )
        )

        typer.echo(
            (
                "  Multidex APKs: "
                f"{apk.multidex_package_count}"
            )
        )

        canonical_physical_dex_total = (
            java_archive.dex_count
            + apk.dex_count
            + len(
                vdex_contained_dex
            )
            + standalone_dex.parsed_count
        )

        typer.echo()
        typer.echo(
            "Canonical Physical Standard DEX Census:"
        )

        typer.echo(
            (
                "  Java archive DEX: "
                f"{java_archive.dex_count}"
            )
        )

        typer.echo(
            (
                "  APK DEX: "
                f"{apk.dex_count}"
            )
        )

        typer.echo(
            (
                "  VDEX-contained DEX: "
                f"{len(vdex_contained_dex)}"
            )
        )

        typer.echo(
            (
                "  Standalone filesystem DEX: "
                f"{standalone_dex.parsed_count}"
            )
        )

        typer.echo(
            (
                "  Total physical standard DEX: "
                f"{canonical_physical_dex_total}"
            )
        )

        typer.echo(
            (
                "  Preserved CompactDex outside standard total: "
                f"{standalone_dex.compact_dex_count}"
            )
        )

        typer.echo(
            (
                "  Unresolved standard DEX: "
                f"{(
                    java_archive.unresolved_dex_count
                    + apk.unresolved_dex_count
                    + vdex_contained_dex_unresolved
                    + standalone_dex.unresolved_count
                )}"
            )
        )

        typer.echo(
            (
                "  Literal package names: "
                f"{sum(
                    1
                    for parsed in apk_packages
                    if isinstance(
                        parsed.package_name.literal,
                        str,
                    )
                )}"
            )
        )

        typer.echo(
            (
                "  Runtime resource overlays: "
                f"{len(apk_overlay_packages)}"
            )
        )

        typer.echo(
            (
                "  versionCode present: "
                f"{apk_version_code_present}"
            )
        )

        typer.echo(
            (
                "  versionCode literal: "
                f"{apk_version_code_literal}"
            )
        )

        typer.echo(
            (
                "  versionCode resource-referenced/typed: "
                f"{(
                    apk_version_code_present
                    - apk_version_code_literal
                )}"
            )
        )

        typer.echo(
            (
                "  versionName present: "
                f"{apk_version_name_present}"
            )
        )

        typer.echo(
            (
                "  versionName literal: "
                f"{apk_version_name_literal}"
            )
        )

        typer.echo(
            (
                "  versionName resource-referenced/typed: "
                f"{(
                    apk_version_name_present
                    - apk_version_name_literal
                )}"
            )
        )

        typer.echo(
            "  Overlay declarations:"
        )

        typer.echo(
            (
                "    targetPackage present: "
                f"{apk_overlay_target_present}"
            )
        )

        typer.echo(
            (
                "    targetPackage literal: "
                f"{apk_overlay_target_literal}"
            )
        )

        typer.echo(
            (
                "    targetPackage resource-referenced/typed: "
                f"{(
                    apk_overlay_target_present
                    - apk_overlay_target_literal
                )}"
            )
        )

        typer.echo(
            (
                "    priority present: "
                f"{apk_overlay_priority_present}"
            )
        )

        typer.echo(
            (
                "    priority literal: "
                f"{apk_overlay_priority_literal}"
            )
        )

        typer.echo(
            (
                "    priority resource-referenced/typed: "
                f"{(
                    apk_overlay_priority_present
                    - apk_overlay_priority_literal
                )}"
            )
        )

        typer.echo(
            (
                "    isStatic present: "
                f"{apk_overlay_static_present}"
            )
        )

        typer.echo(
            (
                "    isStatic literal: "
                f"{apk_overlay_static_literal}"
            )
        )

        typer.echo(
            (
                "    isStatic resource-referenced/typed: "
                f"{(
                    apk_overlay_static_present
                    - apk_overlay_static_literal
                )}"
            )
        )

        if apk_source_counts:
            typer.echo(
                "  Canonical APK source roots:"
            )

            for source_name in sorted(
                apk_source_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{source_name}: "
                        f"{apk_source_counts[source_name]}"
                    )
                )

        typer.echo()
        typer.echo(
            "AVF VM Configuration Parsing:"
        )

        typer.echo(
            (
                "  Configurations: "
                f"{avf_vm_config.configuration_count}"
            )
        )

        typer.echo(
            (
                "  APEX declarations: "
                f"{sum(
                    len(parsed.apexes)
                    for parsed
                    in avf_vm_config.configurations
                )}"
            )
        )

        typer.echo(
            (
                "  Extra APK declarations: "
                f"{sum(
                    len(parsed.extra_apks)
                    for parsed
                    in avf_vm_config.configurations
                )}"
            )
        )

        typer.echo(
            (
                "  Unknown top-level fields: "
                f"{sum(
                    len(parsed.unknown_fields)
                    for parsed
                    in avf_vm_config.configurations
                )}"
            )
        )

        if avf_vm_config.configurations:
            typer.echo(
                "  Parsed configurations:"
            )

            for parsed in (
                avf_vm_config.configurations
            ):
                typer.echo(
                    (
                        "    "
                        f"{parsed.source.source_name}:"
                        f"{parsed.source.apk_android_path.as_posix()}"
                        "!"
                        f"{parsed.source.member_path}"
                    )
                )

                typer.echo(
                    (
                        "      version: "
                        f"{parsed.version}"
                    )
                )

                typer.echo(
                    (
                        "      guest OS: "
                        f"{parsed.os.name}"
                    )
                )

                typer.echo(
                    (
                        "      task type: "
                        f"{parsed.task.task_type}"
                    )
                )

                typer.echo(
                    (
                        "      task command: "
                        f"{parsed.task.command}"
                    )
                )

                typer.echo(
                    (
                        "      prefer staged: "
                        f"{parsed.prefer_staged}"
                    )
                )

                typer.echo(
                    (
                        "      APEX declarations: "
                        f"{len(parsed.apexes)}"
                    )
                )

                for apex_entry in parsed.apexes:
                    typer.echo(
                        (
                            "        "
                            f"{apex_entry.name}"
                        )
                    )

                typer.echo(
                    (
                        "      extra APK declarations: "
                        f"{len(parsed.extra_apks)}"
                    )
                )

                for apk_entry in parsed.extra_apks:
                    typer.echo(
                        (
                            "        "
                            f"{apk_entry.path}"
                        )
                    )

                typer.echo(
                    (
                        "      export tombstones: "
                        f"{parsed.export_tombstones}"
                    )
                )

                typer.echo(
                    (
                        "      enable authfs: "
                        f"{parsed.enable_authfs}"
                    )
                )

                typer.echo(
                    (
                        "      hugepages: "
                        f"{parsed.hugepages}"
                    )
                )

                if parsed.unknown_fields:
                    typer.echo(
                        (
                            "      unknown fields: "
                            + ", ".join(
                                parsed.unknown_fields
                            )
                        )
                    )

        typer.echo()
        typer.echo(
            "Kernel Module Parsing:"
        )

        typer.echo(
            (
                "  Kernel modules: "
                f"{kernel_modules.count}"
            )
        )

        typer.echo(
            (
                "  Modules with .modinfo: "
                f"{kernel_modules.modules_with_modinfo_count}"
            )
        )

        typer.echo(
            (
                "  .modinfo entries: "
                f"{kernel_modules.modinfo_entry_count}"
            )
        )

        module_source_counts: dict[
            str,
            int,
        ] = {}

        module_modinfo_source_counts: dict[
            str,
            int,
        ] = {}

        for module in kernel_modules.modules:
            source_name = (
                module.elf.source
                .source_name
            )

            module_source_counts[
                source_name
            ] = (
                module_source_counts.get(
                    source_name,
                    0,
                )
                + 1
            )

            if (
                module.modinfo_section_offset
                is not None
            ):
                module_modinfo_source_counts[
                    source_name
                ] = (
                    module_modinfo_source_counts.get(
                        source_name,
                        0,
                    )
                    + 1
                )

        if module_source_counts:
            typer.echo(
                "  Canonical module source roots:"
            )

            for source_name in sorted(
                module_source_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{source_name}: "
                        f"modules="
                        f"{module_source_counts[source_name]} "
                        "with_modinfo="
                        f"{module_modinfo_source_counts.get(source_name, 0)}"
                    )
                )

        typer.echo()
        typer.echo(
            "Kernel Module Configuration Parsing:"
        )

        typer.echo(
            (
                "  Sources: "
                f"{len(kernel_module_configurations)}"
            )
        )

        typer.echo(
            (
                "  Meaningful lines: "
                f"{sum(
                    parsed.line_count
                    for parsed
                    in kernel_module_configurations
                )}"
            )
        )

        configuration_kind_counts: dict[
            str,
            int,
        ] = {}

        configuration_line_counts: dict[
            str,
            int,
        ] = {}

        for parsed in (
            kernel_module_configurations
        ):
            kind = (
                parsed.configuration_kind
                .value
            )

            configuration_kind_counts[
                kind
            ] = (
                configuration_kind_counts.get(
                    kind,
                    0,
                )
                + 1
            )

            configuration_line_counts[
                kind
            ] = (
                configuration_line_counts.get(
                    kind,
                    0,
                )
                + parsed.line_count
            )

        if configuration_kind_counts:
            typer.echo(
                "  Configuration families:"
            )

            for kind in sorted(
                configuration_kind_counts
            ):
                typer.echo(
                    (
                        "    "
                        f"{kind}: "
                        "sources="
                        f"{configuration_kind_counts[kind]} "
                        "lines="
                        f"{configuration_line_counts[kind]}"
                    )
                )

        if kernel_module_configurations:
            typer.echo(
                "  Parsed sources:"
            )

            for parsed in (
                kernel_module_configurations
            ):
                typer.echo(
                    (
                        "    "
                        f"{parsed.source.source_name}:"
                        f"{parsed.source.android_path.as_posix()} "
                        f"kind={parsed.configuration_kind.value} "
                        f"lines={parsed.line_count}"
                    )
                )

        typer.echo()
        typer.echo(
            "APEX Parsing:"
        )
        typer.echo(
            (
                "  APEX manifests: "
                f"{len(apex)}"
            )
        )

        for parsed_apex in apex:
            metadata = parsed_apex.metadata

            typer.echo(
                (
                    "  "
                    f"{metadata.apex_name}: "
                    f"version={metadata.version}"
                )
            )
            typer.echo(
                (
                    "    artifact: "
                    f"{metadata.artifact.path}"
                )
            )
            typer.echo(
                (
                    "    provide native libs: "
                    f"{len(metadata.provide_native_libs)}"
                )
            )
            for value in metadata.provide_native_libs:
                typer.echo(
                    f"      {value}"
                )

            typer.echo(
                (
                    "    require native libs: "
                    f"{len(metadata.require_native_libs)}"
                )
            )
            for value in metadata.require_native_libs:
                typer.echo(
                    f"      {value}"
                )

            typer.echo(
                (
                    "    JNI libs: "
                    f"{len(metadata.jni_libs)}"
                )
            )
            for value in metadata.jni_libs:
                typer.echo(
                    f"      {value}"
                )

            typer.echo(
                (
                    "    require shared APEX libs: "
                    f"{len(metadata.require_shared_apex_libs)}"
                )
            )
            for value in metadata.require_shared_apex_libs:
                typer.echo(
                    f"      {value}"
                )

            typer.echo(
                (
                    "    provide shared APEX libs: "
                    f"{metadata.provide_shared_apex_libs}"
                )
            )
            typer.echo(
                (
                    "    provide shared APEX libs present: "
                    f"{metadata.provide_shared_apex_libs_present}"
                )
            )
            typer.echo(
                (
                    "    supports rebootless update: "
                    f"{metadata.supports_rebootless_update}"
                )
            )
            typer.echo(
                (
                    "    supports rebootless update present: "
                    f"{metadata.supports_rebootless_update_present}"
                )
            )

        typer.echo()
        typer.echo(
            "BMP Parsing:"
        )
        typer.echo(
            (
                "  Parsed BMP resources: "
                f"{len(bmp)}"
            )
        )

        for parsed_bmp in bmp:
            artifact = (
                parsed_bmp.artifact
            )

            parent = (
                artifact.parent
            )

            typer.echo(
                (
                    "  "
                    f"{artifact.semantic_name or artifact.path.name}:"
                )
            )

            typer.echo(
                (
                    "    artifact: "
                    f"{artifact.path}"
                )
            )

            typer.echo(
                (
                    "    Extraction operation: "
                    f"{artifact.operation.value}"
                )
            )

            typer.echo(
                (
                    "    Extraction identity preserved: "
                    f"{parsed_bmp.artifact is artifact}"
                )
            )

            typer.echo(
                (
                    "    parent: "
                    + (
                        str(
                            parent.path
                        )
                        if parent is not None
                        else "none"
                    )
                )
            )

            typer.echo(
                (
                    "    dimensions: "
                    f"{parsed_bmp.width}x{parsed_bmp.height}"
                )
            )

            typer.echo(
                (
                    "    bits per pixel: "
                    f"{parsed_bmp.bits_per_pixel}"
                )
            )

            typer.echo(
                (
                    "    compression: "
                    f"{parsed_bmp.compression}"
                )
            )

            typer.echo(
                (
                    "    file size: "
                    f"{parsed_bmp.file_size}"
                )
            )

            typer.echo(
                (
                    "    pixel data offset: "
                    f"{parsed_bmp.pixel_data_offset}"
                )
            )

            typer.echo(
                (
                    "    DIB header size: "
                    f"{parsed_bmp.dib_header_size}"
                )
            )

            typer.echo(
                (
                    "    image size: "
                    f"{parsed_bmp.image_size}"
                )
            )

            typer.echo(
                (
                    "    colors used: "
                    f"{parsed_bmp.colors_used}"
                )
            )

            typer.echo(
                (
                    "    important colors: "
                    f"{parsed_bmp.important_colors}"
                )
            )

        typer.echo()
        typer.echo(
            "SELinux Parsing:"
        )

        typer.echo(
            (
                "  SELinux sources: "
                f"{len(selinux_sources)}"
            )
        )

        for kind in (
            "file_contexts",
            "property_contexts",
            "service_contexts",
            "hwservice_contexts",
            "vndservice_contexts",
            "seapp_contexts",
            "keystore2_key_contexts",
            "mac_permissions",
            "cil",
            "policy_version",
            "policy_hash",
            "compiled_policy",
            "other_text",
            "opaque",
        ):
            typer.echo(
                (
                    f"  {kind} sources: "
                    f"{selinux_kind_counts.get(kind, 0)}"
                )
            )

        typer.echo(
            (
                "  Context declarations: "
                f"{selinux_context_declarations}"
            )
        )

        typer.echo(
            (
                "  SEApp declarations: "
                f"{selinux_seapp_declarations}"
            )
        )

        typer.echo(
            (
                "  CIL forms: "
                f"{len(selinux_cil_forms)}"
            )
        )

        typer.echo(
            (
                "  Distinct CIL form names: "
                f"{len(selinux_cil_form_names)}"
            )
        )

        typer.echo(
            (
                "  Metadata text lines: "
                f"{selinux_metadata_text_lines}"
            )
        )

        typer.echo(
            (
                "  Opaque policy/source artifacts: "
                f"{len(selinux_opaque_sources)}"
            )
        )

        typer.echo(
            (
                "  Ramdisk-backed SELinux sources: "
                f"{len(selinux_ramdisk_sources)}"
            )
        )

        typer.echo(
            (
                "  Meaningful unparsed SELinux lines: "
                f"{selinux_unparsed_lines}"
            )
        )

        typer.echo()
        typer.echo(
            "Ramdisk Parsing:"
        )

        typer.echo(
            (
                "  Canonical ramdisks: "
                f"{len(ramdisks)}"
            )
        )

        typer.echo(
            (
                "  CPIO entries: "
                f"{sum(ramdisk.entry_count for ramdisk in ramdisks)}"
            )
        )

        for ramdisk in ramdisks:
            typer.echo(
                (
                    "  "
                    f"{ramdisk.boot_image_artifact.semantic_name or ramdisk.boot_image_artifact.path.name}:"
                )
            )

            typer.echo(
                (
                    "    entries: "
                    f"{ramdisk.entry_count}"
                )
            )

            typer.echo(
                (
                    "    boot image: "
                    f"{ramdisk.boot_image_artifact.path}"
                )
            )

            typer.echo(
                (
                    "    ramdisk component: "
                    f"{ramdisk.ramdisk_component.path}"
                )
            )

            typer.echo(
                (
                    "    ramdisk CPIO: "
                    f"{ramdisk.ramdisk_cpio.path}"
                )
            )

            typer.echo(
                (
                    "    ramdisk root: "
                    f"{ramdisk.ramdisk_root.path}"
                )
            )

        typer.echo()
        typer.echo(
            "Kernel Parsing:"
        )

        typer.echo(
            (
                "  Kernel images: "
                f"{len(kernels)}"
            )
        )

        for index, kernel in enumerate(
            kernels,
            start=1,
        ):
            typer.echo(
                (
                    f"  Kernel {index}: "
                    f"{kernel.artifact.path}"
                )
            )
            typer.echo(
                (
                    "    Linux banner: "
                    f"{kernel.linux_banner or 'not present'}"
                )
            )
            typer.echo(
                (
                    "    Kernel release: "
                    f"{kernel.kernel_release or 'not present'}"
                )
            )

            if kernel.config is None:
                typer.echo(
                    "    Embedded IKCONFIG: not present"
                )
            else:
                typer.echo(
                    "    Embedded IKCONFIG: parsed"
                )
                typer.echo(
                    (
                        "      compression: "
                        f"{kernel.config.compression.value}"
                    )
                )
                typer.echo(
                    (
                        "      declarations: "
                        f"{kernel.config_count}"
                    )
                )
                typer.echo(
                    (
                        "      unparsed lines: "
                        f"{kernel.unparsed_config_count}"
                    )
                )

        boot_dtbs = (
            parsing_result.boot_dtbs
        )

        typer.echo()
        typer.echo(
            "Boot DTB Parsing:"
        )
        typer.echo(
            (
                "  FDT members: "
                f"{len(boot_dtbs)}"
            )
        )

        for index, parsed in enumerate(
            boot_dtbs,
            start=1,
        ):
            artifact = (
                parsed.artifact
            )

            typer.echo(
                (
                    f"  FDT member {index}: "
                    f"{artifact.path}"
                )
            )

            if artifact.parent is not None:
                typer.echo(
                    (
                        "    parent component: "
                        f"{artifact.parent.path}"
                    )
                )

            typer.echo(
                (
                    "    bytes: "
                    f"{artifact.size_bytes}"
                )
            )
            typer.echo(
                (
                    "    FDT total size: "
                    f"{parsed.header.totalsize}"
                )
            )
            typer.echo(
                (
                    "    nodes: "
                    f"{parsed.node_count}"
                )
            )
            typer.echo(
                (
                    "    properties: "
                    f"{parsed.property_count}"
                )
            )

        vendor_ramdisk_tables = (
            parsing_result
            .vendor_ramdisk_tables
        )

        typer.echo()
        typer.echo(
            "Vendor Ramdisk Table Parsing:"
        )
        typer.echo(
            (
                "  Tables: "
                f"{len(vendor_ramdisk_tables)}"
            )
        )
        typer.echo(
            (
                "  Entries: "
                f"{sum(len(table.entries) for table in vendor_ramdisk_tables)}"
            )
        )

        for table_index, table in enumerate(
            vendor_ramdisk_tables,
            start=1,
        ):
            typer.echo(
                (
                    f"  Table {table_index}: "
                    f"{table.artifact.path}"
                )
            )
            typer.echo(
                (
                    "    boot image: "
                    f"{table.boot_image_artifact.path}"
                )
            )
            typer.echo(
                (
                    "    entry size: "
                    f"{table.entry_size}"
                )
            )
            typer.echo(
                (
                    "    entries: "
                    f"{len(table.entries)}"
                )
            )

            for entry in table.entries:
                typer.echo(
                    (
                        f"    Entry {entry.index}: "
                        f"size={entry.ramdisk_size} "
                        f"offset={entry.ramdisk_offset} "
                        f"type={entry.ramdisk_type} "
                        f"name={entry.ramdisk_name!r}"
                    )
                )
                typer.echo(
                    (
                        "      board_id: "
                        + ", ".join(
                            str(
                                value
                            )
                            for value
                            in entry.board_id
                        )
                    )
                )
                typer.echo(
                    (
                        "      raw bytes: "
                        f"{len(entry.raw)}"
                    )
                )

        boot_signatures = (
            parsing_result.boot_signatures
        )

        typer.echo()
        typer.echo(
            "Boot Signature Parsing:"
        )
        typer.echo(
            (
                "  Boot signatures: "
                f"{len(boot_signatures)}"
            )
        )

        for index, signature in enumerate(
            boot_signatures,
            start=1,
        ):
            metadata = signature.metadata

            typer.echo(
                (
                    f"  Boot signature {index}: "
                    f"{signature.artifact.path}"
                )
            )
            typer.echo(
                (
                    "    boot image: "
                    f"{signature.boot_image_artifact.path}"
                )
            )
            typer.echo(
                (
                    "    required libavb: "
                    f"{metadata.required_libavb_version_major}."
                    f"{metadata.required_libavb_version_minor}"
                )
            )
            typer.echo(
                (
                    "    algorithm type: "
                    f"{metadata.algorithm_type}"
                )
            )
            typer.echo(
                (
                    "    rollback index: "
                    f"{metadata.rollback_index}"
                )
            )
            typer.echo(
                (
                    "    rollback index location: "
                    f"{metadata.rollback_index_location}"
                )
            )
            typer.echo(
                (
                    "    flags: "
                    f"{metadata.flags}"
                )
            )
            typer.echo(
                (
                    "    release string: "
                    f"{metadata.release_string!r}"
                )
            )
            typer.echo(
                (
                    "    descriptors: "
                    f"{len(metadata.descriptors)}"
                )
            )

        structured = (
            parsing_result.structured_configuration
        )

        structured_source_count = sum(
            (
                len(structured.avb_public_keys),
                len(structured.cgroup_configurations),
                len(structured.mke2fs_configurations),
                len(
                    structured
                    .recovery_wipe_configurations
                ),
                len(structured.blueprints),
                len(
                    structured
                    .sensor_hal_configurations
                ),
                len(
                    structured
                    .sensor_registry_configurations
                ),
            )
        )

        structured_cgroup_scalars = sum(
            len(value.scalars)
            for value
            in structured.cgroup_configurations
        )

        structured_mke2fs_entries = sum(
            len(value.entries)
            for value
            in structured.mke2fs_configurations
        )

        structured_recovery_wipe_entries = sum(
            len(value.entries)
            for value
            in structured.recovery_wipe_configurations
        )

        structured_blueprint_modules = sum(
            len(value.modules)
            for value in structured.blueprints
        )

        structured_blueprint_properties = sum(
            len(module.properties)
            for value in structured.blueprints
            for module in value.modules
        )

        structured_rsa_4096_keys = sum(
            1
            for value in structured.avb_public_keys
            if value.key_num_bits == 4096
        )

        typer.echo()
        typer.echo(
            "Structured Configuration Parsing:"
        )
        typer.echo(
            (
                "  Sources: "
                f"{structured_source_count}"
            )
        )

        typer.echo(
            (
                "  AVB public-key sources: "
                f"{len(structured.avb_public_keys)}"
            )
        )
        typer.echo(
            (
                "  AVB RSA-4096 keys: "
                f"{structured_rsa_4096_keys}"
            )
        )

        typer.echo(
            (
                "  Cgroup configuration sources: "
                f"{len(structured.cgroup_configurations)}"
            )
        )
        typer.echo(
            (
                "  Cgroup scalar facts: "
                f"{structured_cgroup_scalars}"
            )
        )

        typer.echo(
            (
                "  Mke2fs configuration sources: "
                f"{len(structured.mke2fs_configurations)}"
            )
        )
        typer.echo(
            (
                "  Mke2fs declarations: "
                f"{structured_mke2fs_entries}"
            )
        )

        typer.echo(
            (
                "  Recovery wipe configuration sources: "
                f"{len(
                    structured
                    .recovery_wipe_configurations
                )}"
            )
        )
        typer.echo(
            (
                "  Recovery wipe declarations: "
                f"{structured_recovery_wipe_entries}"
            )
        )

        typer.echo(
            (
                "  Blueprint sources: "
                f"{len(structured.blueprints)}"
            )
        )
        typer.echo(
            (
                "  Blueprint modules: "
                f"{structured_blueprint_modules}"
            )
        )
        typer.echo(
            (
                "  Blueprint literal properties: "
                f"{structured_blueprint_properties}"
            )
        )


        typer.echo(
            (
                "  Sensor HAL configuration sources: "
                f"{len(structured.sensor_hal_configurations)}"
            )
        )
        typer.echo(
            (
                "  Sensor HAL declarations: "
                f"{sum(
                    len(value.entries)
                    for value
                    in structured.sensor_hal_configurations
                )}"
            )
        )
        typer.echo(
            (
                "  Sensor registry configuration sources: "
                f"{len(structured.sensor_registry_configurations)}"
            )
        )
        typer.echo(
            (
                "  Sensor registry records: "
                f"{sum(
                    len(value.records)
                    for value
                    in structured.sensor_registry_configurations
                )}"
            )
        )

        if structured.avb_public_keys:
            typer.echo(
                "  AVB public keys:"
            )

            for value in (
                structured.avb_public_keys
            ):
                source = value.source

                typer.echo(
                    (
                        "    "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    )
                )
                typer.echo(
                    (
                        "      key bits: "
                        f"{value.key_num_bits}"
                    )
                )
                typer.echo(
                    (
                        "      n0inv: "
                        f"{value.n0inv}"
                    )
                )
                typer.echo(
                    (
                        "      modulus bytes: "
                        f"{len(value.modulus)}"
                    )
                )
                typer.echo(
                    (
                        "      rr bytes: "
                        f"{len(value.rr)}"
                    )
                )

        if structured.cgroup_configurations:
            typer.echo(
                "  Cgroup configurations:"
            )

            for value in (
                structured.cgroup_configurations
            ):
                source = value.source

                typer.echo(
                    (
                        "    "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    )
                )
                typer.echo(
                    (
                        "      scalar facts: "
                        f"{len(value.scalars)}"
                    )
                )

                for scalar in value.scalars:
                    typer.echo(
                        (
                            "      "
                            f"{scalar.path}: "
                            f"{scalar.kind.value} "
                            f"{scalar.value!r}"
                        )
                    )

        if structured.mke2fs_configurations:
            typer.echo(
                "  Mke2fs configurations:"
            )

            for value in (
                structured.mke2fs_configurations
            ):
                source = value.source

                typer.echo(
                    (
                        "    "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    )
                )
                typer.echo(
                    (
                        "      declarations: "
                        f"{len(value.entries)}"
                    )
                )

                for entry in value.entries:
                    scope = (
                        ".".join(entry.scope)
                        if entry.scope
                        else "-"
                    )

                    typer.echo(
                        (
                            "      "
                            f"line {entry.source_line}: "
                            f"section={entry.section!r}, "
                            f"scope={scope!r}, "
                            f"{entry.key}={entry.value}"
                        )
                    )

        if (
            structured
            .recovery_wipe_configurations
        ):
            typer.echo(
                "  Recovery wipe configurations:"
            )

            for value in (
                structured
                .recovery_wipe_configurations
            ):
                source = value.source

                typer.echo(
                    (
                        "    "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    )
                )
                typer.echo(
                    (
                        "      declarations: "
                        f"{len(value.entries)}"
                    )
                )

                for entry in value.entries:
                    typer.echo(
                        (
                            "      "
                            f"line {entry.source_line}: "
                            f"{entry.path}"
                        )
                    )

        if structured.blueprints:
            typer.echo(
                "  Blueprint sources:"
            )

            for value in structured.blueprints:
                source = value.source

                typer.echo(
                    (
                        "    "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    )
                )
                typer.echo(
                    (
                        "      modules: "
                        f"{len(value.modules)}"
                    )
                )

                for module in value.modules:
                    typer.echo(
                        (
                            "      "
                            f"line {module.source_line}: "
                            f"{module.module_type}"
                            + (
                                f" name={module.name!r}"
                                if module.name is not None
                                else ""
                            )
                        )
                    )

                    for prop in (
                        module.properties
                    ):
                        typer.echo(
                            (
                                "        "
                                f"line {prop.source_line}: "
                                f"{prop.name} "
                                f"[{prop.kind.value}] = "
                                f"{prop.value!r}"
                            )
                        )

        typer.echo()
        typer.echo(
            "Partition-image Parsing:"
        )

        typer.echo(
            (
                "  Canonical boot images: "
                f"{len(boot_images)}"
            )
        )

        for boot_image in boot_images:
            _echo_boot_result(
                boot_image.container_kind,
                boot_image,
            )

        typer.echo()
        typer.echo(
            "Parser source provenance:"
        )

        for partition_filesystem in (
            source_inventory.filesystems
        ):
            typer.echo(
                (
                    "  "
                    f"{partition_filesystem.source_name}: "
                    "partition="
                    f"{(
                        partition_filesystem.partition.name
                        if partition_filesystem.partition is not None
                        else "none"
                    )}, "
                    f"artifact={partition_filesystem.artifact.path}"
                )
            )


    report_text = (
        report_buffer.getvalue()
    )

    report_path = (
        parsing_root
        / "parsing-report.txt"
    )

    report_path.write_text(
        report_text,
        encoding="utf-8",
    )

    # Ensure no unfinished live activity block remains before ordinary
    # completion output.
    if sys.stdout.isatty():
        clear_live_progress_block()

    typer.echo()
    typer.echo(
        "Parsing completed successfully."
    )
    typer.echo(
        f"Report: {report_path}"
    )
    typer.echo(
        "Parsing snapshot: "
        f"{parsing_snapshot_path(workspace)}"
    )

    typer.echo(
        f"Report preserved: {report_path}"
    )


def _echo_boot_result(
    name: str,
    parsed_image,
) -> None:
    """
    Print one canonical boot-family Parsing result.
    """

    partition = (
        parsed_image.partition
    )

    metadata = (
        parsed_image.metadata
    )

    typer.echo(
        f"  {name}: parsed"
    )
    typer.echo(
        (
            "    partition: "
            f"{partition.name}"
        )
    )
    typer.echo(
        (
            "    artifact: "
            f"{partition.artifact.path}"
        )
    )
    typer.echo(
        (
            "    header version: "
            f"{metadata.header_version}"
        )
    )

    if hasattr(
        metadata,
        "android_major",
    ):
        typer.echo(
            (
                "    Android version: "
                f"{metadata.android_major}."
                f"{metadata.android_minor}."
                f"{metadata.android_patch}"
            )
        )

    if hasattr(
        metadata,
        "boot_name",
    ):
        typer.echo(
            (
                "    boot name: "
                f"{metadata.boot_name}"
            )
        )

    typer.echo(
        (
            "    cmdline: "
            f"{metadata.cmdline}"
        )
    )

    if hasattr(
        parsed_image,
        "bootconfig",
    ):
        bootconfig = (
            parsed_image.bootconfig
        )

        bootconfig_artifact = (
            parsed_image.bootconfig_artifact
        )

        if bootconfig is None:
            typer.echo(
                "    bootconfig: not present"
            )
        else:
            typer.echo(
                "    bootconfig: parsed"
            )

            if bootconfig_artifact is not None:
                typer.echo(
                    (
                        "      artifact: "
                        f"{bootconfig_artifact.path}"
                    )
                )

            typer.echo(
                (
                    "      entries: "
                    f"{len(bootconfig.entries)}"
                )
            )

            typer.echo(
                (
                    "      unparsed lines: "
                    f"{len(bootconfig.unparsed_lines)}"
                )
            )

            for entry in bootconfig.entries:
                typer.echo(
                    (
                        "      "
                        f"line {entry.line_number}: "
                        f"{entry.key}={entry.value}"
                    )
                )

            for unparsed in (
                bootconfig.unparsed_lines
            ):
                typer.echo(
                    (
                        "      "
                        f"unparsed line "
                        f"{unparsed.line_number}: "
                        f"{unparsed.raw!r} "
                        f"({unparsed.reason})"
                    )
                )
