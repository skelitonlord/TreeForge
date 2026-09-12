from __future__ import annotations

from pathlib import Path
import struct

from treeforge.android.extraction.fbpk.model import (
    FbpkContainerStructure,
    FbpkEntry,
)


class FbpkContainerDecodeError(
    RuntimeError,
):
    """
    Raised when a physical FBPK container cannot be decoded safely.
    """


class FbpkContainerDecoder:
    """
    Decode the physical table of an FBPK container.

    Decode FBPK layouts established from direct physical evidence.

    Supported layouts:

    - version 1: proven single-entry modem/radio layout;
    - version 2: existing table-based layout.

    Unknown versions and unproven v1 multi-entry layouts are rejected rather
    than guessed.
    """

    MAGIC = b"FBPK"

    SUPPORTED_VERSIONS = frozenset(
        {
            1,
            2,
        }
    )

    V1_HEADER_SIZE = 0x54
    V1_ENTRY_SIZE = 0x38
    V1_NAME_OFFSET = 4
    V1_NAME_SIZE = 36
    V1_TAIL_OFFSET = 40
    V1_TAIL_UINT32_COUNT = 4

    MINIMUM_HEADER_SIZE = 16

    RECORD_NAME_OFFSET = 4
    RECORD_NAME_SIZE = 64
    RECORD_TAIL_OFFSET = 68
    RECORD_TAIL_UINT32_COUNT = 9

    EXPECTED_V2_ENTRY_SIZE = (
        RECORD_TAIL_OFFSET
        + RECORD_TAIL_UINT32_COUNT * 4
    )

    def supports(
        self,
        source: Path,
    ) -> bool:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.is_file():
            return False

        try:
            with source.open(
                "rb"
            ) as stream:
                return (
                    stream.read(
                        4
                    )
                    == self.MAGIC
                )

        except OSError:
            return False

    def _decode_v1(
        self,
        *,
        source: Path,
        image_size: int,
    ) -> FbpkContainerStructure:
        """
        Decode the physically proven FBPK v1 single-entry layout.

        The supported structure has:

            fixed container header at 0x54
            one 0x38-byte entry record
            payload beginning immediately after that record

        The final record uint32 is the payload CRC32. Extraction preserves it
        as raw structure; checksum verification may be performed separately.
        """

        if image_size < (
            self.V1_HEADER_SIZE
            + self.V1_ENTRY_SIZE
        ):
            raise FbpkContainerDecodeError(
                "FBPK v1 source is smaller than its proven "
                "single-entry structure"
            )

        with source.open(
            "rb"
        ) as stream:
            stream.seek(
                0x4c
            )

            entry_count, declared_image_size = (
                struct.unpack(
                    "<II",
                    stream.read(
                        8
                    ),
                )
            )

            if entry_count != 1:
                raise FbpkContainerDecodeError(
                    "Unsupported FBPK v1 entry count: "
                    f"{entry_count}; only the physically proven "
                    "single-entry layout is supported"
                )

            if declared_image_size != image_size:
                raise FbpkContainerDecodeError(
                    "FBPK v1 declared image size does not match "
                    "physical source size: "
                    f"declared={declared_image_size}, "
                    f"actual={image_size}"
                )

            record_offset = (
                self.V1_HEADER_SIZE
            )

            stream.seek(
                record_offset
            )

            record = stream.read(
                self.V1_ENTRY_SIZE
            )

            if len(record) != self.V1_ENTRY_SIZE:
                raise FbpkContainerDecodeError(
                    "FBPK v1 entry ended unexpectedly"
                )

            record_type = (
                struct.unpack_from(
                    "<I",
                    record,
                    0,
                )[0]
            )

            name_bytes = (
                record[
                    self.V1_NAME_OFFSET:
                    (
                        self.V1_NAME_OFFSET
                        + self.V1_NAME_SIZE
                    )
                ]
                .split(
                    b"\0",
                    1,
                )[0]
            )

            try:
                name = name_bytes.decode(
                    "ascii"
                )
            except UnicodeDecodeError as error:
                raise FbpkContainerDecodeError(
                    "FBPK v1 entry name is not ASCII"
                ) from error

            raw_tail = tuple(
                struct.unpack_from(
                    "<I",
                    record,
                    (
                        self.V1_TAIL_OFFSET
                        + index * 4
                    ),
                )[0]
                for index in range(
                    self.V1_TAIL_UINT32_COUNT
                )
            )

            payload_offset = (
                self.V1_HEADER_SIZE
                + self.V1_ENTRY_SIZE
            )

            payload_size = (
                raw_tail[0]
            )

            if payload_size <= 0:
                raise FbpkContainerDecodeError(
                    "FBPK v1 entry exposes no payload"
                )

            if (
                payload_offset
                + payload_size
                != image_size
            ):
                raise FbpkContainerDecodeError(
                    "FBPK v1 payload range does not exactly cover "
                    "the proven post-table image region: "
                    f"offset={payload_offset}, "
                    f"size={payload_size}, "
                    f"image_size={image_size}"
                )

            entry = FbpkEntry(
                index=0,
                record_offset=record_offset,
                record_type=record_type,
                name=name,
                raw_tail=raw_tail,
                payload_offset_bytes=(
                    payload_offset
                ),
                payload_size_bytes=(
                    payload_size
                ),
                flags_value=None,
            )

        return FbpkContainerStructure(
            version=1,
            header_size=(
                self.V1_HEADER_SIZE
            ),
            entry_size=(
                self.V1_ENTRY_SIZE
            ),
            table_end=(
                payload_offset
            ),
            image_size=image_size,
            entries=(
                entry,
            ),
        )

    def decode(
        self,
        source: Path,
    ) -> FbpkContainerStructure:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.is_file():
            raise FileNotFoundError(
                source
            )

        image_size = (
            source.stat().st_size
        )

        if image_size < self.MINIMUM_HEADER_SIZE:
            raise FbpkContainerDecodeError(
                "FBPK source is smaller than its minimum header"
            )

        with source.open(
            "rb"
        ) as stream:
            header = stream.read(
                self.MINIMUM_HEADER_SIZE
            )

            magic = header[:4]

            if magic != self.MAGIC:
                raise FbpkContainerDecodeError(
                    f"FBPK magic is missing: {source}"
                )

            (
                version,
                header_size,
                entry_size,
            ) = struct.unpack_from(
                "<III",
                header,
                4,
            )

            if version not in self.SUPPORTED_VERSIONS:
                raise FbpkContainerDecodeError(
                    "Unsupported FBPK version: "
                    f"{version}"
                )

            if version == 1:
                return self._decode_v1(
                    source=source,
                    image_size=image_size,
                )

            if (
                header_size < self.MINIMUM_HEADER_SIZE
                or header_size > image_size
            ):
                raise FbpkContainerDecodeError(
                    "Invalid FBPK header size: "
                    f"{header_size}"
                )

            if (
                entry_size
                != self.EXPECTED_V2_ENTRY_SIZE
            ):
                raise FbpkContainerDecodeError(
                    "Unsupported FBPK v2 entry size: "
                    f"{entry_size}"
                )

            #
            # The earliest positive payload offset is the physical boundary
            # between the entry table/padding and payload bytes.
            #
            # Decode records incrementally. As soon as a valid payload offset
            # is observed, it becomes the upper bound for further record
            # decoding.
            #
            table_end = image_size

            entries: list[
                FbpkEntry
            ] = []

            index = 0
            record_offset = (
                header_size
            )

            while (
                record_offset + entry_size
                <= table_end
            ):
                stream.seek(
                    record_offset
                )

                record = stream.read(
                    entry_size
                )

                if len(
                    record
                ) != entry_size:
                    raise FbpkContainerDecodeError(
                        "FBPK entry ended unexpectedly at "
                        f"offset {record_offset}"
                    )

                record_type = (
                    struct.unpack_from(
                        "<I",
                        record,
                        0,
                    )[0]
                )

                name_bytes = (
                    record[
                        self.RECORD_NAME_OFFSET:
                        (
                            self.RECORD_NAME_OFFSET
                            + self.RECORD_NAME_SIZE
                        )
                    ]
                    .split(
                        b"\0",
                        1,
                    )[0]
                )

                try:
                    name = (
                        name_bytes.decode(
                            "ascii"
                        )
                    )

                except UnicodeDecodeError as error:
                    raise FbpkContainerDecodeError(
                        "FBPK entry name is not ASCII at "
                        f"record {index}"
                    ) from error

                raw_tail = tuple(
                    struct.unpack_from(
                        "<I",
                        record,
                        (
                            self.RECORD_TAIL_OFFSET
                            + tail_index * 4
                        ),
                    )[0]
                    for tail_index
                    in range(
                        self.RECORD_TAIL_UINT32_COUNT
                    )
                )

                entry = FbpkEntry(
                    index=index,
                    record_offset=record_offset,
                    record_type=record_type,
                    name=name,
                    raw_tail=raw_tail,
                    payload_offset_bytes=(
                        raw_tail[3]
                    ),
                    payload_size_bytes=(
                        raw_tail[5]
                    ),
                    flags_value=(
                        raw_tail[7]
                    ),
                )

                if entry.has_payload:
                    payload_end = (
                        entry.payload_offset
                        + entry.payload_size
                    )

                    if (
                        entry.payload_offset
                        < header_size
                    ):
                        raise FbpkContainerDecodeError(
                            "FBPK payload overlaps header: "
                            f"entry={index}, "
                            f"offset={entry.payload_offset}"
                        )

                    if payload_end > image_size:
                        raise FbpkContainerDecodeError(
                            "FBPK payload extends beyond image: "
                            f"entry={index}, "
                            f"offset={entry.payload_offset}, "
                            f"size={entry.payload_size}, "
                            f"image_size={image_size}"
                        )

                    table_end = min(
                        table_end,
                        entry.payload_offset,
                    )

                    if (
                        record_offset + entry_size
                        > table_end
                    ):
                        raise FbpkContainerDecodeError(
                            "FBPK entry table overlaps payload data"
                        )

                entries.append(
                    entry
                )

                index += 1

                record_offset = (
                    header_size
                    + index * entry_size
                )

            #
            # Every named/non-empty entry must point to a real in-image
            # payload. Empty zero slots remain structural table evidence.
            #
            for entry in entries:
                if (
                    entry.name
                    and not entry.has_payload
                ):
                    raise FbpkContainerDecodeError(
                        "Named FBPK entry exposes no valid payload: "
                        f"entry={entry.index}, "
                        f"name={entry.name!r}"
                    )

        return FbpkContainerStructure(
            version=version,
            header_size=header_size,
            entry_size=entry_size,
            table_end=table_end,
            image_size=image_size,
            entries=tuple(
                entries
            ),
        )
