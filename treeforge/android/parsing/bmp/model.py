from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedBmp:
    """
    Literal BMP metadata decoded from one canonical Extraction artifact.

    Parsing records only structure physically encoded in the BMP. Resource
    purpose, UI role, and device-level interpretation belong to later stages.
    """

    artifact: ExtractedArtifact

    file_size: int
    pixel_data_offset: int
    dib_header_size: int

    width: int
    height: int
    planes: int
    bits_per_pixel: int
    compression: int
    image_size: int

    horizontal_resolution: int
    vertical_resolution: int
    colors_used: int
    important_colors: int

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

        non_negative = (
            "file_size",
            "pixel_data_offset",
            "dib_header_size",
            "planes",
            "bits_per_pixel",
            "compression",
            "image_size",
            "colors_used",
            "important_colors",
        )

        for name in non_negative:
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        for name in (
            "width",
            "height",
            "horizontal_resolution",
            "vertical_resolution",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an integer"
                )

        if self.file_size < 14:
            raise ValueError(
                "file_size is too small for a BMP file header"
            )

        if self.dib_header_size < 40:
            raise ValueError(
                "only BMP DIB headers of at least 40 bytes are supported"
            )

        if self.planes != 1:
            raise ValueError(
                "BMP planes must equal 1"
            )
