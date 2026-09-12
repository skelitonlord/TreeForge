from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidPartitionLayoutKnowledge:
    """
    Optional knowledge contributed to Partition Layout.

    Generic Partition Layout remains device- and Android-version-agnostic.
    Version, device, platform, or OEM modules may add explicitly modeled
    layout knowledge here when evidence requires it.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidExtractionKnowledge:
    """
    Optional knowledge contributed to Extraction/materialization.

    Extraction remains the canonical owner of physical source-to-artifact
    transformations. Modules may contribute only explicit extraction knowledge;
    they do not bypass Extraction provenance or lineage.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFilesystemMetadataKnowledge:
    """
    Optional knowledge contributed to Filesystem Metadata interpretation.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsingKnowledge:
    """
    Optional knowledge contributed to Parsing.

    Parsing remains responsible only for intrinsic source-format decoding.
    Module knowledge added here must therefore be parser/format knowledge,
    not cross-source interpretation or device-level conclusions.
    """
