from __future__ import annotations

from dataclasses import dataclass
from struct import Struct

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionArtifactKind,
)
from treeforge.android.parsing.dtb.model import (
    ParsedFdt,
    ParsedFdtHeader,
    ParsedFdtNode,
    ParsedFdtProperty,
    ParsedFdtReservation,
)


class FdtParsingError(
    ValueError,
):
    """
    Raised when a canonical FDT/DTB artifact is structurally malformed.
    """


@dataclass(
    slots=True,
)
class _NodeBuilder:
    name: str
    properties: list[
        ParsedFdtProperty
    ]
    children: list[
        ParsedFdtNode
    ]

    def freeze(
        self,
    ) -> ParsedFdtNode:
        return ParsedFdtNode(
            name=self.name,
            properties=tuple(
                self.properties
            ),
            children=tuple(
                self.children
            ),
        )


class AndroidFdtParser:
    """
    Decode the intrinsic binary Flattened Device Tree format.

    This parser does not interpret Android/device semantics. Property values
    remain exact raw bytes.
    """

    FDT_MAGIC = 0xD00DFEED

    FDT_BEGIN_NODE = 1
    FDT_END_NODE = 2
    FDT_PROP = 3
    FDT_NOP = 4
    FDT_END = 9

    HEADER = Struct(
        ">10I"
    )

    RESERVATION = Struct(
        ">QQ"
    )

    UINT32 = Struct(
        ">I"
    )

    PROP_HEADER = Struct(
        ">II"
    )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> ParsedFdt:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            artifact.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise FdtParsingError(
                "FDT artifact must be a regular file"
            )

        data = (
            artifact.path.read_bytes()
        )

        if len(
            data
        ) < self.HEADER.size:
            raise FdtParsingError(
                "FDT source is smaller than the standard header"
            )

        header = self._decode_header(
            data
        )

        logical = data[
            :header.totalsize
        ]

        reservations, reservation_end = (
            self._decode_reservations(
                logical,
                header,
            )
        )

        self._validate_block_ranges(
            header,
            reservation_end,
        )

        strings = logical[
            header.off_dt_strings:
            (
                header.off_dt_strings
                + header.size_dt_strings
            )
        ]

        root = self._decode_structure(
            logical,
            header,
            strings,
        )

        return ParsedFdt(
            artifact=artifact,
            header=header,
            reservations=reservations,
            root=root,
        )

    def _decode_header(
        self,
        data: bytes,
    ) -> ParsedFdtHeader:
        words = self.HEADER.unpack_from(
            data,
            0,
        )

        header = ParsedFdtHeader(
            magic=words[0],
            totalsize=words[1],
            off_dt_struct=words[2],
            off_dt_strings=words[3],
            off_mem_rsvmap=words[4],
            version=words[5],
            last_comp_version=words[6],
            boot_cpuid_phys=words[7],
            size_dt_strings=words[8],
            size_dt_struct=words[9],
        )

        if (
            header.magic
            != self.FDT_MAGIC
        ):
            raise FdtParsingError(
                "Invalid FDT magic: "
                f"0x{header.magic:08x}"
            )

        if (
            header.totalsize
            < self.HEADER.size
        ):
            raise FdtParsingError(
                "FDT totalsize is smaller than its standard header"
            )

        if (
            header.totalsize
            > len(
                data
            )
        ):
            raise FdtParsingError(
                "FDT totalsize extends beyond the canonical artifact: "
                f"totalsize={header.totalsize}, "
                f"artifact_size={len(data)}"
            )

        if (
            header.last_comp_version
            > header.version
        ):
            raise FdtParsingError(
                "FDT last compatible version exceeds version"
            )

        for (
            field_name,
            offset,
        ) in (
            (
                "off_dt_struct",
                header.off_dt_struct,
            ),
            (
                "off_dt_strings",
                header.off_dt_strings,
            ),
            (
                "off_mem_rsvmap",
                header.off_mem_rsvmap,
            ),
        ):
            if (
                offset
                < self.HEADER.size
                or offset
                >= header.totalsize
            ):
                raise FdtParsingError(
                    f"{field_name} lies outside the FDT body: "
                    f"{offset}"
                )

        if (
            header.off_dt_struct
            % 4
        ):
            raise FdtParsingError(
                "FDT structure block is not 4-byte aligned"
            )

        if (
            header.off_dt_strings
            % 4
        ):
            raise FdtParsingError(
                "FDT strings block is not 4-byte aligned"
            )

        if (
            header.off_mem_rsvmap
            % 8
        ):
            raise FdtParsingError(
                "FDT reservation map is not 8-byte aligned"
            )

        if (
            header.size_dt_struct
            <= 0
        ):
            raise FdtParsingError(
                "FDT structure block cannot be empty"
            )

        struct_end = (
            header.off_dt_struct
            + header.size_dt_struct
        )

        strings_end = (
            header.off_dt_strings
            + header.size_dt_strings
        )

        if (
            struct_end
            > header.totalsize
        ):
            raise FdtParsingError(
                "FDT structure block extends beyond totalsize"
            )

        if (
            strings_end
            > header.totalsize
        ):
            raise FdtParsingError(
                "FDT strings block extends beyond totalsize"
            )

        return header

    def _decode_reservations(
        self,
        data: bytes,
        header: ParsedFdtHeader,
    ) -> tuple[
        tuple[
            ParsedFdtReservation,
            ...,
        ],
        int,
    ]:
        reservations: list[
            ParsedFdtReservation
        ] = []

        cursor = (
            header.off_mem_rsvmap
        )

        while True:
            end = (
                cursor
                + self.RESERVATION.size
            )

            if end > len(
                data
            ):
                raise FdtParsingError(
                    "FDT reservation map is truncated"
                )

            (
                address,
                size,
            ) = self.RESERVATION.unpack_from(
                data,
                cursor,
            )

            cursor = end

            if (
                address == 0
                and size == 0
            ):
                break

            reservations.append(
                ParsedFdtReservation(
                    address=address,
                    size=size,
                )
            )

        return (
            tuple(
                reservations
            ),
            cursor,
        )

    def _validate_block_ranges(
        self,
        header: ParsedFdtHeader,
        reservation_end: int,
    ) -> None:
        ranges = (
            (
                "header",
                0,
                self.HEADER.size,
            ),
            (
                "reservation map",
                header.off_mem_rsvmap,
                reservation_end,
            ),
            (
                "structure block",
                header.off_dt_struct,
                (
                    header.off_dt_struct
                    + header.size_dt_struct
                ),
            ),
            (
                "strings block",
                header.off_dt_strings,
                (
                    header.off_dt_strings
                    + header.size_dt_strings
                ),
            ),
        )

        for index, (
            name_a,
            start_a,
            end_a,
        ) in enumerate(
            ranges
        ):
            if (
                start_a < 0
                or end_a < start_a
                or end_a > header.totalsize
            ):
                raise FdtParsingError(
                    f"Invalid FDT {name_a} range"
                )

            for (
                name_b,
                start_b,
                end_b,
            ) in ranges[
                index + 1:
            ]:
                if (
                    start_a < end_b
                    and start_b < end_a
                ):
                    raise FdtParsingError(
                        "Overlapping FDT blocks: "
                        f"{name_a} and {name_b}"
                    )

    def _decode_structure(
        self,
        data: bytes,
        header: ParsedFdtHeader,
        strings: bytes,
    ) -> ParsedFdtNode:
        start = (
            header.off_dt_struct
        )

        end = (
            start
            + header.size_dt_struct
        )

        cursor = start

        stack: list[
            _NodeBuilder
        ] = []

        root: ParsedFdtNode | None = None
        saw_end = False

        while cursor < end:
            if (
                cursor + 4
                > end
            ):
                raise FdtParsingError(
                    "Truncated FDT structure token"
                )

            token = self.UINT32.unpack_from(
                data,
                cursor,
            )[0]

            cursor += 4

            if (
                token
                == self.FDT_BEGIN_NODE
            ):
                (
                    node_name,
                    cursor,
                ) = self._read_c_string(
                    data,
                    cursor,
                    end,
                    context="FDT node name",
                )

                cursor = self._align4(
                    cursor
                )

                if cursor > end:
                    raise FdtParsingError(
                        "Aligned FDT node name extends beyond structure block"
                    )

                stack.append(
                    _NodeBuilder(
                        name=node_name,
                        properties=[],
                        children=[],
                    )
                )

                continue

            if (
                token
                == self.FDT_END_NODE
            ):
                if not stack:
                    raise FdtParsingError(
                        "FDT_END_NODE without matching FDT_BEGIN_NODE"
                    )

                node = (
                    stack.pop()
                    .freeze()
                )

                if stack:
                    stack[
                        -1
                    ].children.append(
                        node
                    )
                else:
                    if root is not None:
                        raise FdtParsingError(
                            "FDT contains multiple root nodes"
                        )

                    root = node

                continue

            if (
                token
                == self.FDT_PROP
            ):
                if not stack:
                    raise FdtParsingError(
                        "FDT_PROP outside a node"
                    )

                if (
                    cursor
                    + self.PROP_HEADER.size
                    > end
                ):
                    raise FdtParsingError(
                        "Truncated FDT property header"
                    )

                (
                    value_length,
                    name_offset,
                ) = self.PROP_HEADER.unpack_from(
                    data,
                    cursor,
                )

                cursor += (
                    self.PROP_HEADER.size
                )

                value_end = (
                    cursor
                    + value_length
                )

                if value_end > end:
                    raise FdtParsingError(
                        "FDT property value extends beyond structure block"
                    )

                value = bytes(
                    data[
                        cursor:value_end
                    ]
                )

                cursor = self._align4(
                    value_end
                )

                if cursor > end:
                    raise FdtParsingError(
                        "Aligned FDT property extends beyond structure block"
                    )

                name = self._property_name(
                    strings,
                    name_offset,
                )

                stack[
                    -1
                ].properties.append(
                    ParsedFdtProperty(
                        name=name,
                        value=value,
                    )
                )

                continue

            if (
                token
                == self.FDT_NOP
            ):
                continue

            if (
                token
                == self.FDT_END
            ):
                if stack:
                    raise FdtParsingError(
                        "FDT_END encountered before all nodes were closed"
                    )

                if root is None:
                    raise FdtParsingError(
                        "FDT_END encountered before a root node"
                    )

                saw_end = True

                trailing = data[
                    cursor:end
                ]

                if any(
                    trailing
                ):
                    raise FdtParsingError(
                        "Non-zero bytes follow FDT_END in structure block"
                    )

                break

            raise FdtParsingError(
                "Unknown FDT structure token: "
                f"0x{token:08x}"
            )

        if not saw_end:
            raise FdtParsingError(
                "FDT structure block does not contain FDT_END"
            )

        if stack:
            raise FdtParsingError(
                "FDT structure contains unclosed nodes"
            )

        if root is None:
            raise FdtParsingError(
                "FDT structure contains no root node"
            )

        return root

    @staticmethod
    def _read_c_string(
        data: bytes,
        start: int,
        limit: int,
        *,
        context: str,
    ) -> tuple[
        str,
        int,
    ]:
        terminator = data.find(
            b"\0",
            start,
            limit,
        )

        if terminator < 0:
            raise FdtParsingError(
                f"{context} is not NUL terminated"
            )

        raw = data[
            start:terminator
        ]

        try:
            value = raw.decode(
                "utf-8"
            )
        except UnicodeDecodeError as error:
            raise FdtParsingError(
                f"{context} is not valid UTF-8"
            ) from error

        return (
            value,
            terminator + 1,
        )

    @staticmethod
    def _property_name(
        strings: bytes,
        offset: int,
    ) -> str:
        if (
            offset < 0
            or offset >= len(
                strings
            )
        ):
            raise FdtParsingError(
                "FDT property name offset lies outside strings block: "
                f"{offset}"
            )

        terminator = strings.find(
            b"\0",
            offset,
        )

        if terminator < 0:
            raise FdtParsingError(
                "FDT property name is not NUL terminated"
            )

        raw = strings[
            offset:terminator
        ]

        if not raw:
            raise FdtParsingError(
                "FDT property name cannot be empty"
            )

        try:
            return raw.decode(
                "utf-8"
            )
        except UnicodeDecodeError as error:
            raise FdtParsingError(
                "FDT property name is not valid UTF-8"
            ) from error

    @staticmethod
    def _align4(
        value: int,
    ) -> int:
        return (
            value
            + 3
        ) & ~3
