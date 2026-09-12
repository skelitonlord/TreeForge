from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction.cpio.extractor import (
    CpioExtractionResult,
    CpioNewcEntry,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidRamdisk:
    """
    Canonical Parsing projection of one extracted Android boot-family ramdisk.

    Extraction remains authoritative for the physical CPIO archive and its
    exact ordered CpioNewcEntry population.

    Parsing carries that complete archive evidence across its canonical
    boundary together with the exact Extraction lineage needed by downstream
    consumers such as Boot Image.

    No first-stage-init, recovery, installer, reconstruction, or composition
    semantics are assigned here.
    """

    cpio: CpioExtractionResult

    boot_image_artifact: ExtractedArtifact
    ramdisk_component: ExtractedArtifact
    ramdisk_cpio: ExtractedArtifact
    ramdisk_root: ExtractedArtifact

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.cpio,
            CpioExtractionResult,
        ):
            raise TypeError(
                "cpio must be a CpioExtractionResult"
            )

        for name in (
            "boot_image_artifact",
            "ramdisk_component",
            "ramdisk_cpio",
            "ramdisk_root",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                ExtractedArtifact,
            ):
                raise TypeError(
                    f"{name} must be an ExtractedArtifact"
                )

        if self.cpio.artifact is not self.ramdisk_root:
            raise ValueError(
                "Parsed ramdisk must retain exact "
                "CpioExtractionResult artifact identity"
            )

        if (
            self.ramdisk_root.operation
            is not ExtractionOperation.CPIO_EXTRACTION
        ):
            raise ValueError(
                "ramdisk_root must be a canonical "
                "CPIO_EXTRACTION artifact"
            )

        if self.ramdisk_root.parent is not self.ramdisk_cpio:
            raise ValueError(
                "ramdisk_root must retain exact "
                "ramdisk_cpio parent identity"
            )

        if (
            self.ramdisk_cpio.operation
            is not ExtractionOperation.RAMDISK_DECOMPRESSION
        ):
            raise ValueError(
                "ramdisk_cpio must be a canonical "
                "RAMDISK_DECOMPRESSION artifact"
            )

        if self.ramdisk_cpio.parent is not self.ramdisk_component:
            raise ValueError(
                "ramdisk_cpio must retain exact "
                "ramdisk component parent identity"
            )

        if (
            self.ramdisk_component.operation
            is not ExtractionOperation.BOOT_COMPONENT_EXTRACTION
        ):
            raise ValueError(
                "ramdisk_component must be a canonical "
                "BOOT_COMPONENT_EXTRACTION artifact"
            )

        if self.ramdisk_component.parent is not self.boot_image_artifact:
            raise ValueError(
                "ramdisk component must retain exact "
                "boot-image parent identity"
            )

        if not isinstance(
            self.cpio.entries,
            tuple,
        ):
            raise TypeError(
                "CPIO entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                CpioNewcEntry,
            )
            for entry
            in self.cpio.entries
        ):
            raise TypeError(
                "CPIO entries must contain only CpioNewcEntry"
            )

    @property
    def entries(
        self,
    ) -> tuple[
        CpioNewcEntry,
        ...,
    ]:
        return self.cpio.entries

    @property
    def entry_count(
        self,
    ) -> int:
        return len(
            self.cpio.entries
        )

    @property
    def boot_image_name(
        self,
    ) -> str | None:
        return self.boot_image_artifact.semantic_name
