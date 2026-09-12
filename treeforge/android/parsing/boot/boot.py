from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from treeforge.android.parsing.boot.common import (
    decode_android_os_version,
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
class ParsedBootImageMetadata:
    """
    Semantic metadata parsed from one Android boot image header.

    Physical container layout is intentionally excluded. Extraction owns
    component sizes, offsets, alignment, page layout, and materialization.
    """

    header_version: int
    os_version: int

    android_major: int
    android_minor: int
    android_patch: int

    boot_name: str
    cmdline: str

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "header_version",
            "os_version",
            "android_major",
            "android_minor",
            "android_patch",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
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


class BootImageParser:
    """
    Parse boot.img header semantics without re-decoding physical layout.

    Extraction is authoritative for physical component layout, offsets,
    alignment, payload materialization, and ramdisk processing.
    """

    BOOT_MAGIC = b"ANDROID!"

    BOOT_MAGIC_OFFSET = 0
    BOOT_MAGIC_SIZE = len(
        BOOT_MAGIC
    )

    HEADER_READ_SIZE = 4096

    HEADER_VERSION_OFFSET = 40

    LEGACY_OS_VERSION_OFFSET = 44

    LEGACY_BOOT_NAME_OFFSET = 48
    LEGACY_BOOT_NAME_SIZE = 16

    LEGACY_CMDLINE_OFFSET = 64
    LEGACY_CMDLINE_SIZE = 512

    MODERN_OS_VERSION_OFFSET = 16

    MODERN_CMDLINE_OFFSET = 44
    MODERN_CMDLINE_SIZE = 1536

    SUPPORTED_HEADER_VERSIONS = (
        0,
        1,
        2,
        3,
        4,
    )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> ParsedBootImageMetadata:
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
            description="Android boot image",
        )

        validate_image_magic(
            header,
            expected=self.BOOT_MAGIC,
            offset=self.BOOT_MAGIC_OFFSET,
            description="Android boot image",
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
                "Unsupported Android boot "
                "header version: "
                f"{header_version}"
            )

        if header_version >= 3:
            return self._parse_modern(
                header,
                header_version=(
                    header_version
                ),
            )

        return self._parse_legacy(
            header,
            header_version=(
                header_version
            ),
        )

    def _parse_legacy(
        self,
        header: bytes,
        *,
        header_version: int,
    ) -> ParsedBootImageMetadata:
        os_version = read_uint32_le(
            header,
            self.LEGACY_OS_VERSION_OFFSET,
        )

        (
            major,
            minor,
            patch,
        ) = decode_android_os_version(
            os_version
        )

        return ParsedBootImageMetadata(
            header_version=header_version,
            os_version=os_version,
            android_major=major,
            android_minor=minor,
            android_patch=patch,
            boot_name=read_c_string(
                header,
                self.LEGACY_BOOT_NAME_OFFSET,
                self.LEGACY_BOOT_NAME_SIZE,
                encoding="utf-8",
                errors="strict",
            ),
            cmdline=read_c_string(
                header,
                self.LEGACY_CMDLINE_OFFSET,
                self.LEGACY_CMDLINE_SIZE,
                encoding="utf-8",
                errors="strict",
            ),
        )

    def _parse_modern(
        self,
        header: bytes,
        *,
        header_version: int,
    ) -> ParsedBootImageMetadata:
        os_version = read_uint32_le(
            header,
            self.MODERN_OS_VERSION_OFFSET,
        )

        (
            major,
            minor,
            patch,
        ) = decode_android_os_version(
            os_version
        )

        return ParsedBootImageMetadata(
            header_version=header_version,
            os_version=os_version,
            android_major=major,
            android_minor=minor,
            android_patch=patch,
            boot_name="",
            cmdline=read_c_string(
                header,
                self.MODERN_CMDLINE_OFFSET,
                self.MODERN_CMDLINE_SIZE,
                encoding="utf-8",
                errors="strict",
            ),
        )






def read_android_boot_metadata(
    image_path: Path,
) -> ParsedBootImageMetadata:
    """
    Read semantic metadata from one Android boot image.
    """

    return BootImageParser().parse(
        image_path
    )
