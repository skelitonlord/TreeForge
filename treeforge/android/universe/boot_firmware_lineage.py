from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionOperation,
)


class AndroidUniverseBootFirmwareLineageStatus(
    StrEnum,
):
    """
    Canonical Universe interpretation of artifact relationship to a
    boot-firmware payload.

    BOOT_FIRMWARE_DESCENDANT means the family-specific canonical lineage has
    been established exactly.

    UNRESOLVED means canonical evidence does not establish that lineage.
    """

    BOOT_FIRMWARE_DESCENDANT = (
        "boot_firmware_descendant"
    )

    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootFirmwareLineageConclusion:
    """
    Universe-owned semantic conclusion for one canonical artifact.

    ``artifact`` preserves the exact leaf artifact by identity.

    ``lineage`` preserves the exact canonical evidence chain used by the
    family-specific resolver, ordered leaf -> ancestors.

    No filenames, device names, product names, firmware identities, or
    Android-version rules participate in the classification.
    """

    artifact: ExtractedArtifact

    status: (
        AndroidUniverseBootFirmwareLineageStatus
    )

    lineage: tuple[
        ExtractedArtifact,
        ...,
    ]

    reason: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.status,
            AndroidUniverseBootFirmwareLineageStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseBootFirmwareLineageStatus"
            )

        if not isinstance(
            self.lineage,
            tuple,
        ):
            raise TypeError(
                "lineage must be a tuple"
            )

        if (
            not self.lineage
            or self.lineage[0]
            is not self.artifact
        ):
            raise ValueError(
                "lineage must begin with the exact "
                "canonical artifact"
            )

        if not all(
            isinstance(
                artifact,
                ExtractedArtifact,
            )
            for artifact
            in self.lineage
        ):
            raise TypeError(
                "lineage must contain only "
                "ExtractedArtifact instances"
            )

        if (
            not isinstance(
                self.reason,
                str,
            )
            or not self.reason
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )

        if (
            self.status
            is AndroidUniverseBootFirmwareLineageStatus
            .BOOT_FIRMWARE_DESCENDANT
            and self.lineage[-1].operation
            is not ExtractionOperation
            .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
        ):
            raise ValueError(
                "boot-firmware-descendant conclusion must "
                "terminate at the canonical boot-firmware "
                "payload artifact"
            )


class AndroidUniverseBootFirmwareLineageResolver:
    """
    Interpret canonical artifact lineage for boot-firmware-owned resources.

    Family-specific chain shapes remain explicit so this migration preserves
    the exact semantics previously implemented by Reconstruction Planning.
    """

    @staticmethod
    def resolve_sflb_entry(
        artifact: ExtractedArtifact,
    ) -> AndroidUniverseBootFirmwareLineageConclusion:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        parent = artifact.parent

        if (
            parent is not None
            and parent.operation
            is ExtractionOperation
            .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
        ):
            return (
                AndroidUniverseBootFirmwareLineageConclusion(
                    artifact=artifact,
                    status=(
                        AndroidUniverseBootFirmwareLineageStatus
                        .BOOT_FIRMWARE_DESCENDANT
                    ),
                    lineage=(
                        artifact,
                        parent,
                    ),
                    reason=(
                        "Canonical artifact lineage establishes "
                        "this SFLB entry as a direct child of a "
                        "boot-firmware payload."
                    ),
                )
            )

        lineage = (
            (
                artifact,
                parent,
            )
            if parent is not None
            else (
                artifact,
            )
        )

        return (
            AndroidUniverseBootFirmwareLineageConclusion(
                artifact=artifact,
                status=(
                    AndroidUniverseBootFirmwareLineageStatus
                    .UNRESOLVED
                ),
                lineage=lineage,
                reason=(
                    "Canonical artifact lineage does not "
                    "establish this SFLB entry as a direct "
                    "child of a boot-firmware payload."
                ),
            )
        )

    @staticmethod
    def resolve_sflb_bmp(
        artifact: ExtractedArtifact,
    ) -> AndroidUniverseBootFirmwareLineageConclusion:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        sflb_entry = artifact.parent

        firmware_payload = (
            sflb_entry.parent
            if sflb_entry is not None
            else None
        )

        if (
            artifact.operation
            is ExtractionOperation
            .SFLB_RESOURCE_DECOMPRESSION
            and sflb_entry is not None
            and sflb_entry.operation
            is ExtractionOperation
            .SFLB_ENTRY_EXTRACTION
            and firmware_payload is not None
            and firmware_payload.operation
            is ExtractionOperation
            .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
        ):
            return (
                AndroidUniverseBootFirmwareLineageConclusion(
                    artifact=artifact,
                    status=(
                        AndroidUniverseBootFirmwareLineageStatus
                        .BOOT_FIRMWARE_DESCENDANT
                    ),
                    lineage=(
                        artifact,
                        sflb_entry,
                        firmware_payload,
                    ),
                    reason=(
                        "Canonical artifact lineage establishes "
                        "this BMP as a decompressed SFLB resource "
                        "descended from a boot-firmware payload."
                    ),
                )
            )

        lineage_items = [
            artifact,
        ]

        if sflb_entry is not None:
            lineage_items.append(
                sflb_entry
            )

        if firmware_payload is not None:
            lineage_items.append(
                firmware_payload
            )

        return (
            AndroidUniverseBootFirmwareLineageConclusion(
                artifact=artifact,
                status=(
                    AndroidUniverseBootFirmwareLineageStatus
                    .UNRESOLVED
                ),
                lineage=tuple(
                    lineage_items
                ),
                reason=(
                    "Canonical artifact lineage does not "
                    "establish this BMP as a decompressed "
                    "SFLB resource descended from a "
                    "boot-firmware payload."
                ),
            )
        )
