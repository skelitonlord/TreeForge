from __future__ import annotations

from pathlib import Path
import struct

from treeforge.android.extraction.sflb.model import (
    EmbeddedSflbStructure,
    SflbContainer,
    SflbEntry,
)


class SflbContainerDecodeError(
    RuntimeError,
):
    """
    Raised when an SFLB source cannot be decoded safely.
    """


class SflbContainerDecoder:
    """
    Discover embedded SFLB resource containers by intrinsic structure.
    """

    MAGIC = b"sFlB"

    SUPPORTED_VERSION = 1

    HEADER_SIZE = 0x20
    RECORD_SIZE = 0x40

    NAME_OFFSET = 0x00
    NAME_SIZE = 0x30

    PAYLOAD_SIZE_OFFSET = 0x30
    PAYLOAD_OFFSET_OFFSET = 0x34
    OPAQUE_WORD_OFFSET = 0x38
    FLAGS_OFFSET = 0x3C

    def supports(
        self,
        source: Path,
    ) -> bool:
        try:
            return bool(
                self.decode(
                    source
                ).containers
            )

        except (
            FileNotFoundError,
            OSError,
            ValueError,
            SflbContainerDecodeError,
        ):
            return False

    def decode(
        self,
        source: Path,
    ) -> EmbeddedSflbStructure:
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

        data = source.read_bytes()

        decoded: list[
            SflbContainer
        ] = []

        for offset in self._candidate_offsets(
            data
        ):
            container = self._decode_candidate(
                data,
                offset,
            )

            if container is not None:
                decoded.append(
                    container
                )

        containers = tuple(
            SflbContainer(
                index=index,
                offset_bytes=value.offset_bytes,
                span_bytes=value.span_bytes,
                version=value.version,
                entry_count=value.entry_count,
                secondary_count=value.secondary_count,
                raw_header_tail=value.raw_header_tail,
                entries=value.entries,
            )
            for index, value
            in enumerate(
                sorted(
                    decoded,
                    key=lambda item: (
                        item.offset_bytes
                    ),
                )
            )
        )

        return EmbeddedSflbStructure(
            source=source,
            image_size=len(
                data
            ),
            containers=containers,
        )

    @classmethod
    def _candidate_offsets(
        cls,
        data: bytes,
    ) -> tuple[
        int,
        ...,
    ]:
        offsets: list[
            int
        ] = []

        cursor = 0

        while True:
            offset = data.find(
                cls.MAGIC,
                cursor,
            )

            if offset < 0:
                break

            offsets.append(
                offset
            )

            cursor = (
                offset
                + 1
            )

        return tuple(
            offsets
        )

    def _decode_candidate(
        self,
        data: bytes,
        offset: int,
    ) -> SflbContainer | None:
        if (
            offset
            + self.HEADER_SIZE
            > len(
                data
            )
        ):
            return None

        try:
            (
                version,
                entry_count,
                secondary_count,
                span_bytes,
                raw_header_0,
                raw_header_1,
                raw_header_2,
            ) = struct.unpack_from(
                "<7I",
                data,
                offset + 4,
            )

        except struct.error:
            return None

        if version != self.SUPPORTED_VERSION:
            return None

        if (
            entry_count <= 0
            or entry_count > 65535
        ):
            return None

        table_size = (
            entry_count
            * self.RECORD_SIZE
        )

        minimum_span = (
            self.HEADER_SIZE
            + table_size
        )

        if span_bytes < minimum_span:
            return None

        container_end = (
            offset
            + span_bytes
        )

        if container_end > len(
            data
        ):
            return None

        table_start = (
            offset
            + self.HEADER_SIZE
        )

        entries: list[
            SflbEntry
        ] = []

        payload_ranges: list[
            tuple[
                int,
                int,
            ]
        ] = []

        for index in range(
            entry_count
        ):
            record_absolute = (
                table_start
                + index
                * self.RECORD_SIZE
            )

            record_relative = (
                self.HEADER_SIZE
                + index
                * self.RECORD_SIZE
            )

            if (
                record_absolute
                + self.RECORD_SIZE
                > container_end
            ):
                return None

            name_field = data[
                record_absolute:
                record_absolute
                + self.NAME_SIZE
            ]

            nul = name_field.find(
                b"\0"
            )

            if nul < 0:
                return None

            name_bytes = name_field[
                :nul
            ]

            if not name_bytes:
                return None

            try:
                name = name_bytes.decode(
                    "ascii"
                )

            except UnicodeDecodeError:
                return None

            try:
                (
                    payload_size,
                    payload_offset,
                    opaque_word,
                    flags,
                ) = struct.unpack_from(
                    "<4I",
                    data,
                    (
                        record_absolute
                        + self.PAYLOAD_SIZE_OFFSET
                    ),
                )

            except struct.error:
                return None

            if payload_size <= 0:
                return None

            if payload_offset < minimum_span:
                return None

            payload_end = (
                payload_offset
                + payload_size
            )

            if payload_end > span_bytes:
                return None

            payload_ranges.append(
                (
                    payload_offset,
                    payload_end,
                )
            )

            entries.append(
                SflbEntry(
                    index=index,
                    record_offset=record_relative,
                    name=name,
                    payload_size=payload_size,
                    payload_offset=payload_offset,
                    opaque_word=opaque_word,
                    flags=flags,
                )
            )

        ordered_ranges = sorted(
            payload_ranges
        )

        for previous, current in zip(
            ordered_ranges,
            ordered_ranges[1:],
        ):
            if current[0] < previous[1]:
                return None

        return SflbContainer(
            index=0,
            offset_bytes=offset,
            span_bytes=span_bytes,
            version=version,
            entry_count=entry_count,
            secondary_count=secondary_count,
            raw_header_tail=(
                raw_header_0,
                raw_header_1,
                raw_header_2,
            ),
            entries=tuple(
                entries
            ),
        )
