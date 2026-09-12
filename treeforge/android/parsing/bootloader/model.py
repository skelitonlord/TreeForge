from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AndroidParsedUfsDescriptorKind(
    StrEnum,
):
    """
    Literal UFS descriptor-container identity observed in FBPK children.

    Parsing preserves the physical magic without assigning device-policy
    meaning to the structure.
    """

    UFSZ = "UFSZ"
    UFSP = "UFSP"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedFbptEntry:
    """
    One literal 136-byte FBPT partition-table record.

    Only structurally proven fields are decoded. Uninterpreted bytes remain
    available through ``reserved_prefix`` and ``reserved_tail``.
    """

    index: int

    size_bytes: int
    reserved_prefix: int

    name: str
    type_identifier: str
    instance_identifier: str

    reserved_tail: bytes
    raw_record: bytes


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedFbpt:
    """
    Literal FBPT partition-table structure.
    """


    version: int
    table_index: int
    reserved_header_value: int
    entry_count: int

    table_identifier: str

    entries: tuple[
        AndroidParsedFbptEntry,
        ...,
    ]

    raw_header: bytes


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedUfsDescriptor:
    """
    Literal UFSZ/UFSP FBPK child.

    The current factory evidence establishes the format family, magic,
    version-like scalar, fixed physical size, and exact bytes. Field semantics
    beyond those observations remain intentionally uninterpreted.
    """


    kind: AndroidParsedUfsDescriptorKind
    version: int

    raw_payload: bytes


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedUfpk:
    """
    Literal UFPK UFS firmware-update package header.

    Only fields directly established from the container bytes are named.
    Unknown structural state remains preserved in ``raw_header`` and
    ``raw_payload``.
    """


    version: int
    package_name: str

    header_value_0x4c: int
    declared_size: int
    header_value_0x54: int

    device_identifier: str
    controller_identifier: str
    firmware_identifier: str

    raw_header: bytes
    raw_payload: bytes


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedUfpkDescriptor:
    """
    Literal observations from one canonical UFPK descriptor extent.

    Extraction owns descriptor-chain discovery and exact physical extent
    materialization. Parsing decodes only the structurally established
    descriptor header fields from those exact bytes.
    """

    descriptor_kind: int
    identity: str

    field_28: int
    next_offset: int

    raw_header: bytes

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "descriptor_kind",
            "field_28",
            "next_offset",
        ):
            value = getattr(
                self,
                name,
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
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if (
            not isinstance(
                self.identity,
                str,
            )
            or not self.identity
        ):
            raise ValueError(
                "identity must be a non-empty string"
            )

        if not isinstance(
            self.raw_header,
            bytes,
        ):
            raise TypeError(
                "raw_header must be bytes"
            )

        if len(
            self.raw_header
        ) < 0x34:
            raise ValueError(
                "raw_header must contain at least 0x34 bytes"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedBootFirmwarePayload:
    """
    Literal observations from one canonical terminal boot-firmware payload.

    Extraction already owns firmware-envelope decoding, payload
    materialization, physical size/hash evidence, and lineage.

    Parsing records only observations made from the materialized payload
    itself. It does not assign boot policy, trust, execution role, or
    platform-specific meaning.
    """

    firmware_identity: str

    first_u32_le: int | None

    arm64_ret_count: int
    arm64_nop_count: int

    printable_ascii_string_count: int

    trailing_zero_bytes: int

    entropy_bits_per_byte: float

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.firmware_identity,
                str,
            )
            or not self.firmware_identity
        ):
            raise ValueError(
                "firmware_identity must be a non-empty string"
            )

        if (
            self.first_u32_le is not None
            and (
                isinstance(
                    self.first_u32_le,
                    bool,
                )
                or not isinstance(
                    self.first_u32_le,
                    int,
                )
                or not (
                    0
                    <= self.first_u32_le
                    <= 0xFFFFFFFF
                )
            )
        ):
            raise ValueError(
                "first_u32_le must be a uint32 or None"
            )

        for name in (
            "arm64_ret_count",
            "arm64_nop_count",
            "printable_ascii_string_count",
            "trailing_zero_bytes",
        ):
            value = getattr(
                self,
                name,
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
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.entropy_bits_per_byte,
            float,
        ):
            raise TypeError(
                "entropy_bits_per_byte must be a float"
            )

        if not (
            0.0
            <= self.entropy_bits_per_byte
            <= 8.0
        ):
            raise ValueError(
                "entropy_bits_per_byte must be between 0 and 8"
            )


AndroidParsedBootloaderChild = (
    AndroidParsedFbpt
    | AndroidParsedUfsDescriptor
    | AndroidParsedUfpk
    | AndroidParsedUfpkDescriptor
    | AndroidParsedBootFirmwarePayload
)
