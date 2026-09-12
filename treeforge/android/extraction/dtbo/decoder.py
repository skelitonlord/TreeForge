from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from struct import Struct


class DtboImageDecodingError(
    ValueError,
):
    """
    Raised when a physical Android DT table container is malformed.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class DtboTableHeader:
    """
    Exact physical Android DT table header.

    All integer fields are stored in host byte order after decoding the
    big-endian values present in the image.
    """

    magic: int
    total_size: int
    header_size: int
    dt_entry_size: int
    dt_entry_count: int
    dt_entries_offset: int
    page_size: int
    version: int


@dataclass(
    frozen=True,
    slots=True,
)
class DtboTableEntry:
    """
    Exact physical record for one DT table entry.

    Extraction interprets only dt_size and dt_offset as physical placement.

    id, rev, and custom preserve the remaining standard v0 entry words
    without assigning higher-level device-tree semantics.
    """

    index: int
    dt_size: int
    dt_offset: int
    id: int
    rev: int
    custom: tuple[
        int,
        int,
        int,
        int,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class DtboTableImage:
    header: DtboTableHeader
    entries: tuple[
        DtboTableEntry,
        ...,
    ]


class DtboImageDecoder:
    """
    Decode the physical Android DT table container format.

    The format uses big-endian 32-bit words.

    Extraction owns:
      - container recognition;
      - structural header/entry decoding;
      - physical range validation.

    Device-tree semantic interpretation remains downstream.
    """

    DT_TABLE_MAGIC = 0xD7B7AB1E

    HEADER_STRUCT = Struct(
        ">8I"
    )

    ENTRY_STRUCT = Struct(
        ">8I"
    )

    MIN_HEADER_SIZE = (
        HEADER_STRUCT.size
    )

    MIN_ENTRY_SIZE = (
        ENTRY_STRUCT.size
    )

    @classmethod
    def supports(
        cls,
        path: Path,
    ) -> bool:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            return False

        try:
            with path.open(
                "rb"
            ) as stream:
                magic = stream.read(
                    4
                )
        except OSError:
            return False

        return (
            magic
            == cls.DT_TABLE_MAGIC.to_bytes(
                4,
                byteorder="big",
            )
        )

    def decode(
        self,
        path: Path,
    ) -> DtboTableImage:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not path.is_file():
            raise DtboImageDecodingError(
                "DTBO source must be a regular file: "
                f"{path}"
            )

        file_size = (
            path.stat().st_size
        )

        if file_size < self.MIN_HEADER_SIZE:
            raise DtboImageDecodingError(
                "DTBO image is smaller than the table header: "
                f"{path}"
            )

        with path.open(
            "rb"
        ) as stream:
            header_bytes = stream.read(
                self.MIN_HEADER_SIZE
            )

            (
                magic,
                total_size,
                header_size,
                dt_entry_size,
                dt_entry_count,
                dt_entries_offset,
                page_size,
                version,
            ) = self.HEADER_STRUCT.unpack(
                header_bytes
            )

            if magic != self.DT_TABLE_MAGIC:
                raise DtboImageDecodingError(
                    "Invalid DT table magic: "
                    f"0x{magic:08x}"
                )

            if header_size < self.MIN_HEADER_SIZE:
                raise DtboImageDecodingError(
                    "DT table header_size is smaller than "
                    "the standard header"
                )

            if dt_entry_size < self.MIN_ENTRY_SIZE:
                raise DtboImageDecodingError(
                    "DT table dt_entry_size is smaller than "
                    "the standard entry"
                )

            if total_size < header_size:
                raise DtboImageDecodingError(
                    "DT table total_size is smaller than header_size"
                )

            if total_size > file_size:
                raise DtboImageDecodingError(
                    "DT table total_size extends beyond image: "
                    f"total_size={total_size}, "
                    f"file_size={file_size}"
                )

            entries_end = (
                dt_entries_offset
                + (
                    dt_entry_count
                    * dt_entry_size
                )
            )

            if dt_entries_offset < header_size:
                raise DtboImageDecodingError(
                    "DT entry table overlaps the DT table header"
                )

            if entries_end > total_size:
                raise DtboImageDecodingError(
                    "DT entry table extends beyond declared total_size"
                )

            entries: list[
                DtboTableEntry
            ] = []

            for index in range(
                dt_entry_count
            ):
                entry_offset = (
                    dt_entries_offset
                    + (
                        index
                        * dt_entry_size
                    )
                )

                stream.seek(
                    entry_offset
                )

                entry_bytes = stream.read(
                    self.MIN_ENTRY_SIZE
                )

                if (
                    len(entry_bytes)
                    != self.MIN_ENTRY_SIZE
                ):
                    raise DtboImageDecodingError(
                        "Incomplete DT table entry: "
                        f"index={index}"
                    )

                words = (
                    self.ENTRY_STRUCT.unpack(
                        entry_bytes
                    )
                )

                dt_size = words[0]
                dt_offset = words[1]

                if dt_size <= 0:
                    raise DtboImageDecodingError(
                        "DT table entry declares zero size: "
                        f"index={index}"
                    )

                dt_end = (
                    dt_offset
                    + dt_size
                )

                if dt_offset < entries_end:
                    raise DtboImageDecodingError(
                        "DT payload overlaps the entry table: "
                        f"index={index}, "
                        f"offset={dt_offset}"
                    )

                if dt_end > total_size:
                    raise DtboImageDecodingError(
                        "DT payload extends beyond declared total_size: "
                        f"index={index}, "
                        f"offset={dt_offset}, "
                        f"size={dt_size}, "
                        f"end={dt_end}, "
                        f"total_size={total_size}"
                    )

                entries.append(
                    DtboTableEntry(
                        index=index,
                        dt_size=dt_size,
                        dt_offset=dt_offset,
                        id=words[2],
                        rev=words[3],
                        custom=(
                            words[4],
                            words[5],
                            words[6],
                            words[7],
                        ),
                    )
                )

        return DtboTableImage(
            header=DtboTableHeader(
                magic=magic,
                total_size=total_size,
                header_size=header_size,
                dt_entry_size=dt_entry_size,
                dt_entry_count=dt_entry_count,
                dt_entries_offset=dt_entries_offset,
                page_size=page_size,
                version=version,
            ),
            entries=tuple(
                entries
            ),
        )
