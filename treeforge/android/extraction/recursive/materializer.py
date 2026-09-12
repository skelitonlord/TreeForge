from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.elf import (
    EmbeddedElfDecoder,
    EmbeddedElfExtractor,
)
from typing import Protocol

from treeforge.android.extraction.apex.extractor import (
    ApexContainerExtractor,
)
from treeforge.android.extraction.avb import (
    AvbFooterStructureDecoder,
    AvbRegionExtractor,
    AvbVbmetaStructureDecoder,
)
from treeforge.android.extraction.boot.extractor import (
    BootImageExtractor,
)
from treeforge.android.extraction.boot.decoder import (
    BootImageStructureDecoder,
)
from treeforge.android.extraction.boot.metadata import (
    BootContainerKind,
)
from treeforge.android.extraction.cpio.extractor import (
    CpioExtractionResult,
    CpioExtractor,
)
from treeforge.android.extraction.dtbo.decoder import (
    DtboImageDecoder,
)
from treeforge.android.extraction.dtbo.extractor import (
    DtboEntryExtractor,
)
from treeforge.android.extraction.filesystem.extractor import (
    FilesystemExtractor,
)
from treeforge.android.extraction.filesystem.decoder import (
    Ext4FilesystemStructureDecoder,
)
from treeforge.android.extraction.partition.extractor import (
    LogicalPartitionExtractor,
)
from treeforge.android.extraction.partition.liblp_structure import (
    LiblpStructureDecoder,
)
from treeforge.android.extraction.partition.super_metadata_inspector import (
    SuperMetadataInspector,
)
from treeforge.android.extraction.partition.lpdump_parser import (
    LpdumpMetadata,
)
from treeforge.android.providers.artifact import (
    ProviderArtifactClassification,
)
from treeforge.android.extraction.fbpk.decoder import (
    FbpkContainerDecoder,
)
from treeforge.android.extraction.fbpk.extractor import (
    FbpkContainerExtractor,
)

from treeforge.android.extraction.sflb.decoder import (
    SflbContainerDecoder,
)
from treeforge.android.extraction.sflb.extractor import (
    SflbContainerExtractor,
)

from treeforge.android.extraction.sflb.decompressor import (
    SflbResourceDecompressor,
)
from treeforge.android.format.compression import (
    CompressionFormat,
    COMPRESSION_PREFIX_SIZE,
    detect_compression,
)

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.extraction.boot.ramdisk import (
    RamdiskDecompressor,
)
from treeforge.android.extraction.boot.kernel import (
    KernelDecompressor,
)
from treeforge.android.extraction.sparse.extractor import (
    SparseImageExtractor,
)
from treeforge.android.extraction.boot.vendor_boot_decoder import (
    VendorBootImageStructureDecoder,
)
from treeforge.android.format.image import (
    ImageFormat,
    ImageFormatDetector,
)
from treeforge.android.format.logical_partition import (
    LogicalPartitionContainerDetector,
)
from treeforge.android.format.filesystem import (
    FilesystemDetector,
    FilesystemType,
)


from treeforge.android.extraction.firmware_envelope import (
    FirmwareEnvelopeDecoder,
    FirmwareEnvelopeExtractor,
)


