from __future__ import annotations

from fnmatch import fnmatch

from treeforge.android.extraction.cpio.extractor import (
    CpioEntryType,
)

from treeforge.android.boot_image.models import (
    AndroidBootImageCpioEntryDisposition,
    AndroidBootImageCpioEntryInterpretation,
    AndroidBootImageCpioEntryKind,
    AndroidBootImageKernelModuleAliasEntry,
    AndroidBootImageKernelModuleDependencyEntry,
    AndroidBootImageKernelModuleLoadEntry,
    AndroidBootImageKernelModuleReference,
    AndroidBootImageKernelModuleResolution,
    AndroidBootImageKernelModuleSoftDependencyEntry,
    AndroidBootImageKernelModuleUninterpretedLine,
)
from treeforge.android.parsing.kernel_module.model import (
    AndroidKernelModuleConfigurationKind,
)

from treeforge.android.boot_image.models import (
    AndroidBootImageAvbDescriptorInterpretation,
    AndroidBootImageAvbDescriptorKind,
    AndroidBootImageAvbRegionInterpretation,
    AndroidBootImageAvbSourceKind,
    AndroidBootImageAvbVbmetaInterpretation,
    AndroidBootImageBootImageInterpretation,
    AndroidBootImageComponentInterpretation,
    AndroidBootImageComponentRole,
    AndroidBootImageDtboContainerInterpretation,
    AndroidBootImageDtboEntryInterpretation,
    AndroidBootImageInterpretationDisposition,
    AndroidBootImageRamdiskInterpretation,
)
from treeforge.android.boot_image.result import (
    AndroidBootImageIntakeResult,
    AndroidBootImageInterpretationResult,
)
from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
    AndroidParsedAvbKernelCmdlineDescriptor,
    AndroidParsedAvbPropertyDescriptor,
)


