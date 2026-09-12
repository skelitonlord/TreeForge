from __future__ import annotations

from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
)
from treeforge.android.extraction.result import (
    AndroidExtractionResult,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
    PartitionInventory,
)
from treeforge.android.partition.layout import (
    LayoutPartition,
    PartitionLayout,
    PartitionOrigin,
    PartitionPayloadState,
)


class PartitionInventoryResolutionError(
    RuntimeError,
):
    """
    Raised when canonical extracted artifacts cannot produce PartitionInventory.
    """


class PartitionInventoryResolver:
    """
    Build PartitionInventory from already-accessible Extraction artifacts.

    This resolver performs no extraction, conversion, unpacking, copying, or
    materialization.

    Partition identity and structural facts come from PartitionLayout.

    Physical accessibility and derivation evidence come from
    AndroidExtractionResult.

    Exact upstream PartitionSource provenance is preserved.
    """

    def resolve(
        self,
        layout: PartitionLayout,
        extraction: AndroidExtractionResult,
    ) -> PartitionInventory:
        """
        Build a canonical partition inventory from completed extraction state.
        """

        normalized_layout = (
            self._validate_layout(
                layout
            )
        )

        normalized_extraction = (
            self._validate_extraction(
                extraction
            )
        )

        partitions = tuple(
            self._build_inventory_partition(
                partition,
                normalized_extraction,
            )
            for partition
            in normalized_layout.partitions
            if (
                partition.payload_state
                is not PartitionPayloadState.UNAVAILABLE
            )
        )

        return PartitionInventory(
            partitions=partitions
        )

    @staticmethod
    def _validate_layout(
        layout: PartitionLayout,
    ) -> PartitionLayout:
        if not isinstance(
            layout,
            PartitionLayout,
        ):
            raise TypeError(
                "layout must be a PartitionLayout"
            )

        return layout

    @staticmethod
    def _validate_extraction(
        extraction: AndroidExtractionResult,
    ) -> AndroidExtractionResult:
        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise TypeError(
                "extraction must be an AndroidExtractionResult"
            )

        return extraction

    def _build_inventory_partition(
        self,
        partition: LayoutPartition,
        extraction: AndroidExtractionResult,
    ) -> InventoryPartition:
        artifact = (
            self._resolve_artifact(
                partition,
                extraction,
            )
        )

        self._validate_artifact(
            partition,
            artifact,
        )

        return InventoryPartition(
            name=partition.name,
            artifact=artifact,
            slot_suffix=partition.slot_suffix,
        )

    @staticmethod
    def _resolve_artifact(
        partition: LayoutPartition,
        extraction: AndroidExtractionResult,
    ) -> ExtractedArtifact:
        if partition.source is None:
            raise PartitionInventoryResolutionError(
                "Partition has no canonical source provenance: "
                f"{partition.name}"
            )

        source = (
            partition.source.artifact
        )

        candidates = (
            extraction.artifacts_for_source(
                source
            )
        )

        if (
            partition.origin
            is PartitionOrigin.SUPER
        ):
            base_candidates = tuple(
                artifact
                for artifact
                in candidates
                if (
                    artifact.semantic_name
                    == partition.name
                    and artifact.operation
                    is (
                        ExtractionOperation
                        .LOGICAL_PARTITION_EXTRACTION
                    )
                )
            )
        else:
            base_candidates = tuple(
                artifact
                for artifact
                in candidates
                if (
                    artifact.semantic_name
                    == partition.name
                    and artifact.operation
                    in (
                        ExtractionOperation
                        .SOURCE_ADOPTION,
                        ExtractionOperation
                        .ARCHIVE_MEMBER_EXTRACTION,
                    )
                )
            )

        if not base_candidates:
            raise PartitionInventoryResolutionError(
                "No canonical extracted artifact exists "
                f"for partition: {partition.name}"
            )

        if len(base_candidates) != 1:
            raise PartitionInventoryResolutionError(
                "Canonical extraction state contains "
                "ambiguous base artifacts for partition: "
                f"{partition.name}"
            )

        base = (
            base_candidates[0]
        )

        raw = (
            extraction.child_of(
                base,
                operation=(
                    ExtractionOperation
                    .SPARSE_TO_RAW
                ),
            )
        )

        if raw is not None:
            return raw

        return base

    @staticmethod
    def _validate_artifact(
        partition: LayoutPartition,
        artifact: ExtractedArtifact,
    ) -> None:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise PartitionInventoryResolutionError(
                "partition extraction lookup returned "
                f"an invalid artifact: {partition.name}"
            )

        if (
            artifact.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise PartitionInventoryResolutionError(
                "partition inventory requires a file artifact: "
                f"{partition.name}"
            )

        if not artifact.path.exists():
            raise PartitionInventoryResolutionError(
                "partition extraction artifact does not exist: "
                f"{partition.name}: {artifact.path}"
            )

        if not artifact.path.is_file():
            raise PartitionInventoryResolutionError(
                "partition extraction artifact is not a "
                f"regular file: {partition.name}: "
                f"{artifact.path}"
            )

        expected_source = (
            partition.source.artifact
            if partition.source is not None
            else None
        )

        if artifact.source is not expected_source:
            raise PartitionInventoryResolutionError(
                "partition inventory must preserve exact "
                "upstream ProviderArtifact identity for "
                f"{partition.name}"
            )

        if (
            partition.origin
            is PartitionOrigin.SUPER
            and not any(
                lineage_artifact.operation
                is (
                    ExtractionOperation
                    .LOGICAL_PARTITION_EXTRACTION
                )
                for lineage_artifact
                in artifact.lineage
            )
        ):
            raise PartitionInventoryResolutionError(
                "logical partition requires "
                "a logical-partition extraction artifact: "
                f"{partition.name}"
            )