from treeforge.android.extraction.ufpk import (
    UfpkDecoder,
    UfpkExtractor,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ExtractionMaterializationOutcome:
    replacement_parent: (
        ExtractedArtifact
        | None
    ) = None

    artifacts: tuple[
        ExtractedArtifact,
        ...,
    ] = ()

    cpio_extractions: tuple[
        CpioExtractionResult,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            self.replacement_parent
            is not None
            and not isinstance(
                self.replacement_parent,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "replacement_parent must be an "
                "ExtractedArtifact or None"
            )

        if not isinstance(
            self.artifacts,
            tuple,
        ):
            raise TypeError(
                "artifacts must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ExtractedArtifact,
            )
            for item in self.artifacts
        ):
            raise TypeError(
                "artifacts must contain only ExtractedArtifact"
            )

        if not isinstance(
            self.cpio_extractions,
            tuple,
        ):
            raise TypeError(
                "cpio_extractions must be a tuple"
            )


class ExtractionArtifactMaterializer(
    Protocol,
):
    name: str
    operation: ExtractionOperation

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        ...

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        ...


def _fallback_identity(
    parent: ExtractedArtifact,
) -> str:
    digest = (
        sha256(
            parent.path.as_posix().encode(
                "utf-8"
            )
        )
        .hexdigest()[:16]
    )

    stem = (
        parent.path.stem
        or "artifact"
    )

    return (
        f"{digest}-{stem}"
    )


class SparseArtifactMaterializer:
    name = "sparse"
    operation = ExtractionOperation.SPARSE_TO_RAW

    def __init__(
        self,
        *,
        extractor: SparseImageExtractor,
        detector: ImageFormatDetector | None = None,
    ) -> None:
        self._extractor = extractor
        self._detector = (
            detector
            if detector is not None
            else ImageFormatDetector()
        )

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        """
        Return whether a physical file discovered inside a materialized
        directory is an Android sparse image worth promoting into canonical
        Extraction state.

        Candidate recognition is structural and independent of filename or
        extension.
        """

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            return False

        try:
            return (
                self._detector.detect(
                    path
                )
                is ImageFormat.ANDROID_SPARSE
            )
        except (
            FileNotFoundError,
            OSError,
            ValueError,
        ):
            return False

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is ExtractionOperation.SPARSE_TO_RAW
        ):
            return False

        return self.supports_discovered_path(
            parent.path
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        identity = (
            parent.semantic_name
            or _fallback_identity(
                parent
            )
        )

        artifact = (
            self._extractor.extract(
                parent,
                (
                    output_root
                    / "raw"
                    / f"{identity}.raw.img"
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )



class StandaloneAvbVbmetaMaterializer:
    """
    Enrich standalone AVB0 root artifacts with literal physical layout.

    This materializer does not create child artifacts. It only replaces the
    canonical parent with additive structural facts so descriptor/trust
    semantics remain downstream-owned.
    """

    name = "standalone_avb_vbmeta"
    operation = (
        ExtractionOperation
        .ARCHIVE_MEMBER_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: (
            AvbVbmetaStructureDecoder
            | None
        ) = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else AvbVbmetaStructureDecoder()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is ExtractionOperation
            .AVB_REGION_EXTRACTION
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    @staticmethod
    def _merge_facts(
        existing: tuple[
            ExtractionFact,
            ...,
        ],
        added: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        by_name = {
            fact.name: fact
            for fact in existing
        }

        for fact in added:
            current = by_name.get(
                fact.name
            )

            if current is not None:
                if current.value != fact.value:
                    raise ValueError(
                        "standalone AVB structural enrichment "
                        "conflicts with existing fact "
                        f"{fact.name!r}"
                    )

                continue

            by_name[
                fact.name
            ] = fact

        return tuple(
            by_name.values()
        )

    @staticmethod
    def _structure_facts(
        structure,
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        return (
            ExtractionFact(
                name="container_format",
                value="avb_vbmeta",
            ),
            ExtractionFact(
                name="avb_vbmeta_header_size_bytes",
                value=structure.header_size,
            ),
            ExtractionFact(
                name="avb_required_version_major",
                value=structure.required_version_major,
            ),
            ExtractionFact(
                name="avb_required_version_minor",
                value=structure.required_version_minor,
            ),
            ExtractionFact(
                name="avb_authentication_block_offset_bytes",
                value=structure.authentication_block_offset,
            ),
            ExtractionFact(
                name="avb_authentication_block_size_bytes",
                value=structure.authentication_block_size,
            ),
            ExtractionFact(
                name="avb_auxiliary_block_offset_bytes",
                value=structure.auxiliary_block_offset,
            ),
            ExtractionFact(
                name="avb_auxiliary_block_size_bytes",
                value=structure.auxiliary_block_size,
            ),
            ExtractionFact(
                name="avb_vbmeta_size_bytes",
                value=structure.vbmeta_size,
            ),
            ExtractionFact(
                name="avb_algorithm_type",
                value=structure.algorithm_type,
            ),
            ExtractionFact(
                name="avb_hash_offset_bytes",
                value=structure.hash_offset,
            ),
            ExtractionFact(
                name="avb_hash_size_bytes",
                value=structure.hash_size,
            ),
            ExtractionFact(
                name="avb_signature_offset_bytes",
                value=structure.signature_offset,
            ),
            ExtractionFact(
                name="avb_signature_size_bytes",
                value=structure.signature_size,
            ),
            ExtractionFact(
                name="avb_public_key_offset_bytes",
                value=structure.public_key_offset,
            ),
            ExtractionFact(
                name="avb_public_key_size_bytes",
                value=structure.public_key_size,
            ),
            ExtractionFact(
                name="avb_public_key_metadata_offset_bytes",
                value=structure.public_key_metadata_offset,
            ),
            ExtractionFact(
                name="avb_public_key_metadata_size_bytes",
                value=structure.public_key_metadata_size,
            ),
            ExtractionFact(
                name="avb_descriptors_offset_bytes",
                value=structure.descriptors_offset,
            ),
            ExtractionFact(
                name="avb_descriptors_size_bytes",
                value=structure.descriptors_size,
            ),
            ExtractionFact(
                name="avb_rollback_index",
                value=structure.rollback_index,
            ),
            ExtractionFact(
                name="avb_flags",
                value=structure.flags,
            ),
            ExtractionFact(
                name="avb_rollback_index_location",
                value=structure.rollback_index_location,
            ),
            ExtractionFact(
                name="avb_release_string",
                value=structure.release_string,
            ),
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        enriched_parent = replace(
            parent,
            facts=self._merge_facts(
                parent.facts,
                self._structure_facts(
                    structure
                ),
            ),
        )

        return ExtractionMaterializationOutcome(
            replacement_parent=enriched_parent,
            artifacts=(),
        )



class Ext4StructureMaterializer:
    """
    Enrich ext4-containing canonical files with literal superblock structure.

    No filesystem contents are materialized here. This must run before any
    materializer attaches children to the canonical parent.
    """

    name = "ext4_structure"
    operation = (
        ExtractionOperation
        .FILESYSTEM_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: (
            Ext4FilesystemStructureDecoder
            | None
        ) = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else Ext4FilesystemStructureDecoder()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    @staticmethod
    def _merge_facts(
        existing: tuple[
            ExtractionFact,
            ...,
        ],
        added: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        by_name = {
            fact.name: fact
            for fact in existing
        }

        for fact in added:
            current = by_name.get(
                fact.name
            )

            if current is not None:
                if current.value != fact.value:
                    raise ValueError(
                        "ext4 structural enrichment conflicts "
                        f"with existing fact {fact.name!r}"
                    )

                continue

            by_name[
                fact.name
            ] = fact

        return tuple(
            by_name.values()
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        facts = (
            ExtractionFact(
                name="filesystem_format",
                value="ext4",
            ),
            ExtractionFact(
                name="filesystem_superblock_offset_bytes",
                value=structure.superblock_offset,
            ),
            ExtractionFact(
                name="filesystem_superblock_size_bytes",
                value=structure.superblock_size,
            ),
            ExtractionFact(
                name="filesystem_block_size_bytes",
                value=structure.block_size,
            ),
            ExtractionFact(
                name="filesystem_block_count",
                value=structure.block_count,
            ),
            ExtractionFact(
                name="filesystem_size_bytes",
                value=structure.filesystem_size_bytes,
            ),
            ExtractionFact(
                name="filesystem_inode_count",
                value=structure.inode_count,
            ),
            ExtractionFact(
                name="filesystem_free_block_count",
                value=structure.free_block_count,
            ),
            ExtractionFact(
                name="filesystem_free_inode_count",
                value=structure.free_inode_count,
            ),
            ExtractionFact(
                name="filesystem_first_data_block",
                value=structure.first_data_block,
            ),
            ExtractionFact(
                name="filesystem_blocks_per_group",
                value=structure.blocks_per_group,
            ),
            ExtractionFact(
                name="filesystem_inodes_per_group",
                value=structure.inodes_per_group,
            ),
            ExtractionFact(
                name="filesystem_creator_os",
                value=structure.creator_os,
            ),
            ExtractionFact(
                name="filesystem_revision_level",
                value=structure.revision_level,
            ),
            ExtractionFact(
                name="filesystem_state",
                value=structure.state,
            ),
            ExtractionFact(
                name="filesystem_errors_behavior",
                value=structure.errors_behavior,
            ),
            ExtractionFact(
                name="filesystem_inode_size_bytes",
                value=structure.inode_size,
            ),
            ExtractionFact(
                name="filesystem_descriptor_size_bytes",
                value=structure.descriptor_size,
            ),
            ExtractionFact(
                name="filesystem_feature_compat",
                value=structure.feature_compat,
            ),
            ExtractionFact(
                name="filesystem_feature_incompat",
                value=structure.feature_incompat,
            ),
            ExtractionFact(
                name="filesystem_feature_ro_compat",
                value=structure.feature_ro_compat,
            ),
            ExtractionFact(
                name="filesystem_uuid",
                value=structure.uuid,
            ),
            ExtractionFact(
                name="filesystem_volume_name",
                value=structure.volume_name,
            ),
        )

        return ExtractionMaterializationOutcome(
            replacement_parent=replace(
                parent,
                facts=self._merge_facts(
                    parent.facts,
                    facts,
                ),
            ),
        )


class AvbArtifactMaterializer:
    """
    Materialize physical AVB footer-defined regions.

    AVB footer/container layout is Extraction-owned physical evidence.
    VBMeta semantic decoding remains Parsing-owned.
    """

    name = "avb"
    operation = (
        ExtractionOperation
        .AVB_REGION_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: (
            AvbFooterStructureDecoder
            | None
        ) = None,
        extractor: (
            AvbRegionExtractor
            | None
        ) = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else AvbFooterStructureDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else AvbRegionExtractor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        #
        # AVB_REGION_EXTRACTION children are already exact physical regions
        # materialized from an authoritative containing-image footer.
        #
        # They are not new candidate containing images for the same
        # materializer. In particular, the extracted 64-byte avb_footer
        # naturally begins with AVBf and would otherwise be mistaken for a
        # recursively nested AVB container.
        #
        if (
            parent.operation
            is ExtractionOperation
            .AVB_REGION_EXTRACTION
        ):
            return False

        return self._decoder.has_footer(
            parent.path
        )

    @staticmethod
    def _merge_facts(
        existing: tuple[
            ExtractionFact,
            ...,
        ],
        added: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        by_name = {
            fact.name: fact
            for fact in existing
        }

        for fact in added:
            current = by_name.get(
                fact.name
            )

            if current is not None:
                if current.value != fact.value:
                    raise ValueError(
                        "AVB structural enrichment conflicts with "
                        f"existing fact {fact.name!r}"
                    )

                continue

            by_name[
                fact.name
            ] = fact

        return tuple(
            by_name.values()
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        if structure is None:
            raise ValueError(
                "AVB materializer invoked for image without AVB footer"
            )

        semantic_identity = (
            parent.semantic_name
            or parent.path.stem
        )

        #
        # semantic_name is not physical identity. Many canonical artifacts
        # may legitimately share names such as "apex_payload".
        #
        # Derive a stable collision-safe directory from the exact canonical
        # parent path while retaining the semantic identity for readability.
        #
        physical_identity = (
            sha256(
                parent.path
                .as_posix()
                .encode("utf-8")
            )
            .hexdigest()[:16]
        )

        identity = (
            f"{physical_identity}-"
            f"{semantic_identity}"
        )

        hashtree_structures = (
            self._decoder
            .decode_hashtree_physical_structures(
                parent.path,
                structure,
            )
        )

        artifacts = (
            self._extractor.extract(
                parent,
                structure,
                (
                    output_root
                    / "avb"
                    / identity
                ),
                hashtree_structures=(
                    hashtree_structures
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )


class BootArtifactMaterializer:
    name = "boot"
    operation = (
        ExtractionOperation
        .BOOT_COMPONENT_EXTRACTION
    )

    _ANDROID_KINDS = {
        "boot": BootContainerKind.BOOT,
        "init_boot": BootContainerKind.INIT_BOOT,
        "recovery": BootContainerKind.RECOVERY,
        "pvmfw": BootContainerKind.PVMFW,
    }

    def __init__(
        self,
        *,
        extractor: BootImageExtractor | None = None,
        boot_decoder: BootImageStructureDecoder | None = None,
        vendor_boot_decoder: (
            VendorBootImageStructureDecoder
            | None
        ) = None,
    ) -> None:
        self._extractor = (
            extractor
            if extractor is not None
            else BootImageExtractor()
        )

        self._boot_decoder = (
            boot_decoder
            if boot_decoder is not None
            else BootImageStructureDecoder()
        )

        self._vendor_boot_decoder = (
            vendor_boot_decoder
            if vendor_boot_decoder is not None
            else VendorBootImageStructureDecoder()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        return (
            parent.kind
            is ExtractionArtifactKind.FILE
            and (
                parent.semantic_name
                in {
                    "boot",
                    "init_boot",
                    "recovery",
                    "vendor_boot",
                    "vendor_kernel_boot",
                    "pvmfw",
                }
            )
        )

    @staticmethod
    def _merge_facts(
        existing: tuple[
            ExtractionFact,
            ...,
        ],
        added: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        """
        Merge additive Extraction facts without permitting contradictions.
        """

        by_name = {
            fact.name: fact
            for fact in existing
        }

        for fact in added:
            current = by_name.get(
                fact.name
            )

            if current is not None:
                if current.value != fact.value:
                    raise ValueError(
                        "boot structural enrichment conflicts with "
                        f"existing fact {fact.name!r}"
                    )

                continue

            by_name[
                fact.name
            ] = fact

        return tuple(
            by_name.values()
        )

    @staticmethod
    def _boot_structure_facts(
        structure,
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        """
        Convert decoded ANDROID! container structure into canonical
        container-level Extraction facts.
        """

        facts: list[
            ExtractionFact
        ] = [
            ExtractionFact(
                name="container_format",
                value="android_boot",
            ),
            ExtractionFact(
                name="container_kind",
                value=structure.kind.value,
            ),
            ExtractionFact(
                name="header_version",
                value=structure.header_version,
            ),
            ExtractionFact(
                name="header_size_bytes",
                value=structure.header_size,
            ),
            ExtractionFact(
                name="page_size_bytes",
                value=structure.page_size,
            ),
            ExtractionFact(
                name="image_size_bytes",
                value=structure.image_size,
            ),
            ExtractionFact(
                name="os_version_raw",
                value=structure.os_version_raw,
            ),
            ExtractionFact(
                name="cmdline",
                value=structure.cmdline,
            ),
        ]

        #
        # Internal BootImageStructure layouts use zero-sized placeholders for
        # fields that do not exist in a particular boot-header version.
        #
        # Canonical Extraction facts must distinguish "field exists and is
        # empty" from "field is not part of this header format", so only emit
        # component facts for fields actually defined by that version.
        #
        if structure.header_version <= 2:
            applicable_components = [
                (
                    "kernel",
                    structure.kernel,
                ),
                (
                    "ramdisk",
                    structure.ramdisk,
                ),
                (
                    "second",
                    structure.second,
                ),
            ]

            if structure.header_version >= 1:
                applicable_components.append(
                    (
                        "recovery_dtbo",
                        structure.recovery_dtbo,
                    )
                )

            if structure.header_version >= 2:
                applicable_components.append(
                    (
                        "dtb",
                        structure.dtb,
                    )
                )

        else:
            applicable_components = [
                (
                    "kernel",
                    structure.kernel,
                ),
                (
                    "ramdisk",
                    structure.ramdisk,
                ),
            ]

            if structure.header_version == 4:
                applicable_components.append(
                    (
                        "boot_signature",
                        structure.boot_signature,
                    )
                )

        for (
            component_name,
            layout,
        ) in applicable_components:
            facts.extend(
                (
                    ExtractionFact(
                        name=(
                            f"{component_name}_present"
                        ),
                        value=layout.present,
                    ),
                    ExtractionFact(
                        name=(
                            f"{component_name}_offset_bytes"
                        ),
                        value=layout.offset,
                    ),
                    ExtractionFact(
                        name=(
                            f"{component_name}_size_bytes"
                        ),
                        value=layout.size,
                    ),
                )
            )

        if structure.header_version == 4:
            facts.extend(
                (
                    ExtractionFact(
                        name=(
                            "boot_signature_declared_size_bytes"
                        ),
                        value=(
                            structure
                            .boot_signature_declared_size
                        ),
                    ),
                    ExtractionFact(
                        name=(
                            "boot_signature_effective_size_bytes"
                        ),
                        value=(
                            structure
                            .boot_signature
                            .size
                        ),
                    ),
                )
            )

        #
        # Keep raw payload extent and page-aligned container extent distinct.
        #
        # The former is the exact end of the furthest physically present boot
        # component. The latter is the next boot-container page boundary.
        # Neither attempts to describe AVB or partition padding, which are
        # separate physical structures.
        #
        boot_payload_end = max(
            structure.header_size,
            *(
                layout.end
                for (
                    _component_name,
                    layout,
                ) in applicable_components
                if layout.present
            ),
        )

        boot_payload_aligned_end = (
            (
                boot_payload_end
                + structure.page_size
                - 1
            )
            // structure.page_size
            * structure.page_size
        )

        facts.extend(
            (
                ExtractionFact(
                    name="boot_payload_end_bytes",
                    value=boot_payload_end,
                ),
                ExtractionFact(
                    name=(
                        "boot_payload_aligned_end_bytes"
                    ),
                    value=boot_payload_aligned_end,
                ),
            )
        )

        return tuple(
            facts
        )

    @staticmethod
    def _vendor_boot_structure_facts(
        structure,
        *,
        container_kind: str,
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        facts: list[
            ExtractionFact
        ] = [
            ExtractionFact(
                name="container_format",
                value="android_vendor_boot",
            ),
            ExtractionFact(
                name="container_kind",
                value=container_kind,
            ),
            ExtractionFact(
                name="header_version",
                value=structure.header_version,
            ),
            ExtractionFact(
                name="header_size_bytes",
                value=structure.header_size,
            ),
            ExtractionFact(
                name="page_size_bytes",
                value=structure.page_size,
            ),
            ExtractionFact(
                name="image_size_bytes",
                value=structure.image_size,
            ),
            ExtractionFact(
                name="kernel_addr",
                value=structure.kernel_addr,
            ),
            ExtractionFact(
                name="ramdisk_addr",
                value=structure.ramdisk_addr,
            ),
            ExtractionFact(
                name="tags_addr",
                value=structure.tags_addr,
            ),
            ExtractionFact(
                name="dtb_addr",
                value=structure.dtb_addr,
            ),
            ExtractionFact(
                name="cmdline",
                value=structure.cmdline,
            ),
            ExtractionFact(
                name="name",
                value=structure.name,
            ),
        ]

        components = [
            (
                "vendor_ramdisk",
                structure.vendor_ramdisk,
            ),
            (
                "dtb",
                structure.dtb,
            ),
        ]

        if structure.header_version >= 4:
            components.extend(
                (
                    (
                        "vendor_ramdisk_table",
                        structure.vendor_ramdisk_table,
                    ),
                    (
                        "bootconfig",
                        structure.bootconfig,
                    ),
                )
            )

        for component_name, layout in components:
            facts.extend(
                (
                    ExtractionFact(
                        name=f"{component_name}_present",
                        value=layout.present,
                    ),
                    ExtractionFact(
                        name=f"{component_name}_offset_bytes",
                        value=layout.offset,
                    ),
                    ExtractionFact(
                        name=f"{component_name}_size_bytes",
                        value=layout.size,
                    ),
                )
            )

        if structure.header_version >= 4:
            facts.extend(
                (
                    ExtractionFact(
                        name="vendor_ramdisk_table_entry_count",
                        value=(
                            structure
                            .vendor_ramdisk_table_entry_num
                        ),
                    ),
                    ExtractionFact(
                        name="vendor_ramdisk_table_entry_size_bytes",
                        value=(
                            structure
                            .vendor_ramdisk_table_entry_size
                        ),
                    ),
                )
            )

            for entry in (
                structure
                .vendor_ramdisk_table_entries
            ):
                prefix = (
                    f"vendor_ramdisk_entry_{entry.index}"
                )

                facts.extend(
                    (
                        ExtractionFact(
                            name=f"{prefix}_size_bytes",
                            value=entry.ramdisk_size,
                        ),
                        ExtractionFact(
                            name=f"{prefix}_offset_bytes",
                            value=entry.ramdisk_offset,
                        ),
                        ExtractionFact(
                            name=f"{prefix}_type",
                            value=entry.ramdisk_type,
                        ),
                        ExtractionFact(
                            name=f"{prefix}_name",
                            value=entry.ramdisk_name,
                        ),
                    )
                )

                for board_index, value in enumerate(
                    entry.board_id
                ):
                    facts.append(
                        ExtractionFact(
                            name=(
                                f"{prefix}_board_id_"
                                f"{board_index}"
                            ),
                            value=value,
                        )
                    )

        return tuple(
            facts
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        semantic_name = (
            parent.semantic_name
        )

        if semantic_name in {
            "vendor_boot",
            "vendor_kernel_boot",
        }:
            structure = (
                self._vendor_boot_decoder.decode(
                    parent.path
                )
            )

            enriched_parent = replace(
                parent,
                facts=self._merge_facts(
                    parent.facts,
                    self._vendor_boot_structure_facts(
                        structure,
                        container_kind=semantic_name,
                    ),
                ),
            )

            artifacts = (
                self._extractor.extract_vendor_boot(
                    enriched_parent,
                    structure,
                    (
                        output_root
                        / "boot"
                        / semantic_name
                    ),
                    container_kind=semantic_name,
                )
            )

            return ExtractionMaterializationOutcome(
                replacement_parent=enriched_parent,
                artifacts=artifacts,
            )

        else:
            kind = self._ANDROID_KINDS[
                semantic_name
            ]

            structure = (
                self._boot_decoder.decode(
                    parent.path,
                    kind=kind,
                )
            )

            enriched_parent = replace(
                parent,
                facts=self._merge_facts(
                    parent.facts,
                    self._boot_structure_facts(
                        structure
                    ),
                ),
            )

            destination = (
                output_root
                / "boot"
                / kind.value
            )

            artifacts = (
                self._extractor.extract_android_boot(
                    enriched_parent,
                    structure,
                    destination,
                )
            )

            return ExtractionMaterializationOutcome(
                replacement_parent=enriched_parent,
                artifacts=artifacts,
            )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )


class RamdiskArtifactMaterializer:
    name = "ramdisk"
    operation = (
        ExtractionOperation
        .RAMDISK_DECOMPRESSION
    )

    def __init__(
        self,
        *,
        decompressor: RamdiskDecompressor | None = None,
    ) -> None:
        self._decompressor = (
            decompressor
            if decompressor is not None
            else RamdiskDecompressor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        return (
            parent.kind
            is ExtractionArtifactKind.FILE
            and parent.operation
            is ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
            and parent.semantic_name == "ramdisk"
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        boot_family = (
            parent.parent
        )

        if (
            boot_family is None
            or not boot_family.semantic_name
        ):
            raise ValueError(
                "ramdisk lineage has no boot-family identity"
            )

        artifact = (
            self._decompressor.decompress(
                parent,
                (
                    output_root
                    / "ramdisk"
                    / boot_family.semantic_name
                    / "ramdisk.cpio"
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )


class KernelArtifactMaterializer:
    name = "kernel"
    operation = (
        ExtractionOperation
        .KERNEL_DECOMPRESSION
    )

    def __init__(
        self,
        *,
        decompressor: KernelDecompressor | None = None,
    ) -> None:
        self._decompressor = (
            decompressor
            if decompressor is not None
            else KernelDecompressor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if not (
            parent.kind
            is ExtractionArtifactKind.FILE
            and parent.operation
            is ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
            and parent.semantic_name == "kernel"
        ):
            return False

        try:
            from treeforge.android.format.compression import (
                CompressionFormat,
                detect_compression,
            )

            prefix = parent.path.read_bytes()[:16]

            return (
                detect_compression(
                    prefix
                )
                is not CompressionFormat.NONE
            )

        except (
            FileNotFoundError,
            OSError,
        ):
            return False

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        boot_family = (
            parent.parent
        )

        if (
            boot_family is None
            or not boot_family.semantic_name
        ):
            raise ValueError(
                "kernel lineage has no boot-family identity"
            )

        artifact = (
            self._decompressor.decompress(
                parent,
                (
                    output_root
                    / "kernel"
                    / boot_family.semantic_name
                    / "kernel"
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )


class CpioArtifactMaterializer:
    name = "cpio"
    operation = ExtractionOperation.CPIO_EXTRACTION

    def __init__(
        self,
        *,
        extractor: CpioExtractor | None = None,
    ) -> None:
        self._extractor = (
            extractor
            if extractor is not None
            else CpioExtractor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        return (
            parent.kind
            is ExtractionArtifactKind.FILE
            and parent.operation
            is ExtractionOperation
            .RAMDISK_DECOMPRESSION
            and parent.semantic_name
            == "ramdisk_cpio"
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        ramdisk = parent.parent

        boot_family = (
            ramdisk.parent
            if ramdisk is not None
            else None
        )

        if (
            boot_family is None
            or not boot_family.semantic_name
        ):
            raise ValueError(
                "CPIO lineage has no boot-family identity"
            )

        extraction = (
            self._extractor.extract(
                parent,
                (
                    output_root
                    / "ramdisk"
                    / boot_family.semantic_name
                    / "root"
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                extraction.artifact,
            ),
            cpio_extractions=(
                extraction,
            ),
        )


class ApexArtifactMaterializer:
    name = "apex"
    operation = (
        ExtractionOperation
        .APEX_CONTAINER_EXTRACTION
    )

    def __init__(
        self,
        *,
        extractor: ApexContainerExtractor | None = None,
    ) -> None:
        self._extractor = (
            extractor
            if extractor is not None
            else ApexContainerExtractor()
        )

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            return False

        return (
            path.suffix.lower()
            in {
                ".apex",
                ".capex",
            }
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        return self._extractor.supports(
            parent
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        identity = (
            _fallback_identity(
                parent
            )
        )

        destination = (
            output_root
            / "apex"
            / identity
            / "container_member"
        )

        artifact = (
            self._extractor.extract(
                parent,
                destination,
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )



class ConcatenatedFdtArtifactMaterializer:
    """
    Materialize the ordered members of a file that consists entirely of
    multiple directly concatenated Flattened Device Tree blobs.

    Recognition is intrinsic and format-driven:

        * the source is a regular canonical Extraction artifact;
        * at least two FDTs are present;
        * each member begins exactly where the previous member ends;
        * every member has a structurally plausible standard FDT header;
        * the ordered member extents account for every byte in the source.

    Single FDT files are deliberately not materialized again.

    This stage establishes only physical member boundaries and provenance.
    FDT semantic decoding remains owned by Parsing.
    """

    name = "concatenated_fdt"

    operation = (
        ExtractionOperation
        .FDT_MEMBER_EXTRACTION
    )

    FDT_MAGIC = 0xD00DFEED
    HEADER_SIZE = 40

    @classmethod
    def _decode_extents(
        cls,
        path: Path,
    ) -> tuple[
        tuple[
            int,
            int,
        ],
        ...,
    ]:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            return ()

        data = path.read_bytes()

        if len(
            data
        ) < cls.HEADER_SIZE:
            return ()

        extents: list[
            tuple[
                int,
                int,
            ]
        ] = []

        cursor = 0

        while cursor < len(
            data
        ):
            if (
                cursor
                + cls.HEADER_SIZE
                > len(
                    data
                )
            ):
                return ()

            magic = int.from_bytes(
                data[
                    cursor:
                    cursor + 4
                ],
                "big",
            )

            if magic != cls.FDT_MAGIC:
                return ()

            totalsize = int.from_bytes(
                data[
                    cursor + 4:
                    cursor + 8
                ],
                "big",
            )

            off_dt_struct = int.from_bytes(
                data[
                    cursor + 8:
                    cursor + 12
                ],
                "big",
            )

            off_dt_strings = int.from_bytes(
                data[
                    cursor + 12:
                    cursor + 16
                ],
                "big",
            )

            off_mem_rsvmap = int.from_bytes(
                data[
                    cursor + 16:
                    cursor + 20
                ],
                "big",
            )

            version = int.from_bytes(
                data[
                    cursor + 20:
                    cursor + 24
                ],
                "big",
            )

            last_comp_version = (
                int.from_bytes(
                    data[
                        cursor + 24:
                        cursor + 28
                    ],
                    "big",
                )
            )

            size_dt_strings = int.from_bytes(
                data[
                    cursor + 32:
                    cursor + 36
                ],
                "big",
            )

            size_dt_struct = int.from_bytes(
                data[
                    cursor + 36:
                    cursor + 40
                ],
                "big",
            )

            if totalsize < cls.HEADER_SIZE:
                return ()

            end = (
                cursor
                + totalsize
            )

            if end > len(
                data
            ):
                return ()

            if last_comp_version > version:
                return ()

            for offset in (
                off_dt_struct,
                off_dt_strings,
                off_mem_rsvmap,
            ):
                if (
                    offset
                    < cls.HEADER_SIZE
                    or offset
                    >= totalsize
                ):
                    return ()

            if (
                off_dt_struct
                + size_dt_struct
                > totalsize
            ):
                return ()

            if (
                off_dt_strings
                + size_dt_strings
                > totalsize
            ):
                return ()

            extents.append(
                (
                    cursor,
                    totalsize,
                )
            )

            cursor = end

        if cursor != len(
            data
        ):
            return ()

        # A single FDT is already a canonical physical object and does not
        # need another Extraction layer.
        if len(
            extents
        ) < 2:
            return ()

        return tuple(
            extents
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is ExtractionOperation
            .FDT_MEMBER_EXTRACTION
        ):
            return False

        return bool(
            self._decode_extents(
                parent.path
            )
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        extents = (
            self._decode_extents(
                parent.path
            )
        )

        if not extents:
            raise ValueError(
                "concatenated FDT materializer received "
                "an unsupported artifact"
            )

        data = parent.path.read_bytes()

        identity = (
            _fallback_identity(
                parent
            )
        )

        destination_root = (
            output_root
            / "fdt"
            / identity
        )

        destination_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        artifacts: list[
            ExtractedArtifact
        ] = []

        member_count = len(
            extents
        )

        logical_size = sum(
            size
            for _offset, size
            in extents
        )

        if logical_size != len(
            data
        ):
            raise ValueError(
                "concatenated FDT member conservation failed"
            )

        for index, (
            offset,
            size,
        ) in enumerate(
            extents
        ):
            end = (
                offset
                + size
            )

            payload = data[
                offset:end
            ]

            if len(
                payload
            ) != size:
                raise ValueError(
                    "concatenated FDT member extent "
                    "was truncated"
                )

            destination = (
                destination_root
                / f"entry_{index:03d}.dtb"
            )

            destination.unlink(
                missing_ok=True
            )

            destination.write_bytes(
                payload
            )

            actual_size = (
                destination
                .stat()
                .st_size
            )

            if actual_size != size:
                destination.unlink(
                    missing_ok=True
                )

                raise ValueError(
                    "concatenated FDT member size mismatch: "
                    f"expected {size}, "
                    f"got {actual_size}"
                )

            artifacts.append(
                ExtractedArtifact(
                    source=parent.source,
                    path=destination,
                    kind=(
                        ExtractionArtifactKind.FILE
                    ),
                    operation=(
                        ExtractionOperation
                        .FDT_MEMBER_EXTRACTION
                    ),
                    semantic_name=(
                        f"fdt_{index:03d}"
                    ),
                    parent=parent,
                    facts=(
                        ExtractionFact(
                            name="member_index",
                            value=index,
                        ),
                        ExtractionFact(
                            name="member_offset_bytes",
                            value=offset,
                        ),
                        ExtractionFact(
                            name="member_size_bytes",
                            value=size,
                        ),
                        ExtractionFact(
                            name="member_count",
                            value=member_count,
                        ),
                        ExtractionFact(
                            name="container_size_bytes",
                            value=len(
                                data
                            ),
                        ),
                    ),
                    tool=ExtractionToolEvidence(
                        name=(
                            "treeforge-concatenated-fdt"
                        ),
                    ),
                    content_sha256=(
                        sha256(
                            payload
                        ).hexdigest()
                    ),
                    size_bytes=actual_size,
                )
            )

        if sum(
            artifact.size_bytes
            or 0
            for artifact
            in artifacts
        ) != len(
            data
        ):
            raise ValueError(
                "concatenated FDT artifact-byte "
                "conservation failed"
            )

        return ExtractionMaterializationOutcome(
            artifacts=tuple(
                artifacts
            ),
        )


class DtboArtifactMaterializer:
    """
    Materialize physical DT payload entries from any Android DT table
    container recognized by its structural magic and validated table.

    Recognition is independent of filename or provider classification.
    """

    name = "dtbo"
    operation = (
        ExtractionOperation
        .DTBO_ENTRY_EXTRACTION
    )

    def __init__(
        self,
        *,
        extractor: DtboEntryExtractor | None = None,
        decoder: DtboImageDecoder | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else DtboImageDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else DtboEntryExtractor(
                decoder=self._decoder,
            )
        )

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        return self._decoder.supports(
            path
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is ExtractionOperation
            .DTBO_ENTRY_EXTRACTION
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    @staticmethod
    def _merge_facts(
        existing: tuple[
            ExtractionFact,
            ...,
        ],
        added: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        """
        Merge additive Extraction facts without permitting contradictions.
        """

        by_name = {
            fact.name: fact
            for fact in existing
        }

        for fact in added:
            current = by_name.get(
                fact.name
            )

            if current is not None:
                if current.value != fact.value:
                    raise ValueError(
                        "Conflicting Extraction fact while enriching "
                        "DTBO parent: "
                        f"name={fact.name!r}, "
                        f"existing={current.value!r}, "
                        f"added={fact.value!r}"
                    )

                continue

            by_name[
                fact.name
            ] = fact

        return tuple(
            by_name.values()
        )

    @staticmethod
    def _structure_facts(
        structure,
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        header = structure.header

        entries_end = (
            header.dt_entries_offset
            + (
                header.dt_entry_count
                * header.dt_entry_size
            )
        )

        first_payload_offset = (
            min(
                entry.dt_offset
                for entry in structure.entries
            )
            if structure.entries
            else entries_end
        )

        last_payload_end = (
            max(
                (
                    entry.dt_offset
                    + entry.dt_size
                )
                for entry in structure.entries
            )
            if structure.entries
            else entries_end
        )

        facts: list[
            ExtractionFact
        ] = [
            ExtractionFact(
                name="container_format",
                value="android_dt_table",
            ),
            ExtractionFact(
                name="dtbo_magic",
                value=header.magic,
            ),
            ExtractionFact(
                name="dtbo_table_total_size_bytes",
                value=header.total_size,
            ),
            ExtractionFact(
                name="dtbo_header_size_bytes",
                value=header.header_size,
            ),
            ExtractionFact(
                name="dtbo_entry_size_bytes",
                value=header.dt_entry_size,
            ),
            ExtractionFact(
                name="dtbo_entry_count",
                value=header.dt_entry_count,
            ),
            ExtractionFact(
                name="dtbo_entries_offset_bytes",
                value=header.dt_entries_offset,
            ),
            ExtractionFact(
                name="dtbo_entries_end_bytes",
                value=entries_end,
            ),
            ExtractionFact(
                name="dtbo_page_size_bytes",
                value=header.page_size,
            ),
            ExtractionFact(
                name="dtbo_table_version",
                value=header.version,
            ),
            ExtractionFact(
                name="dtbo_first_payload_offset_bytes",
                value=first_payload_offset,
            ),
            ExtractionFact(
                name="dtbo_last_payload_end_bytes",
                value=last_payload_end,
            ),
        ]

        for entry in structure.entries:
            prefix = (
                f"dtbo_entry_{entry.index:03d}"
            )

            facts.extend(
                (
                    ExtractionFact(
                        name=f"{prefix}_offset_bytes",
                        value=entry.dt_offset,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_size_bytes",
                        value=entry.dt_size,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_id",
                        value=entry.id,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_rev",
                        value=entry.rev,
                    ),
                )
            )

            for custom_index, value in enumerate(
                entry.custom
            ):
                facts.append(
                    ExtractionFact(
                        name=(
                            f"{prefix}_custom_"
                            f"{custom_index}"
                        ),
                        value=value,
                    )
                )

        return tuple(
            facts
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        enriched_parent = replace(
            parent,
            facts=self._merge_facts(
                parent.facts,
                self._structure_facts(
                    structure
                ),
            ),
        )

        identity = (
            _fallback_identity(
                enriched_parent
            )
        )

        artifacts = (
            self._extractor.extract(
                enriched_parent,
                (
                    output_root
                    / "dtbo"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            replacement_parent=enriched_parent,
            artifacts=artifacts,
        )


class FbpkArtifactMaterializer:
    """
    Materialize payload entries from structurally recognized FBPK containers.

    Recognition depends only on physical FBPK structure. Provider semantic
    classifications, platform names, device names, and entry names do not
    control eligibility.
    """

    name = "fbpk"

    operation = (
        ExtractionOperation
        .FBPK_ENTRY_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: FbpkContainerDecoder | None = None,
        extractor: FbpkContainerExtractor | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else FbpkContainerDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else FbpkContainerExtractor()
        )

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        return self._decoder.supports(
            path
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        return (
            parent.kind
            is ExtractionArtifactKind.FILE
            and self._decoder.supports(
                parent.path
            )
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        identity = (
            parent.semantic_name
            or _fallback_identity(
                parent
            )
        )

        artifacts = (
            self._extractor.extract(
                parent,
                structure,
                (
                    output_root
                    / "fbpk"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )


class UfpkArtifactMaterializer:
    """
    Materialize physical descriptor-chain regions from structurally recognized
    UFPK containers.

    Eligibility is bounded to canonical FBPK payload entries, while UFPK
    recognition itself is based only on intrinsic physical structure.
    """

    name = "ufpk"

    operation = (
        ExtractionOperation
        .UFPK_DESCRIPTOR_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: UfpkDecoder | None = None,
        extractor: UfpkExtractor | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else UfpkDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else UfpkExtractor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is not ExtractionOperation
            .FBPK_ENTRY_EXTRACTION
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        identity = (
            parent.semantic_name
            or _fallback_identity(
                parent
            )
        )

        artifacts = (
            self._extractor.extract(
                parent,
                structure,
                (
                    output_root
                    / "ufpk"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )


class BootFirmwareEnvelopeMaterializer:
    """
    Materialize the verified payload of a structurally recognized firmware
    envelope.

    Eligibility is intentionally bounded to canonical FBPK entry children.
    Firmware identity names do not control recognition.
    """

    name = "boot_firmware_envelope"

    operation = (
        ExtractionOperation
        .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: FirmwareEnvelopeDecoder | None = None,
        extractor: FirmwareEnvelopeExtractor | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else FirmwareEnvelopeDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else FirmwareEnvelopeExtractor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is not ExtractionOperation
            .FBPK_ENTRY_EXTRACTION
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        identity = (
            _fallback_identity(
                parent
            )
        )

        artifact = (
            self._extractor.extract(
                parent,
                structure,
                (
                    output_root
                    / "firmware_payload"
                    / identity
                    / "payload.bin"
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )


class SflbArtifactMaterializer:
    """
    Materialize resources from structurally recognized embedded SFLB
    containers.
    """

    name = "sflb"

    operation = (
        ExtractionOperation
        .SFLB_ENTRY_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: SflbContainerDecoder | None = None,
        extractor: SflbContainerExtractor | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else SflbContainerDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else SflbContainerExtractor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is not ExtractionOperation
            .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        identity = (
            _fallback_identity(
                parent
            )
        )

        artifacts = (
            self._extractor.extract(
                parent,
                structure,
                (
                    output_root
                    / "sflb"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )


class SflbCompressedResourceMaterializer:
    """
    Decompress structurally compressed canonical SFLB resource children.

    Eligibility is intentionally bounded to SFLB_ENTRY_EXTRACTION lineage.
    Compression format is detected from intrinsic payload bytes rather than
    filename or resource-name conventions.
    """

    name = "sflb_compression"

    operation = (
        ExtractionOperation
        .SFLB_RESOURCE_DECOMPRESSION
    )

    def __init__(
        self,
        *,
        decompressor: SflbResourceDecompressor | None = None,
    ) -> None:
        self._decompressor = (
            decompressor
            if decompressor is not None
            else SflbResourceDecompressor()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is not ExtractionOperation
            .SFLB_ENTRY_EXTRACTION
        ):
            return False

        try:
            with parent.path.open(
                "rb"
            ) as stream:
                prefix = stream.read(
                    COMPRESSION_PREFIX_SIZE
                )

            return (
                detect_compression(
                    prefix
                )
                is not CompressionFormat.NONE
            )

        except (
            FileNotFoundError,
            OSError,
            ValueError,
        ):
            return False

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        identity = (
            _fallback_identity(
                parent
            )
        )

        destination_name = (
            parent.path.stem
            if parent.path.suffix
            else (
                parent.path.name
                + ".decompressed"
            )
        )

        artifact = (
            self._decompressor.decompress(
                parent,
                (
                    output_root
                    / "sflb_decompressed"
                    / identity
                    / destination_name
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )


class EmbeddedElfArtifactMaterializer:
    """
    Materialize structurally valid ELF objects embedded inside eligible
    canonical binary artifacts.

    The ELF decoder/extractor is container-agnostic.

    Current activation is intentionally evidence-bounded to canonical FBPK
    payload children. Additional parent-operation families should be enabled
    only after real artifacts prove that they contain independently
    materializable embedded ELF objects.
    """

    name = "embedded_elf"

    operation = (
        ExtractionOperation
        .EMBEDDED_ELF_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: EmbeddedElfDecoder | None = None,
        extractor: EmbeddedElfExtractor | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else EmbeddedElfDecoder()
        )

        self._extractor = (
            extractor
            if extractor is not None
            else EmbeddedElfExtractor()
        )

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        #
        # Directory-tree discovery is deliberately disabled for this first
        # capability. The current real evidence is for binary children
        # already present in canonical Extraction state.
        #
        # This avoids promoting arbitrary filesystem files merely because
        # they contain an incidental ELF byte sequence.
        #
        return False

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is not ExtractionOperation
            .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        if not structure.ranges:
            return ExtractionMaterializationOutcome()

        identity = (
            parent.semantic_name
            or _fallback_identity(
                parent
            )
        )

        artifacts = (
            self._extractor.extract(
                parent,
                structure,
                (
                    output_root
                    / "elf"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )



class LiblpStructureMaterializer:
    """
    Enrich Android liblp-containing artifacts with literal physical metadata.

    This materializer is structure-only. It never creates logical partition
    payload artifacts and never assigns global identity to partition names.

    Partition, extent, group, and block-device records remain scoped to the
    canonical parent artifact and therefore inherit its exact provenance and
    lineage.
    """

    name = "liblp_structure"
    operation = (
        ExtractionOperation
        .LOGICAL_PARTITION_EXTRACTION
    )

    def __init__(
        self,
        *,
        decoder: (
            LiblpStructureDecoder
            | None
        ) = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else LiblpStructureDecoder()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        return self._decoder.supports(
            parent.path
        )

    @staticmethod
    def _merge_facts(
        existing: tuple[
            ExtractionFact,
            ...,
        ],
        added: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        by_name = {
            fact.name: fact
            for fact in existing
        }

        for fact in added:
            current = by_name.get(
                fact.name
            )

            if current is not None:
                if current.value != fact.value:
                    raise ValueError(
                        "liblp structural enrichment "
                        "conflicts with existing fact "
                        f"{fact.name!r}"
                    )

                continue

            by_name[
                fact.name
            ] = fact

        return tuple(
            by_name.values()
        )

    @staticmethod
    def _structure_facts(
        structure,
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        facts = [
            ExtractionFact(
                name="logical_partition_format",
                value="liblp",
            ),
            ExtractionFact(
                name="liblp_image_size_bytes",
                value=structure.image_size_bytes,
            ),
            ExtractionFact(
                name="liblp_geometry_offset_bytes",
                value=structure.geometry_offset_bytes,
            ),
            ExtractionFact(
                name="liblp_geometry_struct_size_bytes",
                value=structure.geometry_struct_size_bytes,
            ),
            ExtractionFact(
                name="liblp_geometry_checksum",
                value=structure.geometry_checksum,
            ),
            ExtractionFact(
                name="liblp_geometry_checksum_valid",
                value=structure.geometry_checksum_valid,
            ),
            ExtractionFact(
                name="liblp_metadata_max_size_bytes",
                value=structure.metadata_max_size_bytes,
            ),
            ExtractionFact(
                name="liblp_metadata_slot_count",
                value=structure.metadata_slot_count,
            ),
            ExtractionFact(
                name="liblp_logical_block_size_bytes",
                value=structure.logical_block_size_bytes,
            ),
            ExtractionFact(
                name="liblp_metadata_header_offset_bytes",
                value=structure.metadata_header_offset_bytes,
            ),
            ExtractionFact(
                name="liblp_metadata_major_version",
                value=structure.metadata_major_version,
            ),
            ExtractionFact(
                name="liblp_metadata_minor_version",
                value=structure.metadata_minor_version,
            ),
            ExtractionFact(
                name="liblp_metadata_header_size_bytes",
                value=structure.metadata_header_size_bytes,
            ),
            ExtractionFact(
                name="liblp_metadata_tables_size_bytes",
                value=structure.metadata_tables_size_bytes,
            ),
            ExtractionFact(
                name="liblp_metadata_header_checksum",
                value=structure.metadata_header_checksum,
            ),
            ExtractionFact(
                name="liblp_metadata_header_checksum_valid",
                value=structure.metadata_header_checksum_valid,
            ),
            ExtractionFact(
                name="liblp_metadata_tables_checksum",
                value=structure.metadata_tables_checksum,
            ),
            ExtractionFact(
                name="liblp_metadata_tables_checksum_valid",
                value=structure.metadata_tables_checksum_valid,
            ),
            ExtractionFact(
                name="liblp_partition_table_offset_bytes",
                value=structure.partition_table_offset_bytes,
            ),
            ExtractionFact(
                name="liblp_partition_entry_size_bytes",
                value=structure.partition_entry_size_bytes,
            ),
            ExtractionFact(
                name="liblp_partition_count",
                value=len(structure.partitions),
            ),
            ExtractionFact(
                name="liblp_extent_table_offset_bytes",
                value=structure.extent_table_offset_bytes,
            ),
            ExtractionFact(
                name="liblp_extent_entry_size_bytes",
                value=structure.extent_entry_size_bytes,
            ),
            ExtractionFact(
                name="liblp_extent_count",
                value=len(structure.extents),
            ),
            ExtractionFact(
                name="liblp_group_table_offset_bytes",
                value=structure.group_table_offset_bytes,
            ),
            ExtractionFact(
                name="liblp_group_entry_size_bytes",
                value=structure.group_entry_size_bytes,
            ),
            ExtractionFact(
                name="liblp_group_count",
                value=len(structure.groups),
            ),
            ExtractionFact(
                name="liblp_block_device_table_offset_bytes",
                value=structure.block_device_table_offset_bytes,
            ),
            ExtractionFact(
                name="liblp_block_device_entry_size_bytes",
                value=structure.block_device_entry_size_bytes,
            ),
            ExtractionFact(
                name="liblp_block_device_count",
                value=len(structure.block_devices),
            ),
            ExtractionFact(
                name="liblp_serialized_end_bytes",
                value=structure.serialized_end_bytes,
            ),
            ExtractionFact(
                name="liblp_metadata_only_serialization",
                value=structure.metadata_only_serialization,
            ),
            ExtractionFact(
                name="liblp_exactly_serialized_image",
                value=structure.exactly_serialized_image,
            ),
        ]

        for index, partition in enumerate(
            structure.partitions
        ):
            prefix = (
                f"liblp_partition_{index}"
            )

            facts.extend(
                (
                    ExtractionFact(
                        name=f"{prefix}_name",
                        value=partition.name,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_attributes",
                        value=partition.attributes,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_first_extent_index",
                        value=partition.first_extent_index,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_num_extents",
                        value=partition.num_extents,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_group_index",
                        value=partition.group_index,
                    ),
                )
            )

        for index, extent in enumerate(
            structure.extents
        ):
            prefix = (
                f"liblp_extent_{index}"
            )

            facts.extend(
                (
                    ExtractionFact(
                        name=f"{prefix}_num_sectors",
                        value=extent.num_sectors,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_target_type",
                        value=extent.target_type,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_target_data",
                        value=extent.target_data,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_target_source",
                        value=extent.target_source,
                    ),
                )
            )

        for index, group in enumerate(
            structure.groups
        ):
            prefix = (
                f"liblp_group_{index}"
            )

            facts.extend(
                (
                    ExtractionFact(
                        name=f"{prefix}_name",
                        value=group.name,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_flags",
                        value=group.flags,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_maximum_size_bytes",
                        value=group.maximum_size_bytes,
                    ),
                )
            )

        for index, device in enumerate(
            structure.block_devices
        ):
            prefix = (
                f"liblp_block_device_{index}"
            )

            facts.extend(
                (
                    ExtractionFact(
                        name=f"{prefix}_first_logical_sector",
                        value=device.first_logical_sector,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_first_logical_byte",
                        value=device.first_logical_byte,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_alignment_bytes",
                        value=device.alignment_bytes,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_alignment_offset_bytes",
                        value=device.alignment_offset_bytes,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_size_bytes",
                        value=device.size_bytes,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_partition_name",
                        value=device.partition_name,
                    ),
                    ExtractionFact(
                        name=f"{prefix}_flags",
                        value=device.flags,
                    ),
                )
            )

        return tuple(
            facts
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        enriched_parent = replace(
            parent,
            facts=self._merge_facts(
                parent.facts,
                self._structure_facts(
                    structure
                ),
            ),
        )

        return ExtractionMaterializationOutcome(
            replacement_parent=enriched_parent,
            artifacts=(),
        )



class LogicalPartitionContainerMaterializer:
    """
    Materialize logical partition children from any physical Android
    logical-partition container discovered by Extraction.

    Container recognition is delegated to SuperMetadataInspector rather
    than semantic names, provider classifications, or device-specific
    identities.

    Successful metadata probes are cached by physical path so nested
    candidate discovery and subsequent canonical materialization share
    the same inspection result.
    """

    name = "logical_partition_container"
    operation = (
        ExtractionOperation
        .LOGICAL_PARTITION_EXTRACTION
    )

    def __init__(
        self,
        *,
        extractor: LogicalPartitionExtractor | None = None,
        inspector: SuperMetadataInspector | None = None,
    ) -> None:
        self._extractor = (
            extractor
            if extractor is not None
            else LogicalPartitionExtractor()
        )

        self._inspector = (
            inspector
            if inspector is not None
            else SuperMetadataInspector()
        )

        self._metadata_by_path: dict[
            Path,
            LpdumpMetadata,
        ] = {}

    def _inspect_path(
        self,
        path: Path,
    ) -> LpdumpMetadata | None:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            return None

        if not (
            LogicalPartitionContainerDetector
            .detect(
                path
            )
        ):
            return None

        cached = (
            self._metadata_by_path.get(
                path
            )
        )

        if cached is not None:
            return cached

        try:
            metadata = (
                self._inspector.inspect(
                    path
                )
            )
        except Exception:
            #
            # This is a physical-recognition probe. A file that lpdump
            # cannot interpret is simply not an LP container.
            #
            return None

        if not isinstance(
            metadata,
            LpdumpMetadata,
        ):
            return None

        if not metadata.partitions:
            return None

        self._metadata_by_path[
            path
        ] = metadata

        return metadata

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        return (
            self._inspect_path(
                path
            )
            is not None
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        if (
            parent.operation
            is ExtractionOperation
            .LOGICAL_PARTITION_EXTRACTION
        ):
            return False

        #
        # super_empty is a valid LP metadata carrier, so physical probing
        # with lpdump can legitimately recognize it and expose partition
        # definitions. It does not, however, contain the populated logical
        # partition payloads that lpunpack is intended to materialize.
        #
        # Discovery's explicit SUPER_EMPTY classification is therefore an
        # authoritative negative constraint on unpacking.
        #
        # Do not require SUPER positively here: physically discovered nested
        # LP containers may have no ProviderArtifact classification at all
        # and must remain eligible for generic recognition.
        #
        source = parent.source

        if (
            source is not None
            and source.classification
            is ProviderArtifactClassification.SUPER_EMPTY
        ):
            return False

        return (
            self._inspect_path(
                parent.path
            )
            is not None
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        metadata = (
            self._inspect_path(
                parent.path
            )
        )

        if metadata is None:
            raise ValueError(
                "artifact is not a recognized logical-partition "
                f"container: {parent.path}"
            )

        partition_names = tuple(
            partition.name
            for partition
            in metadata.partitions
        )

        if not partition_names:
            raise ValueError(
                "logical-partition container exposes no partitions: "
                f"{parent.path}"
            )

        identity = (
            _fallback_identity(
                parent
            )
        )

        artifacts = (
            self._extractor.extract(
                parent,
                partition_names,
                (
                    output_root
                    / "logical_partitions"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=artifacts,
        )


class FilesystemArtifactMaterializer:
    name = "filesystem"
    operation = (
        ExtractionOperation
        .FILESYSTEM_EXTRACTION
    )

    def __init__(
        self,
        *,
        extractor: FilesystemExtractor | None = None,
    ) -> None:
        self._extractor = (
            extractor
            if extractor is not None
            else FilesystemExtractor()
        )

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        """
        Return whether a physical file discovered inside a materialized
        directory contains a filesystem TreeForge can currently extract.

        Detection is structural and independent of filename or extension.
        """

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            return False

        try:
            detected = FilesystemDetector.detect(
                path
            )
        except (
            FileNotFoundError,
            OSError,
            ValueError,
        ):
            return False

        return (
            detected
            is FilesystemType.EXT4
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        return self._extractor.supports(
            parent
        )

    def materialize(
        self,
        parent: ExtractedArtifact,
        output_root: Path,
    ) -> ExtractionMaterializationOutcome:
        #
        # Filesystem destination identity is physical/materialization identity,
        # not semantic identity.
        #
        # Semantic names such as ``apex_payload`` are intentionally reused by
        # many distinct canonical artifacts and therefore cannot safely own a
        # filesystem output path by themselves.
        #
        # Always use a deterministic collision-resistant identity for the
        # destination path. The resulting filesystem artifact separately
        # preserves ``parent.semantic_name`` as its canonical semantic identity.
        #
        identity = _fallback_identity(
            parent
        )

        artifact = (
            self._extractor.extract(
                parent,
                (
                    output_root
                    / "filesystems"
                    / identity
                ),
            )
        )

        return ExtractionMaterializationOutcome(
            artifacts=(
                artifact,
            ),
        )
