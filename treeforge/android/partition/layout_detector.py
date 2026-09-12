from __future__ import annotations

from pathlib import Path
from typing import Protocol

from treeforge.android.partition.layout import (
    PartitionLayout,
    PartitionLayoutSource,
)
from treeforge.android.partition.layout_builder import (
    PartitionLayoutBuilder,
)
from treeforge.android.extraction.partition.lpdump_parser import (
    LpdumpMetadata,
)
from treeforge.android.partition.source import (
    PartitionSource,
)
from treeforge.android.extraction.partition.super_metadata_inspector import (
    SuperMetadataInspector,
)
from treeforge.android.extraction.partition.liblp_structure import (
    LiblpStructure,
    LiblpStructureDecoder,
)
from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
    ProviderArtifactKind,
)
from treeforge.android.providers.collection import (
    ProviderCollection,
)
from treeforge.core.context.context import (
    Context,
)


class PartitionLayoutDetectionError(
    RuntimeError,
):
    """
    Raised when canonical partition layout interpretation fails.
    """


class SuperMetadataInspectorLike(
    Protocol,
):
    """
    Inspector contract required by the partition layout detector.
    """

    def inspect(
        self,
        source: Path,
    ) -> LpdumpMetadata:
        ...


class LiblpStructureDecoderLike(
    Protocol,
):
    """
    Native liblp physical-structure decoder required for metadata-only
    topology sources.
    """

    def decode(
        self,
        source: Path,
    ) -> LiblpStructure:
        ...


class PartitionLayoutBuilderLike(
    Protocol,
):
    """
    Builder contract required by the partition layout detector.
    """

    def from_lpdump(
        self,
        metadata: LpdumpMetadata,
        super_image: Path,
        *,
        source: PartitionSource | None = None,
    ) -> PartitionLayout:
        ...

    def from_liblp_structure(
        self,
        structure: LiblpStructure,
        *,
        source: PartitionSource | None = None,
    ) -> PartitionLayout:
        ...

    def from_standalone_artifacts(
        self,
        artifacts: tuple[
            ProviderArtifact,
            ...,
        ],
    ) -> PartitionLayout:
        ...