class AndroidBootImageInterpreter:
    """
    Interpret canonical Parsing boot-family evidence for Boot Image.

    Interpretation is structural and device-generic. It does not choose
    AOSP providers, source ownership, image construction arguments, output
    paths, or signing policy.
    """

    _ROLE_BY_SEMANTIC_NAME = {
        "kernel": (
            AndroidBootImageComponentRole.KERNEL
        ),
        "ramdisk": (
            AndroidBootImageComponentRole.RAMDISK
        ),
        "second": (
            AndroidBootImageComponentRole.SECOND
        ),
        "recovery_dtbo": (
            AndroidBootImageComponentRole.RECOVERY_DTBO
        ),
        "dtb": (
            AndroidBootImageComponentRole.DTB
        ),
        "vendor_ramdisk_table": (
            AndroidBootImageComponentRole
            .VENDOR_RAMDISK_TABLE
        ),
        "bootconfig": (
            AndroidBootImageComponentRole.BOOTCONFIG
        ),
        "boot_signature": (
            AndroidBootImageComponentRole.BOOT_SIGNATURE
        ),
    }

    def build(
        self,
        intake: AndroidBootImageIntakeResult,
    ) -> AndroidBootImageInterpretationResult:
        if not isinstance(
            intake,
            AndroidBootImageIntakeResult,
        ):
            raise TypeError(
                "intake must be an AndroidBootImageIntakeResult"
            )

        kernel_by_component_artifact_id = {}

        for kernel in intake.kernels:
            component_artifact = (
                kernel.artifact.parent
            )

            if component_artifact is None:
                continue

            identity = id(
                component_artifact
            )

            if (
                identity
                in kernel_by_component_artifact_id
            ):
                raise ValueError(
                    "multiple canonical ParsedKernelImage objects "
                    "resolve to the same boot component artifact"
                )

            kernel_by_component_artifact_id[
                identity
            ] = kernel

        boot_signature_by_artifact_id = {
            id(
                signature.artifact
            ): signature
            for signature
            in intake.boot_signatures
        }

        if len(
            boot_signature_by_artifact_id
        ) != len(
            intake.boot_signatures
        ):
            raise ValueError(
                "canonical boot-signature population contains "
                "duplicate artifact object identities"
            )

        ramdisk_by_component_artifact_id = {}

        for ramdisk in intake.ramdisks:
            identity = id(
                ramdisk.ramdisk_component
            )

            if (
                identity
                in ramdisk_by_component_artifact_id
            ):
                raise ValueError(
                    "multiple canonical ParsedAndroidRamdisk "
                    "objects resolve to the same boot component"
                )

            ramdisk_by_component_artifact_id[
                identity
            ] = ramdisk

        bootconfig_by_component_artifact_id = {}

        for image in intake.boot_images:
            if (
                image.bootconfig_artifact is None
                or image.bootconfig is None
            ):
                continue

            identity = id(
                image.bootconfig_artifact
            )

            if (
                identity
                in bootconfig_by_component_artifact_id
            ):
                raise ValueError(
                    "multiple canonical ParsedAndroidBootconfig "
                    "objects resolve to the same boot component"
                )

            bootconfig_by_component_artifact_id[
                identity
            ] = image.bootconfig

        dtbs_by_component_artifact_id = {}

        for dtb in intake.boot_dtbs:
            component = (
                dtb.artifact.parent
            )

            if component is None:
                raise ValueError(
                    "canonical boot ParsedFdt must retain its "
                    "boot DTB component parent"
                )

            dtbs_by_component_artifact_id.setdefault(
                id(
                    component
                ),
                [],
            ).append(
                dtb
            )

        dtbs_by_component_artifact_id = {
            identity: tuple(
                values
            )
            for identity, values
            in dtbs_by_component_artifact_id.items()
        }

        vendor_ramdisk_table_by_artifact_id = {
            id(
                table.artifact
            ): table
            for table
            in intake.vendor_ramdisk_tables
        }

        if len(
            vendor_ramdisk_table_by_artifact_id
        ) != len(
            intake.vendor_ramdisk_tables
        ):
            raise ValueError(
                "canonical vendor ramdisk-table population "
                "contains duplicate artifact object identities"
            )

        boot_images = tuple(
            self._interpret_boot_image(
                image,
                kernel_by_component_artifact_id=(
                    kernel_by_component_artifact_id
                ),
                boot_signature_by_artifact_id=(
                    boot_signature_by_artifact_id
                ),
                ramdisk_by_component_artifact_id=(
                    ramdisk_by_component_artifact_id
                ),
                bootconfig_by_component_artifact_id=(
                    bootconfig_by_component_artifact_id
                ),
                dtbs_by_component_artifact_id=(
                    dtbs_by_component_artifact_id
                ),
                vendor_ramdisk_table_by_artifact_id=(
                    vendor_ramdisk_table_by_artifact_id
                ),
            )
            for image
            in intake.boot_images
        )

        dtbo_entries = tuple(
            self._interpret_dtbo_entry(
                entry
            )
            for entry
            in intake.dtbo
        )

        dtbo_containers = (
            self._group_dtbo_containers(
                dtbo_entries
            )
        )

        avb_vbmeta = tuple(
            self._interpret_vbmeta(
                vbmeta
            )
            for vbmeta
            in intake.vbmeta
        )

        avb_node_by_parsed_id = {
            id(
                node.vbmeta
            ): node
            for node
            in avb_vbmeta
        }

        if len(
            avb_node_by_parsed_id
        ) != len(
            avb_vbmeta
        ):
            raise ValueError(
                "canonical VBMeta population contains duplicate "
                "ParsedAvbVbmeta identities"
            )

        avb_regions = tuple(
            self._interpret_avb_region(
                region,
                node_by_parsed_id=(
                    avb_node_by_parsed_id
                ),
            )
            for region
            in intake.avb_regions
        )

        ramdisks = tuple(
            self._interpret_ramdisk(
                intake=intake,
                ramdisk=ramdisk,
            )
            for ramdisk
            in intake.ramdisks
        )

        result = AndroidBootImageInterpretationResult(
            intake=intake,
            boot_images=boot_images,
            ramdisks=ramdisks,
            dtbo_entries=dtbo_entries,
            dtbo_containers=dtbo_containers,
            avb_vbmeta=avb_vbmeta,
            avb_regions=avb_regions,
        )

        if result.parsing is not intake.parsing:
            raise RuntimeError(
                "Boot Image interpretation must retain the exact "
                "canonical AndroidParsingResult"
            )

        return result

    def _interpret_ramdisk(
        self,
        *,
        intake: AndroidBootImageIntakeResult,
        ramdisk,
    ) -> AndroidBootImageRamdiskInterpretation:
        filesystem_matches = tuple(
            source
            for source
            in intake.source_inventory.filesystems
            if (
                source.artifact
                is ramdisk.ramdisk_root
            )
        )

        if len(
            filesystem_matches
        ) != 1:
            raise ValueError(
                "Boot Image ramdisk interpretation requires exactly "
                "one canonical parser filesystem source for each "
                "ramdisk root"
            )

        filesystem_source = (
            filesystem_matches[0]
        )

        boot_matches = tuple(
            image
            for image
            in intake.boot_images
            if (
                image.partition.artifact
                is ramdisk.boot_image_artifact
            )
        )

        if len(
            boot_matches
        ) != 1:
            raise ValueError(
                "Boot Image ramdisk interpretation requires exactly "
                "one ParsedBootImage retaining the ramdisk "
                "boot-family artifact identity"
            )

        boot_image = (
            boot_matches[0]
        )

        canonical_sources = tuple(
            source
            for source
            in intake.source_inventory.sources
            if (
                source.filesystem_source
                is filesystem_source
            )
        )

        init_files = tuple(
            value
            for value
            in intake.filesystem.init_files
            if (
                value.filesystem_source
                is filesystem_source
            )
        )

        fstabs = tuple(
            value
            for value
            in intake.filesystem.fstabs
            if (
                value.filesystem_source
                is filesystem_source
            )
        )

        ueventd_files = tuple(
            value
            for value
            in intake.filesystem.ueventd_files
            if (
                value.filesystem_source
                is filesystem_source
            )
        )

        kernel_modules = tuple(
            value
            for value
            in intake.parsing.kernel_modules.modules
            if (
                value.elf.source.filesystem_source
                is filesystem_source
            )
        )

        kernel_module_configurations = tuple(
            value
            for value
            in intake.parsing.kernel_module_configurations
            if (
                value.source.filesystem_source
                is filesystem_source
            )
        )

        kernel_module_relationships = (
            self._interpret_kernel_module_relationships(
                kernel_modules=kernel_modules,
                configurations=kernel_module_configurations,
            )
        )

        blueprint_resource_sources = (
            self._blueprint_resource_sources(
                intake=intake,
                ramdisk=ramdisk,
                filesystem_source=filesystem_source,
            )
        )

        cpio_entries = (
            self._interpret_cpio_entries(
                ramdisk=ramdisk,
                canonical_sources=canonical_sources,
                blueprint_resource_sources=(
                    blueprint_resource_sources
                ),
                init_files=init_files,
                fstabs=fstabs,
                ueventd_files=ueventd_files,
                kernel_modules=kernel_modules,
                kernel_module_configurations=(
                    kernel_module_configurations
                ),
            )
        )


        return AndroidBootImageRamdiskInterpretation(
            ramdisk=ramdisk,
            filesystem_source=filesystem_source,
            boot_image=boot_image,
            canonical_sources=canonical_sources,
            init_files=init_files,
            fstabs=fstabs,
            ueventd_files=ueventd_files,
            kernel_modules=kernel_modules,
            kernel_module_configurations=(
                kernel_module_configurations
            ),
            kernel_module_load_entries=(
                kernel_module_relationships[
                    "load"
                ]
            ),
            kernel_module_dependency_entries=(
                kernel_module_relationships[
                    "dependency"
                ]
            ),
            kernel_module_alias_entries=(
                kernel_module_relationships[
                    "alias"
                ]
            ),
            kernel_module_soft_dependency_entries=(
                kernel_module_relationships[
                    "softdep"
                ]
            ),
            kernel_module_uninterpreted_lines=(
                kernel_module_relationships[
                    "uninterpreted"
                ]
            ),
            cpio_entries=cpio_entries,
        )

    @staticmethod
    def _bootstrap_normalized_path(
        value,
    ):
        if value is None:
            return None

        if hasattr(
            value,
            "as_posix",
        ):
            value = value.as_posix()

        return str(
            value
        ).lstrip(
            "/"
        )

    @classmethod
    def _parsed_source_path(
        cls,
        value,
    ):
        direct = getattr(
            value,
            "android_path",
            None,
        )

        if direct is not None:
            return cls._bootstrap_normalized_path(
                direct
            )

        source = getattr(
            value,
            "source",
            None,
        )

        if source is not None:
            source_path = getattr(
                source,
                "android_path",
                None,
            )

            if source_path is not None:
                return cls._bootstrap_normalized_path(
                    source_path
                )

        return None

    def _blueprint_resource_sources(
        self,
        *,
        intake,
        ramdisk,
        filesystem_source,
    ):
        """
        Resolve literal Blueprint prebuilt_res srcs against one exact
        ramdisk population.

        This does not parse PNG content or execute Soong. It only associates
        exact preserved CPIO payloads with canonical Parsing Blueprint
        evidence already decoded from the factory image.
        """

        regular_paths = tuple(
            self._bootstrap_normalized_path(
                entry.path
            )
            for entry
            in ramdisk.entries
            if (
                entry.entry_type
                is CpioEntryType.FILE
            )
        )

        associations = {}

        for blueprint in (
            intake.parsing
            .structured_configuration
            .blueprints
        ):
            if (
                blueprint.source.filesystem_source
                is not filesystem_source
            ):
                continue

            blueprint_directory = (
                blueprint.source
                .android_path
                .parent
            )

            for module in blueprint.modules:
                if module.module_type != "prebuilt_res":
                    continue

                src_properties = tuple(
                    prop
                    for prop
                    in module.properties
                    if prop.name == "srcs"
                )

                if not src_properties:
                    continue

                if len(src_properties) != 1:
                    raise ValueError(
                        "Boot Image Blueprint prebuilt_res module "
                        "contains multiple literal srcs properties"
                    )

                src_value = (
                    src_properties[0].value
                )

                if not isinstance(
                    src_value,
                    tuple,
                ):
                    raise ValueError(
                        "Boot Image Blueprint prebuilt_res srcs "
                        "must be a parsed literal string list"
                    )

                for pattern in src_value:
                    if not isinstance(
                        pattern,
                        str,
                    ):
                        raise ValueError(
                            "Boot Image Blueprint prebuilt_res src "
                            "pattern must be a string"
                        )

                    resolved_pattern = (
                        blueprint_directory
                        / pattern
                    ).as_posix().lstrip("/")

                    for path in regular_paths:
                        if not fnmatch(
                            path,
                            resolved_pattern,
                        ):
                            continue

                        existing = associations.get(
                            path
                        )

                        if (
                            existing is not None
                            and existing
                            is not blueprint.source
                        ):
                            raise ValueError(
                                "Boot Image resource path is claimed "
                                "by multiple canonical Blueprint sources: "
                                f"{path!r}"
                            )

                        associations[
                            path
                        ] = blueprint.source

        return associations

    def _interpret_cpio_entries(
        self,
        *,
        ramdisk,
        canonical_sources,
        blueprint_resource_sources,
        init_files,
        fstabs,
        ueventd_files,
        kernel_modules,
        kernel_module_configurations,
    ):
        canonical_sources_by_path = {}

        for source in canonical_sources:
            path = self._parsed_source_path(
                source
            )

            if path is None:
                continue

            existing = canonical_sources_by_path.get(
                path
            )

            if (
                existing is not None
                and existing is not source
            ):
                raise ValueError(
                    "Boot Image ramdisk contains multiple "
                    "canonical Parsing sources for Android path "
                    f"{path!r}"
                )

            canonical_sources_by_path[
                path
            ] = source

        canonical_source_paths = set(
            canonical_sources_by_path
        )

        init_paths = {
            path
            for path
            in (
                self._parsed_source_path(
                    value
                )
                for value
                in init_files
            )
            if path is not None
        }

        fstab_paths = {
            path
            for path
            in (
                self._parsed_source_path(
                    value
                )
                for value
                in fstabs
            )
            if path is not None
        }

        ueventd_paths = {
            path
            for path
            in (
                self._parsed_source_path(
                    value
                )
                for value
                in ueventd_files
            )
            if path is not None
        }

        module_paths = {
            self._bootstrap_normalized_path(
                module.android_path
            )
            for module
            in kernel_modules
        }

        module_configuration_paths = {
            path
            for path
            in (
                self._parsed_source_path(
                    value
                )
                for value
                in kernel_module_configurations
            )
            if path is not None
        }

        interpretations = []

        for index, entry in enumerate(
            ramdisk.entries
        ):
            path = self._bootstrap_normalized_path(
                entry.path
            )

            associated_source = None

            if (
                entry.entry_type
                is CpioEntryType.DIRECTORY
            ):
                kind = (
                    AndroidBootImageCpioEntryKind
                    .DIRECTORY
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .INTERPRETED
                )

            elif (
                entry.entry_type
                is CpioEntryType.SYMLINK
            ):
                kind = (
                    AndroidBootImageCpioEntryKind
                    .SYMLINK
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .INTERPRETED
                )

            elif (
                entry.entry_type
                is CpioEntryType.CHARACTER_DEVICE
            ):
                kind = (
                    AndroidBootImageCpioEntryKind
                    .CHARACTER_DEVICE
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .INTERPRETED
                )

            elif (
                entry.entry_type
                is CpioEntryType.BLOCK_DEVICE
            ):
                kind = (
                    AndroidBootImageCpioEntryKind
                    .BLOCK_DEVICE
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .INTERPRETED
                )

            elif (
                entry.entry_type
                is CpioEntryType.FIFO
            ):
                kind = (
                    AndroidBootImageCpioEntryKind
                    .FIFO
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .INTERPRETED
                )

            elif (
                entry.entry_type
                is CpioEntryType.SOCKET
            ):
                kind = (
                    AndroidBootImageCpioEntryKind
                    .SOCKET
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .INTERPRETED
                )

            elif (
                entry.entry_type
                is CpioEntryType.FILE
            ):
                if path in module_paths:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .KERNEL_MODULE
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif path in module_configuration_paths:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .KERNEL_MODULE_CONFIGURATION
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif path in init_paths:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .INIT_CONFIGURATION
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif path in fstab_paths:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .FSTAB_CONFIGURATION
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif path in ueventd_paths:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .UEVENTD_CONFIGURATION
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif path in {
                    "init",
                    "system/bin/init",
                }:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .INIT_BINARY
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif (
                    path.endswith(
                        ".so"
                    )
                    or "/lib/" in (
                        "/" + path
                    )
                    and ".so" in path.split(
                        "/"
                    )[-1]
                ):
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .SHARED_LIBRARY
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif (
                    entry.mode
                    & 0o111
                ):
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .EXECUTABLE
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .INTERPRETED
                    )

                elif path in canonical_source_paths:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .OTHER_FILE
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .CANONICAL_PARSING_ASSOCIATION
                    )
                    associated_source = (
                        canonical_sources_by_path[
                            path
                        ]
                    )

                elif path in blueprint_resource_sources:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .OTHER_FILE
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .PRESERVED_RESOURCE
                    )
                    associated_source = (
                        blueprint_resource_sources[
                            path
                        ]
                    )

                else:
                    kind = (
                        AndroidBootImageCpioEntryKind
                        .OTHER_FILE
                    )
                    disposition = (
                        AndroidBootImageCpioEntryDisposition
                        .PRESERVED_UNCLASSIFIED
                    )

            else:
                kind = (
                    AndroidBootImageCpioEntryKind
                    .UNKNOWN
                )
                disposition = (
                    AndroidBootImageCpioEntryDisposition
                    .PRESERVED_UNCLASSIFIED
                )

            interpretations.append(
                AndroidBootImageCpioEntryInterpretation(
                    entry=entry,
                    index=index,
                    kind=kind,
                    disposition=disposition,
                    associated_source=associated_source,
                )
            )

        return tuple(
            interpretations
        )

    @staticmethod
    def _resolve_kernel_module_reference(
        raw_reference,
        *,
        kernel_modules,
    ):
        reference = raw_reference.rstrip(
            ":"
        )

        exact_matches = tuple(
            module
            for module
            in kernel_modules
            if (
                module.android_path.as_posix()
                == reference
                or module.android_path.as_posix().lstrip(
                    "/"
                )
                == reference.lstrip(
                    "/"
                )
            )
        )

        if not exact_matches:
            basename_matches = tuple(
                module
                for module
                in kernel_modules
                if (
                    module.android_path.name
                    == reference
                )
            )

            exact_matches = (
                basename_matches
            )

        if (
            not exact_matches
            and not reference.endswith(
                ".ko"
            )
        ):
            stem_matches = tuple(
                module
                for module
                in kernel_modules
                if (
                    module.android_path.stem
                    == reference
                )
            )

            exact_matches = stem_matches

        if not exact_matches:
            reference_name = (
                reference
                .split("/")[-1]
            )

            reference_stem = (
                reference_name[:-3]
                if reference_name.endswith(
                    ".ko"
                )
                else reference_name
            )

            normalized_reference = (
                reference_stem.replace(
                    "-",
                    "_",
                )
            )

            normalized_matches = tuple(
                module
                for module
                in kernel_modules
                if (
                    module.android_path.stem.replace(
                        "-",
                        "_",
                    )
                    == normalized_reference
                )
            )

            exact_matches = normalized_matches

        if len(
            exact_matches
        ) == 1:
            return AndroidBootImageKernelModuleReference(
                raw_reference=raw_reference,
                resolution=(
                    AndroidBootImageKernelModuleResolution
                    .RESOLVED
                ),
                module=exact_matches[0],
                candidates=exact_matches,
            )

        if not exact_matches:
            return AndroidBootImageKernelModuleReference(
                raw_reference=raw_reference,
                resolution=(
                    AndroidBootImageKernelModuleResolution
                    .UNRESOLVED
                ),
                module=None,
                candidates=(),
            )

        return AndroidBootImageKernelModuleReference(
            raw_reference=raw_reference,
            resolution=(
                AndroidBootImageKernelModuleResolution
                .AMBIGUOUS
            ),
            module=None,
            candidates=exact_matches,
        )

    def _interpret_kernel_module_relationships(
        self,
        *,
        kernel_modules,
        configurations,
    ):
        load_entries = []
        dependency_entries = []
        alias_entries = []
        softdep_entries = []
        uninterpreted = []

        for configuration in configurations:
            kind = (
                configuration.configuration_kind
            )

            if kind not in {
                AndroidKernelModuleConfigurationKind.LOAD,
                AndroidKernelModuleConfigurationKind.DEP,
                AndroidKernelModuleConfigurationKind.ALIAS,
                AndroidKernelModuleConfigurationKind.SOFTDEP,
            }:
                continue

            for line in configuration.lines:
                tokens = line.tokens

                if (
                    kind
                    is AndroidKernelModuleConfigurationKind.LOAD
                ):
                    if not tokens:
                        uninterpreted.append(
                            AndroidBootImageKernelModuleUninterpretedLine(
                                configuration=configuration,
                                line=line,
                                reason=(
                                    "modules.load line contains "
                                    "no module tokens"
                                ),
                            )
                        )
                        continue

                    load_entries.append(
                        AndroidBootImageKernelModuleLoadEntry(
                            configuration=configuration,
                            line=line,
                            references=tuple(
                                self._resolve_kernel_module_reference(
                                    token,
                                    kernel_modules=kernel_modules,
                                )
                                for token
                                in tokens
                            ),
                        )
                    )
                    continue

                if (
                    kind
                    is AndroidKernelModuleConfigurationKind.DEP
                ):
                    if not tokens:
                        uninterpreted.append(
                            AndroidBootImageKernelModuleUninterpretedLine(
                                configuration=configuration,
                                line=line,
                                reason=(
                                    "modules.dep line contains "
                                    "no module token"
                                ),
                            )
                        )
                        continue

                    dependency_entries.append(
                        AndroidBootImageKernelModuleDependencyEntry(
                            configuration=configuration,
                            line=line,
                            module=(
                                self._resolve_kernel_module_reference(
                                    tokens[0],
                                    kernel_modules=kernel_modules,
                                )
                            ),
                            dependencies=tuple(
                                self._resolve_kernel_module_reference(
                                    token,
                                    kernel_modules=kernel_modules,
                                )
                                for token
                                in tokens[1:]
                            ),
                        )
                    )
                    continue

                if (
                    kind
                    is AndroidKernelModuleConfigurationKind.ALIAS
                ):
                    if (
                        len(
                            tokens
                        ) < 3
                        or tokens[0] != "alias"
                    ):
                        uninterpreted.append(
                            AndroidBootImageKernelModuleUninterpretedLine(
                                configuration=configuration,
                                line=line,
                                reason=(
                                    "modules.alias line does not use "
                                    "'alias <pattern> <module>' form"
                                ),
                            )
                        )
                        continue

                    alias_entries.append(
                        AndroidBootImageKernelModuleAliasEntry(
                            configuration=configuration,
                            line=line,
                            alias=" ".join(
                                tokens[1:-1]
                            ),
                            module=(
                                self._resolve_kernel_module_reference(
                                    tokens[-1],
                                    kernel_modules=kernel_modules,
                                )
                            ),
                        )
                    )
                    continue

                if (
                    len(
                        tokens
                    ) < 2
                    or tokens[0] != "softdep"
                ):
                    uninterpreted.append(
                        AndroidBootImageKernelModuleUninterpretedLine(
                            configuration=configuration,
                            line=line,
                            reason=(
                                "modules.softdep line does not use "
                                "'softdep <module> ...' form"
                            ),
                        )
                    )
                    continue

                pre_tokens = []
                post_tokens = []
                destination = None
                malformed = False

                for token in tokens[2:]:
                    if token == "pre:":
                        destination = pre_tokens
                        continue

                    if token == "post:":
                        destination = post_tokens
                        continue

                    if destination is None:
                        malformed = True
                        break

                    destination.append(
                        token
                    )

                if malformed:
                    uninterpreted.append(
                        AndroidBootImageKernelModuleUninterpretedLine(
                            configuration=configuration,
                            line=line,
                            reason=(
                                "modules.softdep dependency token "
                                "appears before pre:/post:"
                            ),
                        )
                    )
                    continue

                softdep_entries.append(
                    AndroidBootImageKernelModuleSoftDependencyEntry(
                        configuration=configuration,
                        line=line,
                        module=(
                            self._resolve_kernel_module_reference(
                                tokens[1],
                                kernel_modules=kernel_modules,
                            )
                        ),
                        pre=tuple(
                            self._resolve_kernel_module_reference(
                                token,
                                kernel_modules=kernel_modules,
                            )
                            for token
                            in pre_tokens
                        ),
                        post=tuple(
                            self._resolve_kernel_module_reference(
                                token,
                                kernel_modules=kernel_modules,
                            )
                            for token
                            in post_tokens
                        ),
                    )
                )

        return {
            "load": tuple(
                load_entries
            ),
            "dependency": tuple(
                dependency_entries
            ),
            "alias": tuple(
                alias_entries
            ),
            "softdep": tuple(
                softdep_entries
            ),
            "uninterpreted": tuple(
                uninterpreted
            ),
        }

    def _interpret_boot_image(
        self,
        image,
        *,
        kernel_by_component_artifact_id,
        boot_signature_by_artifact_id,
        ramdisk_by_component_artifact_id,
        bootconfig_by_component_artifact_id,
        dtbs_by_component_artifact_id,
        vendor_ramdisk_table_by_artifact_id,
    ) -> AndroidBootImageBootImageInterpretation:
        components = []

        for artifact in image.component_artifacts:
            semantic_name = artifact.semantic_name

            if semantic_name is None:
                raise ValueError(
                    "canonical boot component lacks semantic_name"
                )

            role = self._ROLE_BY_SEMANTIC_NAME.get(
                semantic_name,
                AndroidBootImageComponentRole.OTHER,
            )

            disposition = (
                AndroidBootImageInterpretationDisposition
                .PRESERVED_UNCLASSIFIED
                if (
                    role
                    is AndroidBootImageComponentRole.OTHER
                )
                else
                AndroidBootImageInterpretationDisposition
                .INTERPRETED
            )

            kernel = (
                kernel_by_component_artifact_id.get(
                    id(
                        artifact
                    )
                )
                if (
                    role
                    is AndroidBootImageComponentRole.KERNEL
                )
                else None
            )

            boot_signature = (
                boot_signature_by_artifact_id.get(
                    id(
                        artifact
                    )
                )
                if (
                    role
                    is AndroidBootImageComponentRole.BOOT_SIGNATURE
                )
                else None
            )

            ramdisk = (
                ramdisk_by_component_artifact_id.get(
                    id(
                        artifact
                    )
                )
                if (
                    role
                    is AndroidBootImageComponentRole.RAMDISK
                )
                else None
            )

            bootconfig = (
                bootconfig_by_component_artifact_id.get(
                    id(
                        artifact
                    )
                )
                if (
                    role
                    is AndroidBootImageComponentRole.BOOTCONFIG
                )
                else None
            )

            dtbs = (
                dtbs_by_component_artifact_id.get(
                    id(
                        artifact
                    ),
                    (),
                )
                if (
                    role
                    is AndroidBootImageComponentRole.DTB
                )
                else ()
            )

            vendor_ramdisk_table = (
                vendor_ramdisk_table_by_artifact_id.get(
                    id(
                        artifact
                    )
                )
                if (
                    role
                    is
                    AndroidBootImageComponentRole
                    .VENDOR_RAMDISK_TABLE
                )
                else None
            )

            components.append(
                AndroidBootImageComponentInterpretation(
                    artifact=artifact,
                    semantic_name=semantic_name,
                    role=role,
                    disposition=disposition,
                    kernel=kernel,
                    boot_signature=boot_signature,
                    ramdisk=ramdisk,
                    bootconfig=bootconfig,
                    dtbs=dtbs,
                    vendor_ramdisk_table=(
                        vendor_ramdisk_table
                    ),
                )
            )

        return AndroidBootImageBootImageInterpretation(
            image=image,
            components=tuple(
                components
            ),
        )

    @staticmethod
    def _fact(
        artifact,
        name: str,
    ):
        matches = tuple(
            fact.value
            for fact
            in artifact.facts
            if fact.name == name
        )

        if len(
            matches
        ) != 1:
            raise ValueError(
                "canonical DTBO entry must contain exactly one "
                f"{name!r} fact"
            )

        return matches[0]

    def _interpret_dtbo_entry(
        self,
        entry,
    ) -> AndroidBootImageDtboEntryInterpretation:
        artifact = entry.artifact

        if artifact.parent is None:
            raise ValueError(
                "canonical DTBO entry must retain its "
                "DTBO container parent"
            )

        return AndroidBootImageDtboEntryInterpretation(
            entry=entry,
            container=artifact.parent,
            entry_index=self._fact(
                artifact,
                "entry_index",
            ),
            offset_bytes=self._fact(
                artifact,
                "offset_bytes",
            ),
            declared_size_bytes=self._fact(
                artifact,
                "declared_size_bytes",
            ),
            dtbo_id=self._fact(
                artifact,
                "dtbo_id",
            ),
            dtbo_rev=self._fact(
                artifact,
                "dtbo_rev",
            ),
            custom=tuple(
                self._fact(
                    artifact,
                    f"dtbo_custom_{index}",
                )
                for index
                in range(
                    4
                )
            ),
            page_size_bytes=self._fact(
                artifact,
                "dtbo_page_size_bytes",
            ),
            table_total_size_bytes=self._fact(
                artifact,
                "dtbo_table_total_size_bytes",
            ),
            table_version=self._fact(
                artifact,
                "dtbo_table_version",
            ),
        )

    @staticmethod
    def _group_dtbo_containers(
        entries,
    ) -> tuple[
        AndroidBootImageDtboContainerInterpretation,
        ...,
    ]:
        ordered_containers = []
        grouped = {}

        for entry in entries:
            key = id(
                entry.container
            )

            if key not in grouped:
                grouped[key] = []
                ordered_containers.append(
                    entry.container
                )

            grouped[key].append(
                entry
            )

        return tuple(
            AndroidBootImageDtboContainerInterpretation(
                container=container,
                entries=tuple(
                    sorted(
                        grouped[
                            id(
                                container
                            )
                        ],
                        key=lambda entry: (
                            entry.entry_index
                        ),
                    )
                ),
            )
            for container
            in ordered_containers
        )

    def _interpret_vbmeta(
        self,
        vbmeta,
    ) -> AndroidBootImageAvbVbmetaInterpretation:
        source_kind = (
            AndroidBootImageAvbSourceKind.STANDALONE
            if (
                vbmeta.artifact
                is vbmeta.container_artifact
            )
            else AndroidBootImageAvbSourceKind.EMBEDDED
        )

        descriptors = tuple(
            self._interpret_avb_descriptor(
                descriptor
            )
            for descriptor
            in vbmeta.metadata.descriptors
        )

        return AndroidBootImageAvbVbmetaInterpretation(
            vbmeta=vbmeta,
            source_kind=source_kind,
            descriptors=descriptors,
        )

    @staticmethod
    def _interpret_avb_descriptor(
        descriptor,
    ) -> AndroidBootImageAvbDescriptorInterpretation:
        if isinstance(
            descriptor,
            AndroidParsedAvbPropertyDescriptor,
        ):
            kind = (
                AndroidBootImageAvbDescriptorKind.PROPERTY
            )
            target_partition = None

        elif isinstance(
            descriptor,
            AndroidParsedAvbHashtreeDescriptor,
        ):
            kind = (
                AndroidBootImageAvbDescriptorKind.HASHTREE
            )
            target_partition = descriptor.partition_name

        elif isinstance(
            descriptor,
            AndroidParsedAvbHashDescriptor,
        ):
            kind = (
                AndroidBootImageAvbDescriptorKind.HASH
            )
            target_partition = descriptor.partition_name

        elif isinstance(
            descriptor,
            AndroidParsedAvbKernelCmdlineDescriptor,
        ):
            kind = (
                AndroidBootImageAvbDescriptorKind.KERNEL_CMDLINE
            )
            target_partition = None

        elif isinstance(
            descriptor,
            AndroidParsedAvbChainPartitionDescriptor,
        ):
            kind = (
                AndroidBootImageAvbDescriptorKind.CHAIN_PARTITION
            )
            target_partition = descriptor.partition_name

        elif isinstance(
            descriptor,
            AndroidParsedAvbDescriptor,
        ):
            kind = (
                AndroidBootImageAvbDescriptorKind.UNKNOWN
            )
            target_partition = None

        else:
            raise TypeError(
                "unsupported canonical AVB descriptor type"
            )

        disposition = (
            AndroidBootImageInterpretationDisposition
            .PRESERVED_UNCLASSIFIED
            if (
                kind
                is AndroidBootImageAvbDescriptorKind.UNKNOWN
            )
            else
            AndroidBootImageInterpretationDisposition
            .INTERPRETED
        )

        return AndroidBootImageAvbDescriptorInterpretation(
            descriptor=descriptor,
            kind=kind,
            disposition=disposition,
            target_partition=target_partition,
        )

    @staticmethod
    def _interpret_avb_region(
        region,
        *,
        node_by_parsed_id,
    ) -> AndroidBootImageAvbRegionInterpretation:
        node = (
            node_by_parsed_id.get(
                id(
                    region.vbmeta
                )
            )
            if region.vbmeta is not None
            else None
        )

        if (
            region.disposition == "parsed"
            and node is None
        ):
            raise ValueError(
                "parsed AVB region references a VBMeta result "
                "outside the canonical VBMeta population"
            )

        return AndroidBootImageAvbRegionInterpretation(
            region=region,
            vbmeta=node,
        )

