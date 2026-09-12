from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.extraction.model import (
    ExtractionOperation,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.apk import (
    AndroidApkParsingResult,
)
from treeforge.android.parsing.elf import (
    AndroidElfParsingResult,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.artifact.classifier import (
    AndroidUniverseArtifactClassifier,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactClassificationOrigin,
    AndroidUniverseArtifactDeploymentRole,
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactKind,
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


class AndroidUniverseArtifactRequirementBuilder:
    """
    Promote every canonical regular filesystem file into Universe ownership.

    Filesystem Metadata remains the exclusive owner of physical enumeration.

    Parsing source identity provides stronger semantic evidence for artifacts
    already recognized as intrinsic Android parser sources. Path-based
    classification remains fallback evidence for every other artifact.

    No Discovery, Extraction, filesystem traversal, parsing, rendering,
    copying, or filesystem writes occur here.
    """

    _PARSING_KIND_MAP = {
        AndroidModelSourceKind.INIT: (
            AndroidUniverseArtifactKind.INIT_RC
        ),
        AndroidModelSourceKind.FSTAB: (
            AndroidUniverseArtifactKind.FSTAB
        ),
        AndroidModelSourceKind.UEVENTD: (
            AndroidUniverseArtifactKind.UEVENTD_RC
        ),
        AndroidModelSourceKind.PROPERTY: (
            AndroidUniverseArtifactKind.PROPERTY_FILE
        ),
        AndroidModelSourceKind.SELINUX: (
            AndroidUniverseArtifactKind.SELINUX_POLICY
        ),
        AndroidModelSourceKind.INPUT_KEY_LAYOUT: (
            AndroidUniverseArtifactKind.ANDROID_KEY_LAYOUT
        ),
        AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP: (
            AndroidUniverseArtifactKind.ANDROID_KEY_CHARACTER_MAP
        ),
        AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION: (
            AndroidUniverseArtifactKind
            .ANDROID_INPUT_DEVICE_CONFIGURATION
        ),
        AndroidModelSourceKind.FONT: (
            AndroidUniverseArtifactKind.FONT
        ),
    }

    def __init__(
        self,
        *,
        classifier: AndroidUniverseArtifactClassifier
        | None = None,
    ) -> None:
        self.classifier = (
            classifier
            if classifier is not None
            else AndroidUniverseArtifactClassifier()
        )

        if not isinstance(
            self.classifier,
            AndroidUniverseArtifactClassifier,
        ):
            raise TypeError(
                "classifier must be an "
                "AndroidUniverseArtifactClassifier"
            )

    def build(
        self,
        source_inventory: FilesystemMetadataInventory,
        *,
        parsing_source_inventory: (
            AndroidModelSourceInventory
            | None
        ) = None,
        apk_parsing: (
            AndroidApkParsingResult
            | None
        ) = None,
        elf_parsing: (
            AndroidElfParsingResult
            | None
        ) = None,
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ] = (),
    ) -> AndroidUniverseArtifactRequirementInventory:
        if not isinstance(
            source_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "source_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if (
            parsing_source_inventory is not None
            and not isinstance(
                parsing_source_inventory,
                AndroidModelSourceInventory,
            )
        ):
            raise TypeError(
                "parsing_source_inventory must be an "
                "AndroidModelSourceInventory or None"
            )

        if (
            apk_parsing is not None
            and not isinstance(
                apk_parsing,
                AndroidApkParsingResult,
            )
        ):
            raise TypeError(
                "apk_parsing must be an "
                "AndroidApkParsingResult or None"
            )

        if (
            elf_parsing is not None
            and not isinstance(
                elf_parsing,
                AndroidElfParsingResult,
            )
        ):
            raise TypeError(
                "elf_parsing must be an "
                "AndroidElfParsingResult or None"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement objects"
            )

        parsing_evidence = (
            self._build_parsing_evidence(
                source_inventory=source_inventory,
                parsing_source_inventory=(
                    parsing_source_inventory
                ),
            )
            if parsing_source_inventory is not None
            else {}
        )

        parsing_android_paths = {}

        if parsing_source_inventory is not None:
            for source in parsing_source_inventory.sources:
                kind = self._kind_from_parsing_source(
                    source
                )

                if kind is None:
                    continue

                filesystem_source = (
                    source.filesystem_source
                )

                try:
                    source_inventory_entry = (
                        source_inventory
                        .entry_for_artifact(
                            filesystem_source.artifact
                        )
                    )
                except KeyError as error:
                    raise ValueError(
                        "Parsing source does not preserve a canonical "
                        "filesystem inventory artifact: "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    ) from error

                try:
                    metadata_path = (
                        source_inventory_entry
                        .filesystem_path_for_materialized_path(
                            source.host_path
                        )
                    )
                except ValueError as error:
                    raise ValueError(
                        "Parsing source does not project into its "
                        "canonical filesystem inventory: "
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    ) from error

                evidence_key = (
                    id(
                        source_inventory_entry.artifact
                    ),
                    metadata_path,
                )

                parsing_android_paths.setdefault(
                    evidence_key,
                    set(),
                ).add(
                    source.android_path.as_posix()
                )

        parsing_android_paths = {
            key: tuple(
                sorted(
                    paths
                )
            )
            for key, paths
            in parsing_android_paths.items()
        }

        apk_evidence = (
            self._build_apk_evidence(
                source_inventory=source_inventory,
                apk_parsing=apk_parsing,
            )
            if apk_parsing is not None
            else {}
        )

        elf_evidence = (
            self._build_elf_evidence(
                source_inventory=source_inventory,
                elf_parsing=elf_parsing,
            )
            if elf_parsing is not None
            else frozenset()
        )

        apex_evidence = (
            self._build_apex_evidence(
                source_inventory=source_inventory,
                apex_requirements=apex_requirements,
            )
        )

        deployment_roles = (
            self._build_deployment_roles(
                source_inventory
            )
        )

        requirements: list[
            AndroidUniverseArtifactRequirement
        ] = []

        for inventory_entry in source_inventory.entries:
            for metadata_entry in (
                inventory_entry
                .result
                .metadata
                .entries
                .values()
            ):
                if (
                    metadata_entry.entry_type
                    is not FilesystemEntryType.FILE
                ):
                    continue

                evidence_key = (
                    id(
                        inventory_entry.artifact
                    ),
                    metadata_entry.path,
                )

                semantic_kinds = (
                    parsing_evidence.get(
                        evidence_key
                    )
                )

                elf_backed = (
                    evidence_key
                    in elf_evidence
                )

                apk_classification = (
                    apk_evidence.get(
                        evidence_key
                    )
                )

                apex_classification = (
                    apex_evidence.get(
                        evidence_key
                    )
                )

                if semantic_kinds is not None:
                    kinds = semantic_kinds
                    disposition = (
                        self._disposition_from_parsing_kinds(
                            semantic_kinds
                        )
                    )
                    classification_origin = (
                        AndroidUniverseArtifactClassificationOrigin
                        .PARSING_EVIDENCE
                    )

                elif apk_classification is not None:
                    (
                        apk_kind,
                        disposition,
                    ) = apk_classification

                    kinds = (
                        apk_kind,
                    )

                    classification_origin = (
                        AndroidUniverseArtifactClassificationOrigin
                        .PARSING_EVIDENCE
                    )

                elif apex_classification is not None:
                    (
                        apex_kind,
                        disposition,
                    ) = apex_classification

                    kinds = (
                        apex_kind,
                    )

                    classification_origin = (
                        AndroidUniverseArtifactClassificationOrigin
                        .APEX_EVIDENCE
                    )

                else:
                    (
                        classified_kind,
                        disposition,
                    ) = self.classifier.classify(
                        metadata_entry.path
                    )

                    # CHRE nanoapps commonly use a .so suffix, but
                    # /etc/chre/*.so is not an ordinary dynamically linked
                    # shared-library deployment.  Preserve the canonical
                    # CHRE payload family before generic ELF refinement.
                    path_parts = tuple(
                        part.lower()
                        for part
                        in PurePosixPath(
                            metadata_entry.path
                        ).parts
                    )

                    if (
                        classified_kind
                        is AndroidUniverseArtifactKind
                        .SHARED_LIBRARY
                        and any(
                            path_parts[index:index + 2]
                            == ("etc", "chre")
                            for index in range(
                                max(
                                    0,
                                    len(path_parts) - 1,
                                )
                            )
                        )
                    ):
                        classified_kind = (
                            AndroidUniverseArtifactKind
                            .CHRE_NANOAPP_METADATA
                        )
                        disposition = (
                            AndroidUniverseArtifactDisposition
                            .PRESERVE
                        )

                    if (
                        elf_backed
                        and disposition
                        is AndroidUniverseArtifactDisposition
                        .UNCLASSIFIED
                        and classified_kind
                        in {
                            AndroidUniverseArtifactKind
                            .SHARED_LIBRARY,
                            AndroidUniverseArtifactKind
                            .HAL_SHARED_LIBRARY,
                            AndroidUniverseArtifactKind
                            .EXECUTABLE,
                            AndroidUniverseArtifactKind
                            .HARDWARE_SERVICE,
                        }
                    ):
                        disposition = (
                            AndroidUniverseArtifactDisposition
                            .INVENTORY_ONLY
                        )

                    kinds = (
                        classified_kind,
                    )

                    classification_origin = (
                        AndroidUniverseArtifactClassificationOrigin
                        .UNRESOLVED
                        if classified_kind
                        is AndroidUniverseArtifactKind.UNKNOWN
                        else
                        AndroidUniverseArtifactClassificationOrigin
                        .PATH_CLASSIFIER
                    )

                deployment_role = deployment_roles[
                    id(inventory_entry)
                ]

                # Non-selected direct partition variants remain
                # canonical Universe evidence, but they do not independently
                # create reconstruction obligations. Preserve stronger
                # Parsing/APEX/family decisions; only otherwise-unresolved
                # alternative artifacts become inventory-only.
                if (
                    disposition
                    is AndroidUniverseArtifactDisposition.UNCLASSIFIED
                    and deployment_role
                    is AndroidUniverseArtifactDeploymentRole
                    .ALTERNATIVE_PARTITION
                ):
                    disposition = (
                        AndroidUniverseArtifactDisposition
                        .INVENTORY_ONLY
                    )

                # Nested and boot-derived filesystem artifacts remain
                # canonical Universe inventory, but they are consumed through
                # their owning container or boot-image realization rather
                # than installed independently by the generated source tree.
                #
                # Preserve stronger family-specific decisions above.  This
                # refinement applies only where artifact disposition remains
                # explicitly unresolved.
                if (
                    disposition
                    is AndroidUniverseArtifactDisposition.UNCLASSIFIED
                    and deployment_role
                    in {
                        AndroidUniverseArtifactDeploymentRole
                        .NESTED_FILESYSTEM,
                        AndroidUniverseArtifactDeploymentRole
                        .BOOT_FILESYSTEM,
                    }
                ):
                    disposition = (
                        AndroidUniverseArtifactDisposition
                        .INVENTORY_ONLY
                    )

                # Installed framework JARs require one additional
                # canonical distinction beyond Java-container identity.
                #
                # A direct /system/framework JAR is platform runtime output:
                # the AOSP platform build owns producing it, so the installed
                # factory copy remains canonical inventory rather than an
                # independent device-tree prebuilt.
                #
                # A direct framework JAR outside /system belongs to an Android
                # extension/product/vendor runtime surface.  Without a
                # canonical source representation, its exact installed bytes
                # remain part of the reconstructed device contract.
                #
                # This uses only the exact Android-visible path retained by
                # Parsing plus the already-derived deployment role.  Host
                # paths, package names, vendor names, and AOSP checkout
                # contents do not participate.
                if (
                    disposition
                    is AndroidUniverseArtifactDisposition.UNCLASSIFIED
                    and deployment_role
                    is AndroidUniverseArtifactDeploymentRole.DIRECT_PARTITION
                    and AndroidUniverseArtifactKind.FRAMEWORK_JAR
                    in kinds
                ):
                    framework_paths = tuple(
                        path
                        for path
                        in parsing_android_paths.get(
                            evidence_key,
                            (),
                        )
                        if (
                            path.endswith(".jar")
                            and "/framework/" in path
                        )
                    )

                    if len(
                        framework_paths
                    ) == 1:
                        framework_path = (
                            framework_paths[0]
                        )

                        if framework_path.startswith(
                            "/system/framework/"
                        ):
                            disposition = (
                                AndroidUniverseArtifactDisposition
                                .INVENTORY_ONLY
                            )
                        else:
                            disposition = (
                                AndroidUniverseArtifactDisposition
                                .PRESERVE
                            )

                # Some direct-partition artifact families intrinsically
                # represent opaque installed payloads whose exact bytes
                # remain part of the device contract.  Apply this only to
                # otherwise-unresolved direct artifacts; stronger Parsing
                # or family-specific decisions above remain authoritative.
                if (
                    disposition
                    is AndroidUniverseArtifactDisposition.UNCLASSIFIED
                    and deployment_role
                    is AndroidUniverseArtifactDeploymentRole.DIRECT_PARTITION
                    and any(
                        kind
                        in {
                            AndroidUniverseArtifactKind.FIRMWARE,
                            AndroidUniverseArtifactKind.SPEECH_MODEL_DATA,
                            AndroidUniverseArtifactKind.MACHINE_LEARNING_MODEL,
                            AndroidUniverseArtifactKind.EBPF_OBJECT,
                            AndroidUniverseArtifactKind.MODEM_PROFILE,
                            AndroidUniverseArtifactKind.AUDIO_DSP_DATA,
                            AndroidUniverseArtifactKind.CHRE_NANOAPP_METADATA,
                            AndroidUniverseArtifactKind.ESIM_SUPPORT_DATA,
                            AndroidUniverseArtifactKind.DEVICE_CALIBRATION_DATA,
                            AndroidUniverseArtifactKind.CHRE_RUNTIME_DATA,
                            AndroidUniverseArtifactKind.FACE_DETECTION_MODEL_DATA,
                            AndroidUniverseArtifactKind.INPUT_METHOD_DATA,
                            AndroidUniverseArtifactKind.FONT,
                            AndroidUniverseArtifactKind.TRUST_CERTIFICATE,
                            AndroidUniverseArtifactKind.CERTIFICATE_CHAIN,
                            AndroidUniverseArtifactKind.OTA_CERTIFICATE_ARCHIVE,
                        }
                        for kind in kinds
                    )
                ):
                    disposition = (
                        AndroidUniverseArtifactDisposition.PRESERVE
                    )

                # Platform/runtime data that is useful canonical inventory
                # but does not independently create source-tree realization
                # work remains inventory-only.
                if (
                    disposition
                    is AndroidUniverseArtifactDisposition.UNCLASSIFIED
                    and deployment_role
                    is AndroidUniverseArtifactDeploymentRole.DIRECT_PARTITION
                    and any(
                        kind
                        in {
                            AndroidUniverseArtifactKind.MEDIA_ASSET,
                            AndroidUniverseArtifactKind.HYPHENATION_DICTIONARY,
                            AndroidUniverseArtifactKind.HYPHENATION_LICENSE,
                            AndroidUniverseArtifactKind.WALLPAPER_ASSET,
                            AndroidUniverseArtifactKind.RUNTIME_BITCODE,
                        }
                        for kind in kinds
                    )
                ):
                    disposition = (
                        AndroidUniverseArtifactDisposition
                        .INVENTORY_ONLY
                    )

                # Canonical source/configuration artifacts whose installed
                # form provides semantic input rather than an opaque payload.
                if (
                    disposition
                    is AndroidUniverseArtifactDisposition.UNCLASSIFIED
                    and deployment_role
                    is AndroidUniverseArtifactDeploymentRole.DIRECT_PARTITION
                    and any(
                        kind
                        in {
                            AndroidUniverseArtifactKind.KERNEL_MODULE_METADATA,
                            AndroidUniverseArtifactKind.SECCOMP_POLICY,
                            AndroidUniverseArtifactKind.OPENCL_ICD_CONFIGURATION,
                        }
                        for kind in kinds
                    )
                ):
                    disposition = (
                        AndroidUniverseArtifactDisposition
                        .SEMANTIC_SOURCE
                    )

                requirements.append(
                    AndroidUniverseArtifactRequirement(
                        inventory_entry=inventory_entry,
                        metadata_entry=metadata_entry,
                        deployment_role=deployment_role,
                        kinds=kinds,
                        disposition=disposition,
                        classification_origin=(
                            classification_origin
                        ),
                    )
                )

        requirements.sort(
            key=lambda requirement: (
                requirement.key
            )
        )

        return (
            AndroidUniverseArtifactRequirementInventory(
                source_inventory=source_inventory,
                requirements=tuple(
                    requirements
                ),
            )
        )

    @staticmethod
    def _disposition_from_parsing_kinds(
        kinds: tuple[
            AndroidUniverseArtifactKind,
            ...,
        ],
    ) -> AndroidUniverseArtifactDisposition:
        """
        Convert intrinsic Parsing evidence into artifact disposition.

        Parsing proves artifact format/content semantics, but that does not
        universally imply that the installed file is a semantic source.

        Input configuration files are semantic source material.

        Font bytes remain exact opaque payload candidates and therefore enter
        normal deployment-role refinement unresolved.

        Installed framework JAR Parsing proves container identity only; it
        does not decide source-built versus prebuilt realization.
        """

        if any(
            kind
            in {
                AndroidUniverseArtifactKind.FONT,
                AndroidUniverseArtifactKind.FRAMEWORK_JAR,
            }
            for kind in kinds
        ):
            return (
                AndroidUniverseArtifactDisposition
                .UNCLASSIFIED
            )

        return (
            AndroidUniverseArtifactDisposition
            .SEMANTIC_SOURCE
        )

    @classmethod
    def _build_deployment_roles(
        cls,
        source_inventory: FilesystemMetadataInventory,
    ) -> dict[
        int,
        AndroidUniverseArtifactDeploymentRole,
    ]:
        """
        Classify exact filesystem inventories by canonical deployment role.

        Direct partition filesystems are identified strictly by Extraction
        identity:

            filesystem.operation is FILESYSTEM_EXTRACTION
            filesystem.parent is partition.artifact

        No host paths, filenames, partition-name suffix stripping, or content
        hashes participate in this classification.

        When multiple direct partition variants share a canonical base name,
        selection follows the existing TreeForge canonical slot policy:

        - exact unsuffixed partition first;
        - otherwise one unique variant;
        - otherwise one ``_a`` variant;
        - otherwise reject ambiguity.
        """

        direct_entries = []

        roles: dict[
            int,
            AndroidUniverseArtifactDeploymentRole,
        ] = {}

        for inventory_entry in source_inventory.entries:
            artifact = inventory_entry.artifact
            partition = inventory_entry.result.partition

            if (
                partition is not None
                and artifact.operation
                is ExtractionOperation.FILESYSTEM_EXTRACTION
                and artifact.parent
                is partition.artifact
            ):
                direct_entries.append(
                    inventory_entry
                )
                continue

            if (
                artifact.operation
                is ExtractionOperation.CPIO_EXTRACTION
            ):
                roles[
                    id(inventory_entry)
                ] = (
                    AndroidUniverseArtifactDeploymentRole
                    .BOOT_FILESYSTEM
                )
            else:
                roles[
                    id(inventory_entry)
                ] = (
                    AndroidUniverseArtifactDeploymentRole
                    .NESTED_FILESYSTEM
                )

        by_base_name = {}

        for inventory_entry in direct_entries:
            partition = inventory_entry.result.partition

            if partition is None:
                raise ValueError(
                    "direct partition filesystem lost "
                    "canonical partition identity"
                )

            by_base_name.setdefault(
                partition.base_name,
                [],
            ).append(
                inventory_entry
            )

        for base_name, entries in by_base_name.items():
            exact = tuple(
                entry
                for entry in entries
                if (
                    entry.result.partition is not None
                    and entry.result.partition.name
                    == base_name
                )
            )

            if len(exact) > 1:
                raise ValueError(
                    "multiple direct filesystems claim one "
                    "unsuffixed canonical partition: "
                    f"{base_name}"
                )

            if exact:
                selected = exact[0]

            elif len(entries) == 1:
                selected = entries[0]

            else:
                preferred = tuple(
                    entry
                    for entry in entries
                    if (
                        entry.result.partition is not None
                        and entry.result.partition.slot_suffix
                        == "_a"
                    )
                )

                if len(preferred) != 1:
                    names = ", ".join(
                        sorted(
                            entry.result.partition.name
                            for entry in entries
                            if entry.result.partition is not None
                        )
                    )

                    raise ValueError(
                        "unable to select one canonical direct "
                        "partition filesystem for "
                        f"{base_name}: {names}"
                    )

                selected = preferred[0]

            for entry in entries:
                roles[
                    id(entry)
                ] = (
                    AndroidUniverseArtifactDeploymentRole
                    .DIRECT_PARTITION
                    if entry is selected
                    else
                    AndroidUniverseArtifactDeploymentRole
                    .ALTERNATIVE_PARTITION
                )

        if len(roles) != len(source_inventory.entries):
            raise ValueError(
                "artifact deployment-role classification "
                "did not cover every filesystem inventory entry"
            )

        return roles

    @classmethod
    def _build_elf_evidence(
        cls,
        *,
        source_inventory: FilesystemMetadataInventory,
        elf_parsing: AndroidElfParsingResult,
    ) -> frozenset[
        tuple[
            int,
            str,
        ]
    ]:
        """
        Index filesystem-backed ELF Parsing by exact canonical filesystem
        artifact + metadata path identity.

        Embedded/extraction-backed ELF objects have no independent filesystem
        Artifact requirement and are intentionally excluded.

        The dedicated ELF Universe family owns preservation, ELF role,
        dependencies, aliases, and downstream reconstruction semantics.
        """

        evidence = set()

        for parsed in elf_parsing.elf_files:
            source = parsed.source

            if not source.is_filesystem_backed:
                continue

            filesystem_source = (
                source.filesystem_source
            )

            if filesystem_source is None:
                raise ValueError(
                    "filesystem-backed ELF source lost "
                    "filesystem_source identity"
                )

            try:
                inventory_entry = (
                    source_inventory
                    .entry_for_artifact(
                        filesystem_source.artifact
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "ELF Parsing filesystem source does not map "
                    "to canonical Filesystem Metadata identity: "
                    f"{source.host_path}"
                ) from error

            try:
                metadata_path = (
                    inventory_entry
                    .filesystem_path_for_materialized_path(
                        source.host_path
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "ELF Parsing host path does not belong to "
                    "its canonical filesystem artifact: "
                    f"{source.host_path}"
                ) from error

            metadata_entry = (
                inventory_entry
                .result
                .metadata
                .get(
                    metadata_path
                )
            )

            if metadata_entry is None:
                raise ValueError(
                    "ELF Parsing source does not map to "
                    "canonical filesystem metadata: "
                    f"{metadata_path}"
                )

            if (
                metadata_entry.entry_type
                is not FilesystemEntryType.FILE
            ):
                raise ValueError(
                    "ELF Parsing source does not map to "
                    "a regular filesystem file"
                )

            if (
                source.metadata_entry is not None
                and source.metadata_entry
                is not metadata_entry
            ):
                raise ValueError(
                    "ELF Parsing changed exact canonical "
                    "Filesystem Metadata entry identity: "
                    f"{metadata_path}"
                )

            evidence.add(
                (
                    id(
                        inventory_entry.artifact
                    ),
                    metadata_entry.path,
                )
            )

        return frozenset(
            evidence
        )

    @classmethod
    def _build_apk_evidence(
        cls,
        *,
        source_inventory: FilesystemMetadataInventory,
        apk_parsing: AndroidApkParsingResult,
    ) -> dict[
        tuple[
            int,
            str,
        ],
        tuple[
            AndroidUniverseArtifactKind,
            AndroidUniverseArtifactDisposition,
        ],
    ]:
        """
        Join parsed installed APK/RRO identity to exact Filesystem Metadata.

        APK package realization is owned by the dedicated canonical APK
        requirement family. The generic Artifact requirement therefore
        remains canonical inventory but does not independently create a
        duplicate reconstruction obligation.
        """

        evidence = {}

        for parsed in apk_parsing.packages:
            filesystem_source = (
                parsed.source.filesystem_source
            )

            try:
                inventory_entry = (
                    source_inventory
                    .entry_for_artifact(
                        filesystem_source.artifact
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "APK Parsing filesystem source does not map "
                    "to canonical Filesystem Metadata identity: "
                    f"{parsed.source.source_name}:"
                    f"{parsed.source.apk_android_path.as_posix()}"
                ) from error

            try:
                metadata_path = (
                    inventory_entry
                    .filesystem_path_for_materialized_path(
                        parsed.source.apk_host_path
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "APK Parsing host path does not belong to "
                    "its canonical filesystem artifact: "
                    f"{parsed.source.source_name}:"
                    f"{parsed.source.apk_android_path.as_posix()}"
                ) from error

            metadata_entry = (
                inventory_entry
                .result
                .metadata
                .get(
                    metadata_path
                )
            )

            if metadata_entry is None:
                raise ValueError(
                    "APK Parsing source does not map to "
                    "canonical filesystem metadata: "
                    f"{metadata_path}"
                )

            if (
                metadata_entry.entry_type
                is not FilesystemEntryType.FILE
            ):
                raise ValueError(
                    "APK Parsing source does not map to "
                    "a regular filesystem file"
                )

            kind = (
                AndroidUniverseArtifactKind
                .RUNTIME_RESOURCE_OVERLAY
                if parsed.overlay is not None
                else AndroidUniverseArtifactKind.APK
            )

            key = (
                id(
                    inventory_entry.artifact
                ),
                metadata_entry.path,
            )

            classification = (
                kind,
                AndroidUniverseArtifactDisposition
                .INVENTORY_ONLY,
            )

            existing = evidence.get(
                key
            )

            if (
                existing is not None
                and existing != classification
            ):
                raise ValueError(
                    "conflicting canonical APK Parsing evidence "
                    f"for {metadata_entry.path}: "
                    f"{existing} != {classification}"
                )

            evidence[
                key
            ] = classification

        return evidence

    @classmethod
    def _build_apex_evidence(
        cls,
        *,
        source_inventory: FilesystemMetadataInventory,
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> dict[
        tuple[
            int,
            str,
        ],
        tuple[
            AndroidUniverseArtifactKind,
            AndroidUniverseArtifactDisposition,
        ],
    ]:
        """
        Build context-sensitive artifact evidence from canonical APEX identity.

        The Filesystem Metadata entry owns the exact materialized filesystem
        artifact. For an APEX payload filesystem its immediate parent is the
        canonical ``apex_payload`` Extraction artifact, whose parent is the
        exact APEX container retained by AndroidUniverseApexRequirement.

        Universe joins those objects strictly by identity. It does not infer
        APEX ownership from filenames, source names, host paths, partition
        names, or Android logical paths.

        CTS shim ``/etc/hash.txt`` semantics are valid only inside the exact
        ``com.android.apex.cts.shim`` APEX context. An identically named file
        anywhere else remains available to normal classification and may remain
        UNKNOWN.
        """

        requirements_by_artifact: dict[
            int,
            AndroidUniverseApexRequirement,
        ] = {}

        for requirement in apex_requirements:
            artifact_id = id(
                requirement.artifact
            )

            existing = (
                requirements_by_artifact.get(
                    artifact_id
                )
            )

            if (
                existing is not None
                and existing is not requirement
            ):
                raise ValueError(
                    "multiple APEX requirements preserve the "
                    "same canonical Extraction artifact"
                )

            requirements_by_artifact[
                artifact_id
            ] = requirement

        evidence: dict[
            tuple[
                int,
                str,
            ],
            tuple[
                AndroidUniverseArtifactKind,
                AndroidUniverseArtifactDisposition,
            ],
        ] = {}

        # Promote the exact installed APEX container itself from canonical
        # APEX evidence before considering artifacts inside its payload.
        #
        # deployment_context preserves both the exact enclosing filesystem
        # Extraction artifact and the exact relative source path established
        # from Extraction ancestry. Convert that materialized location through
        # Filesystem Metadata's canonical path mapping rather than rebuilding
        # an Android path from partition names or filenames.
        for requirement in apex_requirements:
            deployment_context = (
                requirement.deployment_context
            )

            filesystem_artifact = (
                deployment_context.filesystem_artifact
            )

            try:
                inventory_entry = (
                    source_inventory.entry_for_artifact(
                        filesystem_artifact
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "APEX deployment filesystem does not map to "
                    "canonical Filesystem Metadata identity: "
                    f"{requirement.requirement_id} -> "
                    f"{filesystem_artifact.path}"
                ) from error

            materialized_path = (
                filesystem_artifact.path.joinpath(
                    *deployment_context.relative_path.parts
                )
            )

            try:
                metadata_path = (
                    inventory_entry
                    .filesystem_path_for_materialized_path(
                        materialized_path
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "APEX deployment path does not belong to its "
                    "canonical filesystem artifact: "
                    f"{requirement.requirement_id} -> "
                    f"{materialized_path}"
                ) from error

            metadata_entry = (
                inventory_entry
                .result
                .metadata
                .get(
                    metadata_path
                )
            )

            if metadata_entry is None:
                raise ValueError(
                    "APEX deployment path does not map to a "
                    "canonical filesystem metadata entry: "
                    f"{requirement.requirement_id} -> "
                    f"{metadata_path}"
                )

            if (
                metadata_entry.entry_type
                is not FilesystemEntryType.FILE
            ):
                raise ValueError(
                    "canonical APEX deployment entry is not "
                    "a regular filesystem file: "
                    f"{requirement.requirement_id} -> "
                    f"{metadata_entry.path}"
                )

            key = (
                id(
                    inventory_entry.artifact
                ),
                metadata_entry.path,
            )

            existing = evidence.get(
                key
            )

            classification = (
                AndroidUniverseArtifactKind.APEX,
                AndroidUniverseArtifactDisposition
                .INVENTORY_ONLY,
            )

            if (
                existing is not None
                and existing != classification
            ):
                raise ValueError(
                    "conflicting canonical APEX evidence for "
                    f"{metadata_entry.path}: "
                    f"{existing} != {classification}"
                )

            evidence[
                key
            ] = classification

        for inventory_entry in source_inventory.entries:
            filesystem_artifact = (
                inventory_entry.artifact
            )

            payload = (
                filesystem_artifact.parent
            )

            if payload is None:
                continue

            container = (
                payload.parent
            )

            if container is None:
                continue

            apex_requirement = (
                requirements_by_artifact.get(
                    id(
                        container
                    )
                )
            )

            if apex_requirement is None:
                continue

            if (
                apex_requirement.apex_name
                != "com.android.apex.cts.shim"
            ):
                continue

            metadata_entry = (
                inventory_entry
                .result
                .metadata
                .get(
                    "/etc/hash.txt"
                )
            )

            if metadata_entry is None:
                continue

            if (
                metadata_entry.entry_type
                is not FilesystemEntryType.FILE
            ):
                raise ValueError(
                    "CTS shim /etc/hash.txt exists but is not "
                    "a canonical regular filesystem file"
                )

            key = (
                id(
                    filesystem_artifact
                ),
                metadata_entry.path,
            )

            evidence[
                key
            ] = (
                AndroidUniverseArtifactKind
                .CTS_SHIM_ALLOWED_HASHES,
                AndroidUniverseArtifactDisposition
                .INVENTORY_ONLY,
            )

        return evidence

    @classmethod
    def _build_parsing_evidence(
        cls,
        *,
        source_inventory: FilesystemMetadataInventory,
        parsing_source_inventory: AndroidModelSourceInventory,
    ) -> dict[
        tuple[
            int,
            str,
        ],
        tuple[
            AndroidUniverseArtifactKind,
            ...,
        ],
    ]:
        """
        Index Parsing evidence by exact canonical filesystem identity.

        The Extraction artifact backing the physical filesystem is the
        authoritative filesystem identity. Partition ownership and parser
        source names remain provenance/context only.

        Filesystem-native metadata paths are derived from materialized host
        paths through FilesystemMetadataInventoryEntry rather than reconstructed
        from Android logical/view paths.
        """

        evidence_sets: dict[
            tuple[
                int,
                str,
            ],
            set[
                AndroidUniverseArtifactKind,
            ],
        ] = {}

        for source in parsing_source_inventory.sources:
            filesystem_source = (
                source.filesystem_source
            )

            try:
                inventory_entry = (
                    source_inventory
                    .entry_for_artifact(
                        filesystem_source.artifact
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "Parsing source filesystem does not map to "
                    "canonical Filesystem Metadata identity: "
                    f"{source.source_name}:"
                    f"{source.android_path.as_posix()} "
                    f"-> {filesystem_source.artifact.path}"
                ) from error

            kind = cls._kind_from_parsing_source(
                source
            )

            if kind is None:
                continue

            try:
                metadata_path = (
                    inventory_entry
                    .filesystem_path_for_materialized_path(
                        source.host_path
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "Parsing source host path does not belong to "
                    "its canonical filesystem artifact: "
                    f"{source.source_name}:"
                    f"{source.android_path.as_posix()} "
                    f"-> {source.host_path}"
                ) from error

            metadata_entry = (
                inventory_entry
                .result
                .metadata
                .get(
                    metadata_path
                )
            )

            if metadata_entry is None:
                raise ValueError(
                    "Parsing source does not map to its "
                    "canonical filesystem metadata entry: "
                    f"{source.source_name}:"
                    f"{source.android_path.as_posix()} "
                    f"-> {metadata_path}"
                )

            key = (
                id(
                    inventory_entry.artifact
                ),
                metadata_entry.path,
            )

            evidence_sets.setdefault(
                key,
                set(),
            ).add(
                kind
            )

        return {
            key: tuple(
                sorted(
                    kinds,
                    key=lambda item: item.value,
                )
            )
            for key, kinds in evidence_sets.items()
        }

    @classmethod
    def _kind_from_parsing_source(
        cls,
        source: AndroidModelSource,
    ) -> AndroidUniverseArtifactKind | None:
        """
        Translate intrinsic Parsing source-family identity into a Universe
        artifact family.

        VINTF is intentionally resolved from its Android-visible filename
        because Parsing's source kind represents the format family while
        Universe distinguishes manifest, compatibility matrix, and other
        VINTF XML artifacts.

        SELinux contexts remain distinguishable from compiled/policy source
        artifacts using their canonical filename.
        """

        if source.kind is AndroidModelSourceKind.VINTF:
            name = (
                source.android_path.name.lower()
            )

            if name == "manifest.xml":
                return (
                    AndroidUniverseArtifactKind
                    .VINTF_MANIFEST
                )

            if (
                name == "compatibility_matrix.xml"
                or "compatibility_matrix" in name
            ):
                return (
                    AndroidUniverseArtifactKind
                    .VINTF_MATRIX
                )

            return (
                AndroidUniverseArtifactKind
                .VINTF_XML
            )

        if source.kind is AndroidModelSourceKind.SHELL_SCRIPT:
            return AndroidUniverseArtifactKind.EXECUTABLE

        if source.kind is AndroidModelSourceKind.JAVA_ARCHIVE:
            parts = tuple(
                part.lower()
                for part
                in source.android_path.parts
            )

            if "framework" in parts:
                return (
                    AndroidUniverseArtifactKind
                    .FRAMEWORK_JAR
                )

            return None

        if source.kind is AndroidModelSourceKind.SELINUX:
            name = (
                source.android_path.name.lower()
            )

            if (
                name.endswith("_contexts")
                or name
                in {
                    "file_contexts",
                    "property_contexts",
                    "service_contexts",
                    "hwservice_contexts",
                    "vndservice_contexts",
                    "seapp_contexts",
                    "keystore2_key_contexts",
                }
            ):
                return (
                    AndroidUniverseArtifactKind
                    .SELINUX_CONTEXTS
                )

        return cls._PARSING_KIND_MAP.get(
            source.kind
        )