from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from treeforge.android.parsing.boot.common import (
    read_image_header,
    validate_image_magic,
    validate_image_source,
)

from treeforge.core.binary import (
    read_c_string,
    read_uint32_le,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedVendorBootImageMetadata:
    """
    Semantic metadata parsed from one Android vendor_boot image header.

    Physical container structure is intentionally excluded. Extraction owns
    page/header layout, component sizes and offsets, vendor ramdisk-table
    placement, bootconfig placement, and payload materialization.
    """

    header_version: int

    boot_name: str
    cmdline: str

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.header_version,
                bool,
            )
            or not isinstance(
                self.header_version,
                int,
            )
        ):
            raise TypeError(
                "header_version must be an int"
            )

        if self.header_version < 0:
            raise ValueError(
                "header_version cannot be negative"
            )

        if not isinstance(
            self.boot_name,
            str,
        ):
            raise TypeError(
                "boot_name must be a string"
            )

        if not isinstance(
            self.cmdline,
            str,
        ):
            raise TypeError(
                "cmdline must be a string"
            )


class VendorBootImageParser:
    """
    Parse semantic metadata from Android vendor_boot.img headers.

    Extraction is authoritative for physical container structure, component
    sizes and offsets, page/header layout, vendor ramdisk-table placement,
    bootconfig placement, and payload materialization.

    This parser intentionally interprets only semantic header fields currently
    represented by TreeForge Parsing.
    """

    VENDOR_BOOT_MAGIC = b"VNDRBOOT"

    MAGIC_OFFSET = 0
    MAGIC_SIZE = len(
        VENDOR_BOOT_MAGIC
    )

    HEADER_READ_SIZE = 4096

    HEADER_VERSION_OFFSET = 8

    CMDLINE_OFFSET = 28
    CMDLINE_SIZE = 2048

    NAME_OFFSET = 2080
    NAME_SIZE = 16

    SUPPORTED_HEADER_VERSIONS = (
        3,
        4,
    )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> ParsedVendorBootImageMetadata:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        image_path = (
            validate_image_source(
                artifact.path
            )
        )

        header = read_image_header(
            image_path,
            size=self.HEADER_READ_SIZE,
            description="Android vendor_boot image",
        )

        validate_image_magic(
            header,
            expected=self.VENDOR_BOOT_MAGIC,
            offset=self.MAGIC_OFFSET,
            description="Android vendor_boot image",
        )

        header_version = (
            read_uint32_le(
                header,
                self.HEADER_VERSION_OFFSET,
            )
        )

        if (
            header_version
            not in self.SUPPORTED_HEADER_VERSIONS
        ):
            raise ValueError(
                "Unsupported Android vendor_boot "
                "header version: "
                f"{header_version}"
            )

        return ParsedVendorBootImageMetadata(
            header_version=header_version,
            boot_name=read_c_string(
                header,
                self.NAME_OFFSET,
                self.NAME_SIZE,
                encoding="ascii",
                errors="ignore",
            ),
            cmdline=read_c_string(
                header,
                self.CMDLINE_OFFSET,
                self.CMDLINE_SIZE,
                encoding="ascii",
                errors="ignore",
            ),
        )





def read_android_vendor_boot_metadata(
    image_path: Path,
) -> ParsedVendorBootImageMetadata:
    """
    Read semantic metadata from one Android vendor_boot image.
    """

    return VendorBootImageParser().parse(
        image_path
    )
