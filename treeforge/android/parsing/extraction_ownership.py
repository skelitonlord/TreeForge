from __future__ import annotations

from enum import StrEnum

from treeforge.android.extraction import (
    ExtractionOperation,
)


class ParsingExtractionOwnership(
    StrEnum,
):
    """
    Explicit Parsing-stage disposition for every canonical Extraction
    operation.

    DIRECT
        Parsing directly consumes and conserves artifacts from this operation
        in a dedicated parsed/result family.

    FILESYSTEM_MEDIATED
        Parsing consumes the operation through the canonical filesystem
        metadata / parser-filesystem projection rather than as an independent
        direct family.

    LINEAGE_CARRIER
        The operation preserves physical derivation or ancestry required by
        a later canonical Parsing input, but is not itself a separate parsed
        semantic population.

    NOT_PARSING_INPUT
        The operation belongs wholly to Extraction mechanics and has no
        independent Parsing semantic contract.
    """

    DIRECT = "direct"
    FILESYSTEM_MEDIATED = "filesystem_mediated"
    LINEAGE_CARRIER = "lineage_carrier"
    NOT_PARSING_INPUT = "not_parsing_input"


PARSING_EXTRACTION_OWNERSHIP = {
    #
    # Direct Parsing-owned populations.
    #
    ExtractionOperation.BOOT_COMPONENT_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.AVB_REGION_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.KERNEL_DECOMPRESSION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.APEX_CONTAINER_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.DTBO_ENTRY_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.FDT_MEMBER_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.FBPK_ENTRY_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.BOOT_FIRMWARE_PAYLOAD_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.UFPK_DESCRIPTOR_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.SFLB_ENTRY_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.SFLB_RESOURCE_DECOMPRESSION:
        ParsingExtractionOwnership.DIRECT,

    ExtractionOperation.EMBEDDED_ELF_EXTRACTION:
        ParsingExtractionOwnership.DIRECT,

    #
    # Canonical filesystem roots. Filesystem Metadata owns the physical
    # inventory and Parsing consumes the exact resulting
    # AndroidParserFilesystemSource projection.
    #
    ExtractionOperation.FILESYSTEM_EXTRACTION:
        ParsingExtractionOwnership.FILESYSTEM_MEDIATED,

    ExtractionOperation.CPIO_EXTRACTION:
        ParsingExtractionOwnership.FILESYSTEM_MEDIATED,

    #
    # Physical / derivation lineage. These operations remain canonical
    # provenance but do not each create an independent Parsing population.
    #
    ExtractionOperation.SOURCE_ADOPTION:
        ParsingExtractionOwnership.LINEAGE_CARRIER,

    ExtractionOperation.ARCHIVE_MEMBER_EXTRACTION:
        ParsingExtractionOwnership.LINEAGE_CARRIER,

    ExtractionOperation.LOGICAL_PARTITION_EXTRACTION:
        ParsingExtractionOwnership.LINEAGE_CARRIER,

    ExtractionOperation.SPARSE_TO_RAW:
        ParsingExtractionOwnership.LINEAGE_CARRIER,

    ExtractionOperation.RAMDISK_DECOMPRESSION:
        ParsingExtractionOwnership.LINEAGE_CARRIER,

    ExtractionOperation.NESTED_ARTIFACT_DISCOVERY:
        ParsingExtractionOwnership.LINEAGE_CARRIER,

    #
    # Retained Extraction operation with no independent Parsing semantic
    # contract. Current canonical source materialization is represented by
    # SOURCE_ADOPTION or ARCHIVE_MEMBER_EXTRACTION.
    #
    ExtractionOperation.SOURCE_MATERIALIZATION:
        ParsingExtractionOwnership.NOT_PARSING_INPUT,
}


def validate_parsing_extraction_ownership() -> None:
    """
    Fail closed whenever Extraction adds or removes an operation without an
    explicit Parsing-stage ownership decision.
    """

    declared = set(
        PARSING_EXTRACTION_OWNERSHIP
    )

    canonical = set(
        ExtractionOperation
    )

    missing = (
        canonical
        - declared
    )

    extra = (
        declared
        - canonical
    )

    if missing or extra:
        raise RuntimeError(
            "Parsing Extraction-operation ownership is incomplete: "
            f"missing={sorted(value.value for value in missing)}, "
            f"extra={sorted(value.value for value in extra)}"
        )

    if len(
        PARSING_EXTRACTION_OWNERSHIP
    ) != len(
        ExtractionOperation
    ):
        raise RuntimeError(
            "Parsing Extraction-operation ownership must contain "
            "exactly one classification per ExtractionOperation"
        )


validate_parsing_extraction_ownership()
