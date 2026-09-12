from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddedElfRange:
    """
    One structurally validated ELF object embedded inside a larger file.

    Offsets are relative to the physical parent artifact.

    ``size_bytes`` is the complete physically backed ELF extent established
    from intrinsic ELF structure:

    - ELF header;
    - program-header table;
    - section-header table;
    - every file-backed program segment;
    - every file-backed section.

    SHT_NOBITS sections contribute no physical bytes.
    """

    index: int
    offset_bytes: int
    size_bytes: int

    elf_class: int
    encoding: int
    elf_type: int
    machine: int
    elf_version: int

    entry_point: int

    program_header_offset: int
    program_header_entry_size: int
    program_header_count: int

    section_header_offset: int
    section_header_entry_size: int
    section_header_count: int

    def __post_init__(
        self,
    ) -> None:
        integer_fields = (
            "index",
            "offset_bytes",
            "size_bytes",
            "elf_class",
            "encoding",
            "elf_type",
            "machine",
            "elf_version",
            "entry_point",
            "program_header_offset",
            "program_header_entry_size",
            "program_header_count",
            "section_header_offset",
            "section_header_entry_size",
            "section_header_count",
        )

        for field_name in integer_fields:
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

        if self.size_bytes <= 0:
            raise ValueError(
                "size_bytes must be greater than zero"
            )

        if self.elf_class not in {
            1,
            2,
        }:
            raise ValueError(
                "elf_class must be ELFCLASS32 or ELFCLASS64"
            )

        if self.encoding not in {
            1,
            2,
        }:
            raise ValueError(
                "encoding must be little- or big-endian ELF data"
            )

    @property
    def end_offset_bytes(
        self,
    ) -> int:
        return (
            self.offset_bytes
            + self.size_bytes
        )


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddedElfStructure:
    """
    Complete deterministic set of structurally valid embedded ELF ranges in
    one physical parent file.
    """

    source: Path
    image_size: int
    ranges: tuple[
        EmbeddedElfRange,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if (
            isinstance(
                self.image_size,
                bool,
            )
            or not isinstance(
                self.image_size,
                int,
            )
        ):
            raise TypeError(
                "image_size must be an int"
            )

        if self.image_size < 0:
            raise ValueError(
                "image_size cannot be negative"
            )

        if not isinstance(
            self.ranges,
            tuple,
        ):
            raise TypeError(
                "ranges must be a tuple"
            )

        if not all(
            isinstance(
                value,
                EmbeddedElfRange,
            )
            for value in self.ranges
        ):
            raise TypeError(
                "ranges must contain only EmbeddedElfRange"
            )

        canonical = tuple(
            sorted(
                self.ranges,
                key=lambda value: (
                    value.offset_bytes,
                    value.index,
                ),
            )
        )

        if canonical != self.ranges:
            raise ValueError(
                "embedded ELF ranges must use canonical physical order"
            )

        for expected_index, value in enumerate(
            self.ranges
        ):
            if value.index != expected_index:
                raise ValueError(
                    "embedded ELF range indexes must be contiguous"
                )

            if value.end_offset_bytes > self.image_size:
                raise ValueError(
                    "embedded ELF range exceeds parent image size"
                )
