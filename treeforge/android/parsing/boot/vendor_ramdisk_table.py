from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionOperation,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedVendorRamdiskTableEntry:
    """
    Literal semantic decode of one canonical vendor_boot v4
    vendor-ramdisk-table entry.

    ``raw`` preserves the complete physical entry so Parsing never silently
    discards bytes if a future format extends the currently known fields.
    """

    index: int
    ramdisk_size: int
    ramdisk_offset: int
    ramdisk_type: int
    ramdisk_name: str
    board_id: tuple[
        int,
        ...,
    ]
    raw: bytes

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "index",
                self.index,
            ),
            (
                "ramdisk_size",
                self.ramdisk_size,
            ),
            (
                "ramdisk_offset",
                self.ramdisk_offset,
            ),
            (
                "ramdisk_type",
                self.ramdisk_type,
            ),
        ):
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
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if not isinstance(
            self.ramdisk_name,
            str,
        ):
            raise TypeError(
                "ramdisk_name must be a string"
            )

        if not isinstance(
            self.board_id,
            tuple,
        ):
            raise TypeError(
                "board_id must be a tuple"
            )

        if len(
            self.board_id
        ) != 16:
            raise ValueError(
                "board_id must contain exactly 16 words"
            )

        for value in self.board_id:
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
                    "board_id values must be ints"
                )

            if value < 0:
                raise ValueError(
                    "board_id values cannot be negative"
                )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        if len(
            self.raw
        ) < 108:
            raise ValueError(
                "vendor ramdisk-table entry must preserve "
                "at least the 108-byte v4 structure"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedVendorRamdiskTable:
    """
    Canonical Parsing interpretation of one exact
    vendor_ramdisk_table boot component.

    Extraction owns its physical location and materialization. Parsing owns
    the literal structured entry semantics carried by the table.
    """

    artifact: ExtractedArtifact
    boot_image_artifact: ExtractedArtifact
    entry_size: int
    entries: tuple[
        ParsedVendorRamdiskTableEntry,
        ...,
    ]

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
            self.boot_image_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "boot_image_artifact must be an ExtractedArtifact"
            )

        if (
            self.artifact.operation
            is not ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
        ):
            raise ValueError(
                "vendor ramdisk table must originate from "
                "BOOT_COMPONENT_EXTRACTION"
            )

        if (
            self.artifact.semantic_name
            != "vendor_ramdisk_table"
        ):
            raise ValueError(
                "vendor ramdisk table artifact must retain "
                "semantic_name='vendor_ramdisk_table'"
            )

        if (
            self.artifact.parent
            is not self.boot_image_artifact
        ):
            raise ValueError(
                "vendor ramdisk table must preserve exact "
                "boot-image parent identity"
            )

        if (
            isinstance(
                self.entry_size,
                bool,
            )
            or not isinstance(
                self.entry_size,
                int,
            )
        ):
            raise TypeError(
                "entry_size must be an int"
            )

        if self.entry_size < 108:
            raise ValueError(
                "entry_size must be at least 108 bytes"
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
                ParsedVendorRamdiskTableEntry,
            )
            for entry
            in self.entries
        ):
            raise TypeError(
                "entries must contain only "
                "ParsedVendorRamdiskTableEntry values"
            )

        expected_indices = tuple(
            range(
                len(
                    self.entries
                )
            )
        )

        actual_indices = tuple(
            entry.index
            for entry
            in self.entries
        )

        if (
            actual_indices
            != expected_indices
        ):
            raise ValueError(
                "vendor ramdisk table entries must preserve "
                "canonical source order"
            )

        for entry in self.entries:
            if len(
                entry.raw
            ) != self.entry_size:
                raise ValueError(
                    "vendor ramdisk table entry raw size "
                    "must equal declared entry_size"
                )

        expected_size = (
            self.entry_size
            * len(
                self.entries
            )
        )

        if (
            self.artifact.size_bytes
            is not None
            and self.artifact.size_bytes
            != expected_size
        ):
            raise ValueError(
                "vendor ramdisk table byte conservation failed"
            )


