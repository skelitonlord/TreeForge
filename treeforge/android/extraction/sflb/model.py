from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(
    frozen=True,
    slots=True,
)
class SflbEntry:
    """
    One structurally decoded SFLB resource-table entry.
    """

    index: int
    record_offset: int
    name: str
    payload_size: int
    payload_offset: int
    opaque_word: int
    flags: int

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "index",
            "record_offset",
            "payload_size",
            "payload_offset",
            "opaque_word",
            "flags",
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
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name cannot be empty"
            )

        if self.payload_size <= 0:
            raise ValueError(
                "payload_size must be greater than zero"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class SflbContainer:
    """
    One structurally validated SFLB resource container embedded in a file.
    """

    index: int
    offset_bytes: int
    span_bytes: int
    version: int
    entry_count: int
    secondary_count: int

    raw_header_tail: tuple[
        int,
        int,
        int,
    ]

    entries: tuple[
        SflbEntry,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "index",
            "offset_bytes",
            "span_bytes",
            "version",
            "entry_count",
            "secondary_count",
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

        if self.span_bytes <= 0:
            raise ValueError(
                "span_bytes must be greater than zero"
            )

        if self.entry_count <= 0:
            raise ValueError(
                "entry_count must be greater than zero"
            )

        if not isinstance(
            self.raw_header_tail,
            tuple,
        ):
            raise TypeError(
                "raw_header_tail must be a tuple"
            )

        if len(
            self.raw_header_tail
        ) != 3:
            raise ValueError(
                "raw_header_tail must contain exactly three uint32 values"
            )

        for value in self.raw_header_tail:
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
                    "raw_header_tail must contain non-negative integers"
                )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                SflbEntry,
            )
            for entry in self.entries
        ):
            raise TypeError(
                "entries must contain only SflbEntry instances"
            )

        if len(
            self.entries
        ) != self.entry_count:
            raise ValueError(
                "entry_count must match entries"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class EmbeddedSflbStructure:
    """
    Structurally recognized SFLB containers inside one physical parent file.
    """

    source: Path
    image_size: int

    containers: tuple[
        SflbContainer,
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
            self.containers,
            tuple,
        ):
            raise TypeError(
                "containers must be a tuple"
            )

        if not all(
            isinstance(
                container,
                SflbContainer,
            )
            for container in self.containers
        ):
            raise TypeError(
                "containers must contain only SflbContainer instances"
            )
