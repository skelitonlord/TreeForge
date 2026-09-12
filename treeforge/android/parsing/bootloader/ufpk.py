from __future__ import annotations

from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.parsing.bootloader.model import (
    AndroidParsedUfpk,
    AndroidParsedUfpkDescriptor,
)


class AndroidUfpkParser:
    """
    Decode the proven outer header of a UFPK UFS firmware-update package.

    The firmware package internals remain opaque until their record semantics
    are independently established. Parsing therefore preserves the complete
    source bytes rather than inventing subordinate artifacts or meanings.
    """

    MAGIC = b"UFPK"

    #
    # The observed structural metadata ends before 0x1b0. Preserve this
    # region exactly as header evidence while retaining the remainder as the
    # uninterpreted package body.
    #
    HEADER_SIZE = 0x1B0

    @staticmethod
    def _u32(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 4
            ],
            "little",
        )

    @staticmethod
    def _text(
        data: bytes,
        offset: int,
        size: int,
    ) -> str:
        return (
            data[
                offset:
                offset + size
            ]
            .split(
                b"\0",
                1,
            )[0]
            .decode(
                "ascii",
                errors="replace",
            )
            .rstrip()
        )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedUfpk:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path

        data = source.read_bytes()

        if len(data) < self.HEADER_SIZE:
            raise ValueError(
                "UFPK source is smaller than "
                f"0x{self.HEADER_SIZE:x} bytes: "
                f"{source}"
            )

        if (
            data[:4]
            != self.MAGIC
        ):
            raise ValueError(
                f"invalid UFPK magic: {source}"
            )

        version = self._u32(
            data,
            4,
        )

        package_name = self._text(
            data,
            8,
            0x44,
        )

        header_value_0x4c = (
            self._u32(
                data,
                0x4C,
            )
        )

        declared_size = (
            self._u32(
                data,
                0x50,
            )
        )

        header_value_0x54 = (
            self._u32(
                data,
                0x54,
            )
        )

        device_identifier = (
            self._text(
                data,
                0x58,
                0x24,
            )
        )

        controller_identifier = (
            self._text(
                data,
                0x8C,
                0x10,
            )
        )

        firmware_identifier = (
            self._text(
                data,
                0xB4,
                0x10,
            )
        )

        return AndroidParsedUfpk(
            version=version,
            package_name=package_name,
            header_value_0x4c=(
                header_value_0x4c
            ),
            declared_size=declared_size,
            header_value_0x54=(
                header_value_0x54
            ),
            device_identifier=(
                device_identifier
            ),
            controller_identifier=(
                controller_identifier
            ),
            firmware_identifier=(
                firmware_identifier
            ),
            raw_header=data[
                :self.HEADER_SIZE
            ],
            raw_payload=data[
                self.HEADER_SIZE:
            ],
        )



class AndroidUfpkDescriptorParser:
    """
    Decode the proven fixed descriptor prefix from one canonical descriptor
    extent materialized by Extraction.

    Descriptor-chain discovery and physical extent calculation remain owned
    by Extraction. Parsing does not follow pointers or create children.
    """

    MINIMUM_HEADER_SIZE = 0x34

    @staticmethod
    def _u32(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 4
            ],
            "little",
        )

    @staticmethod
    def _identity(
        data: bytes,
    ) -> str:
        return (
            data[
                4:0x28
            ]
            .split(
                b"\0",
                1,
            )[0]
            .decode(
                "ascii",
                errors="replace",
            )
            .rstrip()
        )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedUfpkDescriptor:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            artifact.operation
            is not ExtractionOperation
            .UFPK_DESCRIPTOR_EXTRACTION
        ):
            raise ValueError(
                "UFPK descriptor Parsing requires a "
                "UFPK_DESCRIPTOR_EXTRACTION artifact"
            )

        data = artifact.path.read_bytes()

        if len(
            data
        ) < self.MINIMUM_HEADER_SIZE:
            raise ValueError(
                "UFPK descriptor extent is smaller than "
                "the proven descriptor prefix"
            )

        descriptor_kind = (
            self._u32(
                data,
                0x00,
            )
        )

        identity = (
            self._identity(
                data
            )
        )

        if not identity:
            raise ValueError(
                "UFPK descriptor identity is empty"
            )

        field_28 = (
            self._u32(
                data,
                0x28,
            )
        )

        next_offset = (
            self._u32(
                data,
                0x30,
            )
        )

        return AndroidParsedUfpkDescriptor(
            descriptor_kind=descriptor_kind,
            identity=identity,
            field_28=field_28,
            next_offset=next_offset,
            raw_header=data[
                :self.MINIMUM_HEADER_SIZE
            ],
        )