class AndroidVendorRamdiskTableParser:
    """
    Decode one exact vendor_ramdisk_table component.

    Android vendor_boot v4 defines a 108-byte known entry prefix:

        uint32 ramdisk_size
        uint32 ramdisk_offset
        uint32 ramdisk_type
        char   ramdisk_name[32]
        uint32 board_id[16]

    The complete physical entry remains preserved in ``raw``.
    """

    KNOWN_ENTRY_SIZE = 108

    @staticmethod
    def _fact(
        artifact: ExtractedArtifact,
        name: str,
    ) -> str | int | bool | None:
        matches = tuple(
            fact.value
            for fact
            in artifact.facts
            if fact.name == name
        )

        if len(
            matches
        ) > 1:
            raise ValueError(
                "canonical Extraction artifact contains "
                f"duplicate {name!r} facts"
            )

        return (
            matches[0]
            if matches
            else None
        )

    @classmethod
    def parse(
        cls,
        artifact: ExtractedArtifact,
        boot_image_artifact: ExtractedArtifact,
    ) -> ParsedVendorRamdiskTable:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            boot_image_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "boot_image_artifact must be an ExtractedArtifact"
            )

        if (
            artifact.operation
            is not ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
            or artifact.semantic_name
            != "vendor_ramdisk_table"
        ):
            raise ValueError(
                "parser requires a canonical "
                "vendor_ramdisk_table boot component"
            )

        if (
            artifact.parent
            is not boot_image_artifact
        ):
            raise ValueError(
                "vendor ramdisk-table parent identity mismatch"
            )

        entry_count = cls._fact(
            artifact,
            "table_entry_count",
        )

        entry_size = cls._fact(
            artifact,
            "table_entry_size_bytes",
        )

        for name, value in (
            (
                "table_entry_count",
                entry_count,
            ),
            (
                "table_entry_size_bytes",
                entry_size,
            ),
        ):
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
                raise ValueError(
                    "canonical vendor ramdisk-table component "
                    f"is missing integer {name}"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        assert isinstance(
            entry_count,
            int,
        )
        assert isinstance(
            entry_size,
            int,
        )

        if entry_size < cls.KNOWN_ENTRY_SIZE:
            raise ValueError(
                "vendor ramdisk-table entry is smaller than "
                "the known v4 structure"
            )

        data = artifact.path.read_bytes()

        expected_size = (
            entry_count
            * entry_size
        )

        if len(
            data
        ) != expected_size:
            raise ValueError(
                "vendor ramdisk-table byte conservation failed: "
                f"expected {expected_size}, got {len(data)}"
            )

        entries: list[
            ParsedVendorRamdiskTableEntry
        ] = []

        for index in range(
            entry_count
        ):
            start = (
                index
                * entry_size
            )

            end = (
                start
                + entry_size
            )

            raw = data[
                start:end
            ]

            if len(
                raw
            ) != entry_size:
                raise ValueError(
                    "vendor ramdisk-table entry was truncated"
                )

            ramdisk_size = int.from_bytes(
                raw[
                    0:4
                ],
                "little",
            )

            ramdisk_offset = int.from_bytes(
                raw[
                    4:8
                ],
                "little",
            )

            ramdisk_type = int.from_bytes(
                raw[
                    8:12
                ],
                "little",
            )

            name_bytes = raw[
                12:44
            ]

            ramdisk_name = (
                name_bytes
                .split(
                    b"\x00",
                    1,
                )[0]
                .decode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )

            board_id = tuple(
                int.from_bytes(
                    raw[
                        44 + word_index * 4:
                        48 + word_index * 4
                    ],
                    "little",
                )
                for word_index
                in range(
                    16
                )
            )

            entries.append(
                ParsedVendorRamdiskTableEntry(
                    index=index,
                    ramdisk_size=ramdisk_size,
                    ramdisk_offset=(
                        ramdisk_offset
                    ),
                    ramdisk_type=(
                        ramdisk_type
                    ),
                    ramdisk_name=(
                        ramdisk_name
                    ),
                    board_id=(
                        board_id
                    ),
                    raw=raw,
                )
            )

        return ParsedVendorRamdiskTable(
            artifact=artifact,
            boot_image_artifact=(
                boot_image_artifact
            ),
            entry_size=entry_size,
            entries=tuple(
                entries
            ),
        )
