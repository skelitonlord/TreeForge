from __future__ import annotations

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from pathlib import Path

from treeforge.android.parsing.bootloader.model import (
    AndroidParsedFbpt,
    AndroidParsedFbptEntry,
)


class AndroidFbptParser:
    """
    Decode the literal FBPT structure observed in FBPK partition-table
    children.

    The format is structurally fixed by the real factory artifacts:

      header:  64 bytes
      record: 136 bytes
    """

    MAGIC = b"FBPT"

    HEADER_SIZE = 64
    RECORD_SIZE = 136

    NAME_OFFSET = 0x0C
    NAME_SIZE = 0x24

    TYPE_IDENTIFIER_OFFSET = 0x30
    TYPE_IDENTIFIER_SIZE = 0x25

    INSTANCE_IDENTIFIER_OFFSET = 0x55
    INSTANCE_IDENTIFIER_SIZE = 0x25

    RESERVED_TAIL_OFFSET = 0x7A

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
    def _u64(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 8
            ],
            "little",
        )

    @staticmethod
    def _text(
        data: bytes,
    ) -> str:
        return (
            data
            .split(
                b"\0",
                1,
            )[0]
            .decode(
                "ascii",
                errors="replace",
            )
        )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedFbpt:
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
                f"FBPT source is smaller than "
                f"{self.HEADER_SIZE} bytes: {source}"
            )

        if (
            data[:4]
            != self.MAGIC
        ):
            raise ValueError(
                f"invalid FBPT magic: {source}"
            )

        version = self._u32(
            data,
            4,
        )

        table_index = self._u32(
            data,
            8,
        )

        reserved_header_value = (
            self._u32(
                data,
                12,
            )
        )

        entry_count = self._u32(
            data,
            16,
        )

        expected_size = (
            self.HEADER_SIZE
            + (
                entry_count
                * self.RECORD_SIZE
            )
        )

        if len(data) != expected_size:
            raise ValueError(
                "FBPT physical size does not match "
                "header entry count: "
                f"size={len(data)}, "
                f"entry_count={entry_count}, "
                f"expected={expected_size}"
            )

        table_identifier = (
            self._text(
                data[
                    20:
                    self.HEADER_SIZE
                ]
            )
        )

        entries: list[
            AndroidParsedFbptEntry
        ] = []

        for index in range(
            entry_count
        ):
            start = (
                self.HEADER_SIZE
                + (
                    index
                    * self.RECORD_SIZE
                )
            )

            record = data[
                start:
                start
                + self.RECORD_SIZE
            ]

            size_bytes = self._u64(
                record,
                0,
            )

            reserved_prefix = (
                self._u32(
                    record,
                    8,
                )
            )

            name = self._text(
                record[
                    self.NAME_OFFSET:
                    self.NAME_OFFSET
                    + self.NAME_SIZE
                ]
            )

            type_identifier = (
                self._text(
                    record[
                        self.TYPE_IDENTIFIER_OFFSET:
                        self.TYPE_IDENTIFIER_OFFSET
                        + self.TYPE_IDENTIFIER_SIZE
                    ]
                )
            )

            instance_identifier = (
                self._text(
                    record[
                        self.INSTANCE_IDENTIFIER_OFFSET:
                        self.INSTANCE_IDENTIFIER_OFFSET
                        + self.INSTANCE_IDENTIFIER_SIZE
                    ]
                )
            )

            entries.append(
                AndroidParsedFbptEntry(
                    index=index,
                    size_bytes=size_bytes,
                    reserved_prefix=(
                        reserved_prefix
                    ),
                    name=name,
                    type_identifier=(
                        type_identifier
                    ),
                    instance_identifier=(
                        instance_identifier
                    ),
                    reserved_tail=record[
                        self.RESERVED_TAIL_OFFSET:
                    ],
                    raw_record=record,
                )
            )

        return AndroidParsedFbpt(
            version=version,
            table_index=table_index,
            reserved_header_value=(
                reserved_header_value
            ),
            entry_count=entry_count,
            table_identifier=(
                table_identifier
            ),
            entries=tuple(
                entries
            ),
            raw_header=data[
                :self.HEADER_SIZE
            ],
        )
