from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.bmp import (
    AndroidParsedBmp,
)
from treeforge.android.universe.boot_firmware_lineage import (
    AndroidUniverseBootFirmwareLineageConclusion,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBmpRequirement:
    """
    Canonical device-level requirement promoted from one parsed BMP resource.

    Extraction remains authoritative for resource materialization and lineage.
    Parsing remains authoritative for intrinsic BMP structure.

    Universe preserves the exact AndroidParsedBmp and ExtractedArtifact
    identities while making the parsed resource available as canonical
    device-level evidence. Resource purpose or UI semantics are deliberately
    not inferred here.
    """

    source: AndroidParsedBmp

    boot_firmware_lineage: (
        AndroidUniverseBootFirmwareLineageConclusion
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidParsedBmp,
        ):
            raise TypeError(
                "source must be an AndroidParsedBmp"
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
                "canonical BMP artifact identity"
            )

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        return self.source.artifact

    @property
    def file_size(
        self,
    ) -> int:
        return self.source.file_size

    @property
    def pixel_data_offset(
        self,
    ) -> int:
        return self.source.pixel_data_offset

    @property
    def dib_header_size(
        self,
    ) -> int:
        return self.source.dib_header_size

    @property
    def width(
        self,
    ) -> int:
        return self.source.width

    @property
    def height(
        self,
    ) -> int:
        return self.source.height

    @property
    def planes(
        self,
    ) -> int:
        return self.source.planes

    @property
    def bits_per_pixel(
        self,
    ) -> int:
        return self.source.bits_per_pixel

    @property
    def compression(
        self,
    ) -> int:
        return self.source.compression

    @property
    def image_size(
        self,
    ) -> int:
        return self.source.image_size

    @property
    def horizontal_resolution(
        self,
    ) -> int:
        return self.source.horizontal_resolution

    @property
    def vertical_resolution(
        self,
    ) -> int:
        return self.source.vertical_resolution

    @property
    def colors_used(
        self,
    ) -> int:
        return self.source.colors_used

    @property
    def important_colors(
        self,
    ) -> int:
        return self.source.important_colors

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "bmp:"
            f"{self.source.artifact.path.as_posix()}"
        )