class PartitionLayoutDetector:
    """
    Interpret canonical Discovery artifacts as an Android partition layout.

    This detector does not perform source Discovery.

    It consumes the canonical provider collection already produced and
    semantically enriched by Discovery.

    In particular, it does not:

    - scan workspace image directories;
    - rediscover files by extension;
    - classify arbitrary images as partitions;
    - mutate parallel device-model state;
    - inspect filesystems.

    Discovery classifications determine which artifacts are eligible to
    participate in the partition layout.

    Exact ProviderArtifact identity is preserved through PartitionSource so
    all upstream Discovery provenance survives partition interpretation.
    """

    PARTITION_CLASSIFICATIONS = frozenset(
        {
            ProviderArtifactClassification.BOOT,
            ProviderArtifactClassification.INIT_BOOT,
            ProviderArtifactClassification.VENDOR_BOOT,
            ProviderArtifactClassification.VENDOR_KERNEL_BOOT,
            ProviderArtifactClassification.RECOVERY,
            ProviderArtifactClassification.SYSTEM,
            ProviderArtifactClassification.SYSTEM_EXT,
            ProviderArtifactClassification.SYSTEM_OTHER,
            ProviderArtifactClassification.PRODUCT,
            ProviderArtifactClassification.VENDOR,
            ProviderArtifactClassification.ODM,
            ProviderArtifactClassification.USERDATA,
            ProviderArtifactClassification.VENDOR_DLKM,
            ProviderArtifactClassification.SYSTEM_DLKM,
            ProviderArtifactClassification.ODM_DLKM,
            ProviderArtifactClassification.VBMETA,
            ProviderArtifactClassification.VBMETA_SYSTEM,
            ProviderArtifactClassification.VBMETA_VENDOR,
            ProviderArtifactClassification.DTBO,
            ProviderArtifactClassification.PVMFW,
        }
    )

    def __init__(
        self,
        *,
        inspector: (
            SuperMetadataInspectorLike
            | None
        ) = None,
        builder: (
            PartitionLayoutBuilderLike
            | None
        ) = None,
        structure_decoder: (
            LiblpStructureDecoderLike
            | None
        ) = None,
    ) -> None:
        self._inspector = (
            inspector
            if inspector is not None
            else SuperMetadataInspector()
        )

        self._builder = (
            builder
            if builder is not None
            else PartitionLayoutBuilder()
        )

        self._structure_decoder = (
            structure_decoder
            if structure_decoder is not None
            else LiblpStructureDecoder()
        )

    def detect(
        self,
        context: Context,
    ) -> PartitionLayout:
        """
        Interpret the canonical Discovery artifact collection.

        A real super artifact is authoritative when Discovery contains one.

        When no populated super artifact exists, a Discovery-classified
        super_empty artifact remains canonical dynamic-partition topology
        evidence. Its metadata is interpreted structurally without implying
        that logical partition payloads are physically present.

        Standalone partition artifacts are preserved alongside dynamic
        topology rather than being discarded.
        """

        normalized_context = (
            self._validate_context(
                context
            )
        )

        collection = (
            self._require_provider_collection(
                normalized_context
            )
        )

        standalone_layout = (
            self._detect_standalone_layout(
                collection
            )
        )

        super_artifact = (
            self._find_super_artifact(
                collection
            )
        )

        if super_artifact is not None:
            dynamic_layout = (
                self._detect_super_layout(
                    context,
                    super_artifact,
                )
            )

            return self._compose_layouts(
                standalone_layout,
                dynamic_layout,
            )

        super_empty_artifact = (
            self._find_super_empty_artifact(
                collection
            )
        )

        if super_empty_artifact is not None:
            dynamic_layout = (
                self._detect_super_empty_layout(
                    context,
                    super_empty_artifact,
                )
            )

            return self._compose_layouts(
                standalone_layout,
                dynamic_layout,
            )

        return standalone_layout

    @staticmethod
    def _compose_layouts(
        standalone: PartitionLayout,
        dynamic: PartitionLayout,
    ) -> PartitionLayout:
        """
        Compose standalone partition evidence with dynamic topology.

        Exact duplicate partition names are rejected by PartitionLayout
        validation rather than silently preferring one source over another.
        """

        if not standalone.partitions:
            return dynamic

        if not dynamic.partitions:
            return standalone

        return PartitionLayout(
            source=PartitionLayoutSource.MIXED,
            partitions=(
                standalone.partitions
                + dynamic.partitions
            ),
            groups=dynamic.groups,
            block_devices=dynamic.block_devices,
        )

    def _detect_super_empty_layout(
        self,
        context: Context,
        artifact: ProviderArtifact,
    ) -> PartitionLayout:
        """
        Interpret a canonical metadata-only super_empty artifact.

        TreeForge's native liblp decoder is used because super_empty is a
        serialized metadata carrier rather than a populated raw super payload.
        """

        image = (
            self._require_accessible_image(
                context,
                artifact,
            )
        )

        try:
            structure = (
                self._structure_decoder.decode(
                    image
                )
            )
        except Exception as error:
            raise PartitionLayoutDetectionError(
                "Unable to decode canonical liblp topology from "
                f"{artifact.source_name}"
            ) from error

        if not structure.metadata_only_serialization:
            raise PartitionLayoutDetectionError(
                "Discovery-classified super_empty is not a "
                "metadata-only liblp serialization: "
                f"{artifact.source_name}"
            )

        source = PartitionSource(
            artifact=artifact
        )

        try:
            return (
                self._builder.from_liblp_structure(
                    structure,
                    source=source,
                )
            )
        except Exception as error:
            raise PartitionLayoutDetectionError(
                "Unable to build canonical metadata-only "
                "dynamic partition topology from "
                f"{artifact.source_name}"
            ) from error

    def _detect_super_layout(
        self,
        context: Context,
        artifact: ProviderArtifact,
    ) -> PartitionLayout:
        """
        Interpret one Discovery-classified super artifact.
        """

        image = (
            self._require_accessible_image(
                context,
                artifact,
            )
        )

        try:
            metadata = (
                self._inspector.inspect(
                    image
                )
            )
        except Exception as error:
            raise (
                PartitionLayoutDetectionError(
                    "Unable to inspect dynamic "
                    "partition metadata from "
                    f"{artifact.source_name}"
                )
            ) from error

        source = PartitionSource(
            artifact=artifact
        )

        try:
            return (
                self._builder.from_lpdump(
                    metadata,
                    image,
                    source=source,
                )
            )
        except Exception as error:
            raise (
                PartitionLayoutDetectionError(
                    "Unable to build dynamic "
                    "partition layout from "
                    f"{artifact.source_name}"
                )
            ) from error

    def _detect_standalone_layout(
        self,
        collection: ProviderCollection,
    ) -> PartitionLayout:
        """
        Build a layout from partition artifacts already known by Discovery.
        """

        artifacts = (
            self._standalone_partition_artifacts(
                collection
            )
        )

        try:
            return (
                self._builder
                .from_standalone_artifacts(
                    artifacts
                )
            )
        except Exception as error:
            raise (
                PartitionLayoutDetectionError(
                    "Unable to build standalone "
                    "partition layout from "
                    "Discovery artifacts"
                )
            ) from error

    @classmethod
    def _standalone_partition_artifacts(
        cls,
        collection: ProviderCollection,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Select artifacts whose canonical Discovery semantics identify them as
        standalone Android partitions.

        Materialization is deliberately not required here.

        PartitionLayout records partition structure and evidence available at the
        layout stage. Later stages may add accessibility or extraction information
        without changing the partition's established identity or provenance.
        """

        selected: list[
            ProviderArtifact
        ] = []

        for result in collection:
            for artifact in (
                result.artifact_inventory
            ):
                if (
                    artifact.kind
                    is not ProviderArtifactKind.IMAGE
                ):
                    continue

                if (
                    artifact.classification
                    not in cls.PARTITION_CLASSIFICATIONS
                ):
                    continue

                selected.append(
                    artifact
                )

        return tuple(
            sorted(
                selected,
                key=lambda artifact: (
                    artifact.classification.value,
                    artifact.source_name,
                ),
            )
        )

    @staticmethod
    def _find_super_artifact(
        collection: ProviderCollection,
    ) -> ProviderArtifact | None:
        """
        Return the unique Discovery artifact classified as real super.

        Materialization is not part of artifact existence.
        """

        matches: list[
            ProviderArtifact
        ] = []

        for result in collection:
            matches.extend(
                result
                .artifact_inventory
                .artifacts_of_classification(
                    ProviderArtifactClassification.SUPER
                )
            )

        if not matches:
            return None

        if len(
            matches
        ) > 1:
            raise PartitionLayoutDetectionError(
                "Multiple super artifacts were discovered"
            )

        return matches[0]

    @staticmethod
    def _find_super_empty_artifact(
        collection: ProviderCollection,
    ) -> ProviderArtifact | None:
        """
        Return the unique Discovery artifact classified as super_empty.

        super_empty is topology evidence, not proof of payload availability.
        """

        matches: list[
            ProviderArtifact
        ] = []

        for result in collection:
            matches.extend(
                result
                .artifact_inventory
                .artifacts_of_classification(
                    ProviderArtifactClassification.SUPER_EMPTY
                )
            )

        if not matches:
            return None

        if len(matches) > 1:
            raise PartitionLayoutDetectionError(
                "Multiple super_empty artifacts were discovered"
            )

        return matches[0]

    @staticmethod
    def _require_accessible_image(
        context: Context,
        artifact: ProviderArtifact,
    ) -> Path:
        """
        Return the canonical materialized form of one Discovery artifact.

        Partition Layout does not materialize provider artifacts itself.
        Physical accessibility must already have been established by
        Extraction for this exact ProviderArtifact identity.

        Only the source-level Extraction artifact is eligible. Derived
        descendants produced by later Extraction operations must never be
        substituted for the canonical source materialization.
        """

        extraction = (
            context.android_extraction
        )

        if extraction is None:
            raise PartitionLayoutDetectionError(
                "Dynamic super layout inspection requires "
                "Extraction source materialization before "
                "Partition Layout: "
                f"{artifact.source_name}"
            )

        candidates = tuple(
            candidate
            for candidate in extraction.artifacts_for_source(
                artifact
            )
            if candidate.parent is None
        )

        if not candidates:
            raise PartitionLayoutDetectionError(
                "No canonical materialized Extraction artifact "
                "exists for provider source: "
                f"{artifact.source_name}"
            )

        if len(candidates) != 1:
            raise PartitionLayoutDetectionError(
                "Canonical source materialization is ambiguous "
                "for provider source: "
                f"{artifact.source_name}"
            )

        canonical = (
            candidates[0]
        )

        if not canonical.path.is_file():
            raise PartitionLayoutDetectionError(
                "Canonical materialized provider artifact is "
                "not a regular file: "
                f"{canonical.path}"
            )

        return canonical.path

    @staticmethod
    def _require_provider_collection(
        context: Context,
    ) -> ProviderCollection:
        """
        Require the canonical Discovery provider collection.
        """

        collection = (
            context.provider_collection
        )

        if collection is None:
            raise (
                PartitionLayoutDetectionError(
                    "Canonical Discovery provider "
                    "collection is not available"
                )
            )

        if not isinstance(
            collection,
            ProviderCollection,
        ):
            raise TypeError(
                "context.provider_collection must "
                "be a ProviderCollection"
            )

        return collection

    @staticmethod
    def _validate_context(
        context: Context,
    ) -> Context:
        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be Context"
            )

        return context