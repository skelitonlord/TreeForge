from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.sflb import (
    AndroidParsedSflbEntry,
)
from treeforge.android.universe.boot_firmware_lineage import (
    AndroidUniverseBootFirmwareLineageConclusion,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSflbRequirement:
    """
    Canonical device-level requirement promoted from one parsed SFLB entry.

    Extraction remains authoritative for container discovery, structural
    boundaries, payload materialization, decompression decisions, hashing,
    and lineage.

    Parsing remains authoritative for literal SFLB entry structure.

    Universe preserves the exact AndroidParsedSflbEntry as canonical evidence
    and owns later device-level interpretation and reconciliation.
    """

    source: AndroidParsedSflbEntry

    boot_firmware_lineage: (
        AndroidUniverseBootFirmwareLineageConclusion
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidParsedSflbEntry,
        ):
            raise TypeError(
                "source must be an AndroidParsedSflbEntry"
            )

        if not isinstance(
            self.source.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "source.artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.boot_firmware_lineage,
            AndroidUniverseBootFirmwareLineageConclusion,
        ):
            raise TypeError(
                "boot_firmware_lineage must be an "
                "AndroidUniverseBootFirmwareLineageConclusion"
            )

        if (
            self.boot_firmware_lineage.artifact
            is not self.source.artifact
        ):
            raise ValueError(
                "boot_firmware_lineage must preserve the exact "
                "canonical SFLB artifact identity"
            )

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        return self.source.artifact

    @property
    def entry_name(
        self,
    ) -> str:
        return self.source.entry_name

    @property
    def container_index(
        self,
    ) -> int:
        return self.source.container_index

    @property
    def version(
        self,
    ) -> int:
        return self.source.version

    @property
    def entry_count(
        self,
    ) -> int:
        return self.source.entry_count

    @property
    def secondary_count(
        self,
    ) -> int:
        return self.source.secondary_count

    @property
    def entry_index(
        self,
    ) -> int:
        return self.source.entry_index

    @property
    def payload_size_bytes(
        self,
    ) -> int:
        return self.source.payload_size_bytes

    @property
    def opaque_word(
        self,
    ) -> int:
        return self.source.opaque_word

    @property
    def flags(
        self,
    ) -> int:
        return self.source.flags

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "sflb:"
            f"{self.source.artifact.path.as_posix()}:"
            f"{self.source.container_index}:"
            f"{self.source.entry_index}:"
            f"{self.source.entry_name}"
        )
