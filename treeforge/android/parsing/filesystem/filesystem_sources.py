from __future__ import annotations

from dataclasses import replace
from pathlib import PurePosixPath

from treeforge.android.extraction import (
    AndroidExtractionResult,
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
)
from treeforge.android.filesystem.filesystem import (
    Filesystem,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.partition.inventory import (
    PartitionInventory,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidFilesystemView,
    AndroidParserFilesystemSource,
    AndroidPartitionFilesystem,
)


class AndroidFilesystemSourceBuildError(
    RuntimeError,
):
    """
    Raised when parser-ready filesystems cannot be built from Extraction state.
    """


class AndroidFilesystemSourceBuilder:
    """
    Build parser-facing filesystem sources from completed canonical state.

    This class performs no extraction or physical materialization.

    Every returned parser-facing filesystem retains the exact canonical
    InventoryPartition and filesystem Extraction artifact from which it was
    derived. Parser policy belongs here, after Extraction and Inventory.
    """

    def build(
        self,
        extraction: AndroidExtractionResult,
        inventory: PartitionInventory,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> tuple[
        AndroidParserFilesystemSource,
        ...,
    ]:
        """
        Build parser-facing filesystem sources from the complete canonical
        Filesystem Metadata inventory.

        FilesystemMetadataInventory is authoritative for physical filesystem
        root enumeration. Extraction and PartitionInventory are consumed only
        for canonical lineage classification and parser-facing identity.

        No filesystem root may enter Parsing unless Filesystem Metadata has
        already established that exact Extraction artifact.
        """

        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise TypeError(
                "extraction must be an AndroidExtractionResult"
            )

        if not isinstance(
            inventory,
            PartitionInventory,
        ):
            raise TypeError(
                "inventory must be a PartitionInventory"
            )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        filesystems = tuple(
            self._build_filesystem_source(
                entry=entry,
                extraction=extraction,
                inventory=inventory,
            )
            for entry in filesystem_inventory
        )

        self._validate_filesystem_conservation(
            filesystem_inventory=filesystem_inventory,
            filesystems=filesystems,
        )

        #
        # ``source_name`` is parser-facing semantic identity and therefore
        # may differ from the underlying Extraction semantic name.
        #
        # Physical identity remains the exact canonical filesystem artifact
        # owned by FilesystemMetadataInventory.
        #
        name_counts: dict[str, int] = {}

        for source in filesystems:
            name_counts[
                source.source_name
            ] = (
                name_counts.get(
                    source.source_name,
                    0,
                )
                + 1
            )

        canonical_filesystems: list[
            AndroidParserFilesystemSource
        ] = []

        for source in filesystems:
            if (
                name_counts[
                    source.source_name
                ] > 1
                and source.partition is None
            ):
                physical_identity = (
                    source.artifact.path.name
                )

                if not physical_identity:
                    raise AndroidFilesystemSourceBuildError(
                        "duplicate non-partition parser filesystem "
                        "source exposes no stable physical identity: "
                        f"{source.source_name}"
                    )

                source = replace(
                    source,
                    source_name=(
                        f"{source.source_name}:"
                        f"{physical_identity}"
                    ),
                )

            canonical_filesystems.append(
                source
            )

        seen_names: set[str] = set()

        for source in canonical_filesystems:
            if source.source_name in seen_names:
                raise AndroidFilesystemSourceBuildError(
                    "duplicate parser filesystem source identity "
                    "after canonical lineage qualification: "
                    f"{source.source_name}"
                )

            seen_names.add(
                source.source_name
            )

        return tuple(
            sorted(
                canonical_filesystems,
                key=lambda value: (
                    value.source_name
                ),
            )
        )

    @staticmethod
    def _build_filesystem_source(
        *,
        entry,
        extraction: AndroidExtractionResult,
        inventory: PartitionInventory,
    ) -> AndroidParserFilesystemSource:
        """
        Convert one exact Filesystem Metadata root into one parser source.

        Physical enumeration is complete before this method is called.
        Extraction lineage is inspected only to derive parser-facing role and
        semantic identity.
        """

        result = entry.result
        artifact = result.artifact

        if (
            artifact.kind
            is not ExtractionArtifactKind.DIRECTORY
        ):
            raise AndroidFilesystemSourceBuildError(
                "Filesystem Metadata contains a non-directory "
                "parser filesystem artifact: "
                f"{artifact.path}"
            )

        if (
            artifact.operation
            not in {
                ExtractionOperation.FILESYSTEM_EXTRACTION,
                ExtractionOperation.CPIO_EXTRACTION,
            }
        ):
            raise AndroidFilesystemSourceBuildError(
                "Filesystem Metadata contains an unsupported "
                "parser filesystem operation: "
                f"{artifact.operation}: {artifact.path}"
            )

        if not any(
            candidate is artifact
            for candidate
            in extraction.artifacts
        ):
            raise AndroidFilesystemSourceBuildError(
                "Filesystem Metadata artifact is not retained by "
                "the canonical Extraction result: "
                f"{artifact.path}"
            )

        filesystem = Filesystem(
            artifact.path
        )

        partition = result.partition

        if (
            partition is not None
            and not any(
                candidate is partition
                for candidate
                in inventory.partitions
            )
        ):
            raise AndroidFilesystemSourceBuildError(
                "Filesystem Metadata partition provenance is not "
                "retained by canonical PartitionInventory: "
                f"{partition.name}"
            )

        if (
            artifact.operation
            is ExtractionOperation.CPIO_EXTRACTION
        ):
            return (
                AndroidFilesystemSourceBuilder
                ._build_ramdisk_source(
                    artifact=artifact,
                    filesystem=filesystem,
                    partition=partition,
                )
            )

        parent = artifact.parent

        if (
            parent is not None
            and parent.operation
            is ExtractionOperation.APEX_CONTAINER_EXTRACTION
        ):
            return (
                AndroidFilesystemSourceBuilder
                ._build_apex_source(
                    artifact=artifact,
                    filesystem=filesystem,
                    partition=partition,
                )
            )

        direct_partition = (
            partition is not None
            and parent is partition.artifact
        )

        if direct_partition:
            views = (
                AndroidFilesystemSourceBuilder
                ._build_views(
                    partition_name=(
                        partition.base_name
                    ),
                    filesystem=filesystem,
                )
            )

            return AndroidPartitionFilesystem(
                source_name=(
                    partition.base_name
                ),
                partition=partition,
                artifact=artifact,
                filesystem=filesystem,
                views=views,
            )

        source_name = (
            artifact.semantic_name
        )

        if (
            not isinstance(
                source_name,
                str,
            )
            or not source_name.strip()
        ):
            raise AndroidFilesystemSourceBuildError(
                "canonical non-partition filesystem "
                "has no semantic Extraction identity: "
                f"{artifact.path}"
            )

        return AndroidParserFilesystemSource(
            source_name=source_name,
            artifact=artifact,
            filesystem=filesystem,
            views=(
                AndroidFilesystemView(
                    filesystem=filesystem,
                    android_prefix=(
                        PurePosixPath("/")
                    ),
                ),
            ),
            partition=partition,
        )

    @staticmethod
    def _build_ramdisk_source(
        *,
        artifact: ExtractedArtifact,
        filesystem: Filesystem,
        partition,
    ) -> AndroidParserFilesystemSource:
        """
        Derive parser-facing ramdisk identity from canonical Extraction
        lineage without re-enumerating CPIO roots.
        """

        ramdisk_cpio = artifact.parent

        if ramdisk_cpio is None:
            raise AndroidFilesystemSourceBuildError(
                "CPIO extraction artifact has no ramdisk CPIO parent"
            )

        ramdisk_component = ramdisk_cpio.parent

        if ramdisk_component is None:
            raise AndroidFilesystemSourceBuildError(
                "ramdisk CPIO lineage has no ramdisk component"
            )

        boot_family = ramdisk_component.parent

        if (
            boot_family is None
            or not boot_family.semantic_name
        ):
            raise AndroidFilesystemSourceBuildError(
                "ramdisk lineage has no boot-family identity"
            )

        return AndroidParserFilesystemSource(
            source_name=boot_family.semantic_name,
            artifact=artifact,
            filesystem=filesystem,
            views=(
                AndroidFilesystemView(
                    filesystem=filesystem,
                    android_prefix=PurePosixPath("/"),
                ),
            ),
            partition=partition,
        )

    @staticmethod
    def _build_apex_source(
        *,
        artifact: ExtractedArtifact,
        filesystem: Filesystem,
        partition,
    ) -> AndroidParserFilesystemSource:
        """
        Derive specialized APEX parser identity from an already-canonical
        Filesystem Metadata root.
        """

        payload = artifact.parent

        if (
            payload is None
            or payload.operation
            is not ExtractionOperation.APEX_CONTAINER_EXTRACTION
            or payload.semantic_name != "apex_payload"
        ):
            raise AndroidFilesystemSourceBuildError(
                "APEX parser source does not have canonical "
                "apex_payload lineage: "
                f"{artifact.path}"
            )

        container = payload.parent

        if container is None:
            raise AndroidFilesystemSourceBuildError(
                "APEX payload filesystem lineage has no "
                "container artifact"
            )

        outer_container = container

        while (
            outer_container.operation
            is ExtractionOperation.APEX_CONTAINER_EXTRACTION
        ):
            parent = outer_container.parent

            if parent is None:
                raise AndroidFilesystemSourceBuildError(
                    "APEX container lineage terminates before "
                    "its discovered outer container"
                )

            outer_container = parent

        if (
            outer_container.operation
            is not ExtractionOperation.NESTED_ARTIFACT_DISCOVERY
        ):
            raise AndroidFilesystemSourceBuildError(
                "APEX payload filesystem lineage does not "
                "terminate at a canonical nested artifact"
            )

        source_identity = (
            outer_container.path.name
        )

        if not source_identity:
            raise AndroidFilesystemSourceBuildError(
                "APEX outer container has no stable "
                "physical identity"
            )

        lineage_identity = (
            AndroidFilesystemSourceBuilder
            ._apex_lineage_identity(
                outer_container
            )
        )

        return AndroidParserFilesystemSource(
            source_name=(
                "apex:"
                f"{lineage_identity}:"
                f"{source_identity}"
            ),
            artifact=artifact,
            filesystem=filesystem,
            views=(
                AndroidFilesystemView(
                    filesystem=filesystem,
                    android_prefix=PurePosixPath("/"),
                ),
            ),
            partition=partition,
        )

    @staticmethod
    def _validate_filesystem_conservation(
        *,
        filesystem_inventory: FilesystemMetadataInventory,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> None:
        """
        Require one-to-one conservation of canonical filesystem artifacts
        across the Filesystem Metadata -> Parsing Preparation boundary.
        """

        expected = {
            id(entry.artifact): entry.artifact
            for entry in filesystem_inventory
        }

        actual: dict[
            int,
            ExtractedArtifact,
        ] = {}

        for source in filesystems:
            artifact = source.artifact
            identity = id(
                artifact
            )

            if identity in actual:
                raise AndroidFilesystemSourceBuildError(
                    "Parsing Preparation duplicated canonical "
                    "filesystem artifact identity: "
                    f"{artifact.path}"
                )

            actual[
                identity
            ] = artifact

        expected_ids = set(
            expected
        )

        actual_ids = set(
            actual
        )

        if expected_ids == actual_ids:
            return

        missing = tuple(
            expected[identity].path.as_posix()
            for identity
            in expected_ids - actual_ids
        )

        unexpected = tuple(
            actual[identity].path.as_posix()
            for identity
            in actual_ids - expected_ids
        )

        raise AndroidFilesystemSourceBuildError(
            "Parsing Preparation filesystem conservation failed: "
            f"missing={missing}, unexpected={unexpected}"
        )

    @staticmethod
    def _apex_lineage_identity(
        outer_container: ExtractedArtifact,
    ) -> str:
        """
        Return the canonical parser-source lineage owning one APEX container.

        APEX basenames are not globally unique across Android source roots.
        The same APEX may legitimately exist in multiple extracted partition
        or ramdisk filesystems.

        Parsing therefore preserves the nearest canonical filesystem-bearing
        ancestor as part of parser source identity rather than collapsing
        distinct Extraction lineages by filename alone.
        """

        if not isinstance(
            outer_container,
            ExtractedArtifact,
        ):
            raise TypeError(
                "outer_container must be an ExtractedArtifact"
            )

        ancestor = (
            outer_container.parent
        )

        while ancestor is not None:
            if (
                ancestor.operation
                in {
                    ExtractionOperation
                    .FILESYSTEM_EXTRACTION,
                    ExtractionOperation
                    .CPIO_EXTRACTION,
                }
                and ancestor.kind
                is ExtractionArtifactKind.DIRECTORY
            ):
                identity = (
                    ancestor.semantic_name
                    or ancestor.path.name
                )

                if identity:
                    return identity

            ancestor = (
                ancestor.parent
            )

        #
        # Nested-artifact discovery always preserves its physical parent
        # lineage. If no canonical filesystem-bearing ancestor exists,
        # preserve the immediate parent identity rather than collapsing to
        # the APEX basename alone.
        #
        parent = (
            outer_container.parent
        )

        if parent is not None:
            identity = (
                parent.semantic_name
                or parent.path.name
            )

            if identity:
                return identity

        raise AndroidFilesystemSourceBuildError(
            "APEX outer container lineage exposes no stable "
            "parser source identity"
        )

    @staticmethod
    def _owning_partition(
        artifact: ExtractedArtifact,
        inventory: PartitionInventory,
    ) -> InventoryPartition | None:
        """
        Return the exact canonical partition owning one Extraction lineage.

        Parser-facing descendant filesystems retain their immediate
        Extraction artifact separately. Partition provenance is inherited
        only when that artifact's canonical parent chain reaches the exact
        Extraction artifact already owned by one InventoryPartition.

        No path, filename, semantic-name, source-name, slot, Android-version,
        or device-specific inference is permitted here.
        """

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            inventory,
            PartitionInventory,
        ):
            raise TypeError(
                "inventory must be a PartitionInventory"
            )

        current: ExtractedArtifact | None = artifact

        while current is not None:
            matches = tuple(
                partition
                for partition in inventory.partitions
                if partition.artifact is current
            )

            if len(matches) > 1:
                raise AndroidFilesystemSourceBuildError(
                    "Extraction artifact identity is owned by "
                    "multiple InventoryPartition entries"
                )

            if matches:
                return matches[0]

            current = current.parent

        return None

    @staticmethod
    def _build_views(
        *,
        partition_name: str,
        filesystem: Filesystem,
    ) -> tuple[
        AndroidFilesystemView,
        ...,
    ]:
        """
        Build parser-visible Android namespace views over one physical
        extracted partition filesystem.
        """

        if not isinstance(
            partition_name,
            str,
        ):
            raise TypeError(
                "partition_name must be a string"
            )

        if not partition_name:
            raise ValueError(
                "partition_name must not be empty"
            )

        if not isinstance(
            filesystem,
            Filesystem,
        ):
            raise TypeError(
                "filesystem must be a Filesystem"
            )

        primary_android_prefix = (
            PurePosixPath("/")
            if partition_name == "system"
            else (
                PurePosixPath("/")
                / partition_name
            )
        )

        views: list[
            AndroidFilesystemView
        ] = [
            AndroidFilesystemView(
                filesystem=filesystem,
                android_prefix=(
                    primary_android_prefix
                ),
            )
        ]

        if partition_name == "system":
            embedded_system_root = (
                filesystem.root
                / "system"
            )

            if embedded_system_root.is_dir():
                views.append(
                    AndroidFilesystemView(
                        filesystem=Filesystem(
                            embedded_system_root
                        ),
                        android_prefix=PurePosixPath(
                            "/system"
                        ),
                    )
                )

        return tuple(
            views
        )
