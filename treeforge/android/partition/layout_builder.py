from __future__ import annotations

from pathlib import Path

from treeforge.android.partition.layout import (
    LayoutBlockDevice,
    LayoutPartition,
    LayoutPartitionGroup,
    PartitionLayout,
    PartitionLayoutSource,
    PartitionOrigin,
    PartitionPayloadState,
)
from treeforge.android.extraction.partition.lpdump_parser import (
    LpBlockDevice,
    LpGroup,
    LpPartition,
    LpdumpMetadata,
)
from treeforge.android.extraction.partition.liblp_structure import (
    LiblpGroupRecord,
    LiblpPartitionRecord,
    LiblpStructure,
)
from treeforge.android.partition.source import (
    PartitionSource,
)
from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactKind,
)


class PartitionLayoutBuildError(ValueError):
    """
    Raised when source metadata cannot produce a partition layout.
    """


class PartitionLayoutBuilder:
    """
    Build TreeForge's canonical immutable partition layout.

    The builder converts source-specific partition information into the
    source-independent PartitionLayout model.

    This first implementation supports dynamic-partition metadata produced by
    LpdumpParser. Standalone-image conversion will be added separately.
    """

    SECTOR_SIZE_BYTES = 512

    def from_lpdump(
        self,
        metadata: LpdumpMetadata,
        super_image: Path,
        *,
        source: PartitionSource | None = None,
    ) -> PartitionLayout:
        normalized_metadata = self._validate_metadata(metadata)
        normalized_super_image = self._validate_super_image(super_image)

        if (
            source is not None
            and not isinstance(source, PartitionSource)
        ):
            raise TypeError(
                "source must be a PartitionSource or None"
            )

        partitions = tuple(
            self._build_partition(
                partition,
                normalized_super_image,
                source=source,
            )
            for partition in normalized_metadata.partitions
        )

        groups = tuple(
            self._build_group(group)
            for group in normalized_metadata.groups
        )

        block_devices = tuple(
            self._build_lpdump_block_device(block_device)
            for block_device in normalized_metadata.block_devices
        )

        return PartitionLayout(
            source=PartitionLayoutSource.SUPER,
            partitions=partitions,
            groups=groups,
            block_devices=block_devices,
        )


    def from_liblp_structure(
        self,
        structure: LiblpStructure,
        *,
        source: PartitionSource | None = None,
    ) -> PartitionLayout:
        """
        Build canonical dynamic-partition topology directly from TreeForge's
        decoded on-disk liblp structure.

        This path is appropriate for metadata-only liblp artifacts such as
        super_empty, where physical topology is canonical but logical payload
        extents may intentionally be absent.
        """

        if not isinstance(
            structure,
            LiblpStructure,
        ):
            raise TypeError(
                "structure must be a LiblpStructure"
            )

        if (
            source is not None
            and not isinstance(
                source,
                PartitionSource,
            )
        ):
            raise TypeError(
                "source must be a PartitionSource or None"
            )

        groups = tuple(
            self._build_liblp_group(
                group
            )
            for group
            in structure.groups
        )

        block_devices = tuple(
            self._build_liblp_block_device(
                block_device
            )
            for block_device
            in structure.block_devices
        )

        partitions = tuple(
            self._build_liblp_partition(
                partition,
                structure,
                source=source,
            )
            for partition
            in structure.partitions
        )

        return PartitionLayout(
            source=PartitionLayoutSource.SUPER,
            partitions=partitions,
            groups=groups,
            block_devices=block_devices,
        )

    def from_standalone_images(
        self,
        images: tuple[
            Path,
            ...,
        ],
    ) -> PartitionLayout:
        """
        Build a canonical layout from standalone partition images.

        Each image filename becomes the exact partition name after removing
        the final ``.img`` suffix.

        Examples:

        - system.img -> system
        - vendor_a.img -> vendor_a
        - system_ext.img -> system_ext

        Args:
            images:
                Immutable tuple of standalone partition image paths.

        Returns:
            Canonical immutable standalone partition layout.

        Raises:
            TypeError:
                If images is not a tuple or contains a non-Path value.

            FileNotFoundError:
                If an image does not exist.

            IsADirectoryError:
                If an image path is a directory.
        """

        normalized_images = (
            self._validate_standalone_images(
                images
            )
        )

        partitions = tuple(
            self._build_standalone_partition(
                image
            )
            for image in normalized_images
        )

        return PartitionLayout(
            source=PartitionLayoutSource.STANDALONE,
            partitions=partitions,
            groups=(),
        )

    def from_standalone_artifacts(
        self,
        artifacts: tuple[
            ProviderArtifact,
            ...,
        ],
    ) -> PartitionLayout:
        """
        Build a canonical standalone layout directly from Discovery artifacts.

        Discovery provenance is authoritative.

        A partition does not need to have been materialized in order to exist
        in PartitionLayout.

        Physical accessibility is owned by Extraction and is intentionally not
        copied from Discovery artifacts into the structural Layout model.
        """

        if not isinstance(
            artifacts,
            tuple,
        ):
            raise TypeError(
                "artifacts must be a tuple"
            )

        partitions: list[
            LayoutPartition
        ] = []

        for artifact in artifacts:
            if not isinstance(
                artifact,
                ProviderArtifact,
            ):
                raise TypeError(
                    "artifacts must contain "
                    "ProviderArtifact objects"
                )

            if (
                artifact.kind
                is not ProviderArtifactKind.IMAGE
            ):
                raise PartitionLayoutBuildError(
                    "Standalone partition artifact must "
                    "have image structural kind: "
                    f"{artifact.source_name}"
                )

            partitions.append(
                self._build_standalone_artifact(
                    artifact
                )
            )

        return PartitionLayout(
            source=PartitionLayoutSource.STANDALONE,
            partitions=tuple(
                partitions
            ),
            groups=(),
        )

    @staticmethod
    def _build_standalone_partition(
        image: Path,
    ) -> LayoutPartition:
        """
        Convert one standalone image into a canonical partition.
        """

        name = image.name.removesuffix(
            ".img"
        )

        slot_suffix: str | None = None

        if name.endswith("_a"):
            slot_suffix = "_a"
        elif name.endswith("_b"):
            slot_suffix = "_b"

        return LayoutPartition(
            name=name,
            origin=PartitionOrigin.STANDALONE,
            payload_state=PartitionPayloadState.AVAILABLE,
            size_bytes=image.stat().st_size,
            readonly=None,
            slot_suffix=slot_suffix,
            group=None,
        )

    @classmethod
    def _validate_standalone_images(
        cls,
        images: tuple[
            Path,
            ...,
        ],
    ) -> tuple[
        Path,
        ...,
    ]:
        """
        Validate standalone partition image paths.
        """

        if not isinstance(
            images,
            tuple,
        ):
            raise TypeError(
                "images must be a tuple"
            )

        normalized: list[Path] = []

        for image in images:
            normalized.append(
                cls._validate_standalone_image(
                    image
                )
            )

        return tuple(
            normalized
        )

    @staticmethod
    def _validate_standalone_image(
        image: Path,
    ) -> Path:
        """
        Validate one standalone partition image.
        """

        if not isinstance(
            image,
            Path,
        ):
            raise TypeError(
                "standalone image must be a pathlib.Path"
            )

        if image.suffix != ".img":
            raise PartitionLayoutBuildError(
                f"Standalone partition image must use "
                f"the .img suffix: {image}"
            )

        if not image.exists():
            raise FileNotFoundError(
                f"Standalone partition image does not exist: "
                f"{image}"
            )

        if image.is_dir():
            raise IsADirectoryError(
                f"Standalone partition image cannot be "
                f"a directory: {image}"
            )

        if not image.is_file():
            raise PartitionLayoutBuildError(
                f"Standalone partition image must be "
                f"a regular file: {image}"
            )

        return image

    @staticmethod
    def _build_standalone_artifact(
        artifact: ProviderArtifact,
    ) -> LayoutPartition:
        """
        Interpret one exact Discovery artifact as a standalone partition.

        Semantic classification supplies the canonical partition identity.

        Physical image accessibility is established later by Extraction.
        """

        name = (
            artifact.classification.value
        )

        slot_suffix: str | None = None

        if name.endswith(
            "_a"
        ):
            slot_suffix = "_a"

        elif name.endswith(
            "_b"
        ):
            slot_suffix = "_b"

        return LayoutPartition(
            name=name,
            origin=PartitionOrigin.STANDALONE,
            source=PartitionSource(
                artifact=artifact
            ),
            payload_state=PartitionPayloadState.AVAILABLE,
            size_bytes=(
                artifact.provenance.size_bytes
            ),
            readonly=None,
            slot_suffix=slot_suffix,
            group=None,
        )

    @staticmethod
    def _build_liblp_block_device(
        block_device,
    ) -> LayoutBlockDevice:
        """
        Preserve one exact decoded liblp physical block-device record.
        """

        return LayoutBlockDevice(
            partition_name=block_device.partition_name,
            size_bytes=block_device.size_bytes,
            first_logical_sector=block_device.first_logical_sector,
            alignment_bytes=block_device.alignment_bytes,
            alignment_offset_bytes=block_device.alignment_offset_bytes,
            flags=(
                frozenset()
                if block_device.flags == 0
                else frozenset(
                    {
                        f"liblp_raw_flags:{block_device.flags}"
                    }
                )
            ),
        )

    def _build_liblp_partition(
        self,
        partition: LiblpPartitionRecord,
        structure: LiblpStructure,
        *,
        source: PartitionSource | None = None,
    ) -> LayoutPartition:
        """
        Convert one literal liblp partition record into canonical topology.

        Payload availability is derived only from physically described extents.
        """

        if not isinstance(
            partition,
            LiblpPartitionRecord,
        ):
            raise TypeError(
                "partition must be a LiblpPartitionRecord"
            )

        extent_start = (
            partition.first_extent_index
        )
        extent_end = (
            extent_start
            + partition.num_extents
        )

        extents = (
            structure.extents[
                extent_start:extent_end
            ]
        )

        sector_count = sum(
            extent.num_sectors
            for extent in extents
        )

        if (
            partition.group_index < 0
            or partition.group_index
            >= len(structure.groups)
        ):
            raise PartitionLayoutBuildError(
                "liblp partition references invalid group index: "
                f"{partition.name}: {partition.group_index}"
            )

        group = (
            structure.groups[
                partition.group_index
            ]
        )

        slot_suffix: str | None = None

        if partition.name.endswith("_a"):
            slot_suffix = "_a"
        elif partition.name.endswith("_b"):
            slot_suffix = "_b"

        return LayoutPartition(
            name=partition.name,
            origin=PartitionOrigin.SUPER,
            source=source,
            payload_state=(
                PartitionPayloadState.AVAILABLE
                if sector_count > 0
                else PartitionPayloadState.UNAVAILABLE
            ),
            size_bytes=(
                sector_count
                * self.SECTOR_SIZE_BYTES
            ),
            readonly=bool(
                partition.attributes & 1
            ),
            slot_suffix=slot_suffix,
            group=group.name,
        )

    @staticmethod
    def _build_liblp_group(
        group: LiblpGroupRecord,
    ) -> LayoutPartitionGroup:
        """
        Convert one literal liblp group record into canonical topology.
        """

        if not isinstance(
            group,
            LiblpGroupRecord,
        ):
            raise TypeError(
                "group must be a LiblpGroupRecord"
            )

        slot_suffix: str | None = None

        if group.name.endswith("_a"):
            slot_suffix = "_a"
        elif group.name.endswith("_b"):
            slot_suffix = "_b"

        return LayoutPartitionGroup(
            name=group.name,
            maximum_size_bytes=(
                group.maximum_size_bytes
            ),
            slot_suffix=slot_suffix,
            flags=(
                frozenset()
                if group.flags == 0
                else frozenset(
                    {
                        f"liblp_raw_flags:{group.flags}"
                    }
                )
            ),
        )

    @staticmethod
    def _build_lpdump_block_device(
        block_device: LpBlockDevice,
    ) -> LayoutBlockDevice:
        # Preserve exactly the physical facts normalized lpdump exposes.
        # Alignment/raw integer flag fields remain unknown on this path.
        if not isinstance(block_device, LpBlockDevice):
            raise TypeError(
                "block_device must be an LpBlockDevice"
            )

        return LayoutBlockDevice(
            partition_name=block_device.name,
            size_bytes=block_device.size_bytes,
            first_logical_sector=block_device.first_sector,
            flags=block_device.flags,
        )

    def _build_partition(
        self,
        partition: LpPartition,
        super_image: Path,
        *,
        source: PartitionSource | None = None,
    ) -> LayoutPartition:
        """
        Convert one lpdump partition into a canonical layout partition.

        Discovery provenance for the containing super artifact is retained by
        exact PartitionSource identity when available.
        """

        return LayoutPartition(
            name=partition.name,
            origin=PartitionOrigin.SUPER,
            source=source,
            payload_state=(
                PartitionPayloadState.AVAILABLE
                if partition.sector_count > 0
                else PartitionPayloadState.UNAVAILABLE
            ),
            size_bytes=(
                partition.sector_count
                * self.SECTOR_SIZE_BYTES
            ),
            readonly=partition.is_readonly,
            slot_suffix=partition.slot_suffix,
            group=partition.group,
        )

    @staticmethod
    def _build_group(
        group: LpGroup,
    ) -> LayoutPartitionGroup:
        """
        Convert one lpdump group into a canonical layout group.
        """

        return LayoutPartitionGroup(
            name=group.name,
            maximum_size_bytes=(
                group.maximum_size_bytes
            ),
            slot_suffix=group.slot_suffix,
            flags=group.flags,
        )

    @staticmethod
    def _validate_metadata(
        metadata: LpdumpMetadata,
    ) -> LpdumpMetadata:
        """
        Validate parsed metadata supplied to the builder.
        """

        if not isinstance(
            metadata,
            LpdumpMetadata,
        ):
            raise TypeError(
                "metadata must be LpdumpMetadata"
            )

        return metadata

    @staticmethod
    def _validate_super_image(
        super_image: Path,
    ) -> Path:
        """
        Validate the source super image.
        """

        if not isinstance(
            super_image,
            Path,
        ):
            raise TypeError(
                "super_image must be a pathlib.Path"
            )

        if not super_image.exists():
            raise FileNotFoundError(
                f"Super image does not exist: "
                f"{super_image}"
            )

        if super_image.is_dir():
            raise IsADirectoryError(
                f"Super image cannot be a directory: "
                f"{super_image}"
            )

        if not super_image.is_file():
            raise PartitionLayoutBuildError(
                f"Super image must be a regular file: "
                f"{super_image}"
            )

        return super_image