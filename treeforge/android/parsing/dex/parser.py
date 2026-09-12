from __future__ import annotations

import struct

from treeforge.android.parsing.dex.model import (
    AndroidDexClass,
    AndroidDexEndianEncoding,
    AndroidDexHeader,
    AndroidDexSource,
    AndroidDexString,
    AndroidDexType,
    ParsedAndroidDex,
)


class AndroidDexParsingError(
    ValueError
):
    """
    Raised when positively identified DEX bytes cannot be represented
    faithfully.
    """


class AndroidDexParser:
    """
    Decode literal standard DEX header structure from canonical DEX bytes.

    The parser is intentionally container-agnostic. APK, JAR, OAT, VDEX, or
    standalone source discovery remains with the owning container parser.
    """

    STANDARD_HEADER_SIZE = 0x70

    REVERSE_ENDIAN_CONSTANT = 0x78563412
    ENDIAN_CONSTANT = 0x12345678

    NO_INDEX = 0xFFFFFFFF

    @staticmethod
    def _checked_end(
        *,
        offset: int,
        size: int,
        payload_size: int,
        label: str,
    ) -> int:
        if (
            offset < 0
            or size < 0
        ):
            raise AndroidDexParsingError(
                f"{label} contains a negative range"
            )

        end = offset + size

        if (
            offset > payload_size
            or end > payload_size
        ):
            raise AndroidDexParsingError(
                f"{label} exceeds supplied DEX payload"
            )

        return end

    @classmethod
    def _validate_table(
        cls,
        *,
        offset: int,
        count: int,
        item_size: int,
        alignment: int,
        payload_size: int,
        label: str,
    ) -> None:
        if count == 0:
            if offset != 0:
                raise AndroidDexParsingError(
                    f"{label} has zero count with nonzero offset"
                )

            return

        if offset == 0:
            raise AndroidDexParsingError(
                f"{label} has nonzero count with zero offset"
            )

        if offset % alignment != 0:
            raise AndroidDexParsingError(
                f"{label} is not {alignment}-byte aligned"
            )

        cls._checked_end(
            offset=offset,
            size=count * item_size,
            payload_size=payload_size,
            label=label,
        )

    @classmethod
    def _read_uleb128(
        cls,
        payload: bytes,
        offset: int,
    ) -> tuple[
        int,
        int,
    ]:
        value = 0
        shift = 0
        cursor = offset

        for index in range(5):
            if cursor >= len(
                payload
            ):
                raise AndroidDexParsingError(
                    "truncated DEX ULEB128 value"
                )

            byte = payload[
                cursor
            ]
            cursor += 1

            value |= (
                byte & 0x7F
            ) << shift

            if (
                byte & 0x80
            ) == 0:
                if (
                    index == 4
                    and byte > 0x0F
                ):
                    raise AndroidDexParsingError(
                        "DEX ULEB128 value exceeds 32 bits"
                    )

                return (
                    value,
                    cursor,
                )

            shift += 7

        raise AndroidDexParsingError(
            "DEX ULEB128 value exceeds five bytes"
        )

    @classmethod
    def _decode_mutf8(
        cls,
        *,
        payload: bytes,
        data_offset: int,
    ) -> tuple[
        int,
        tuple[
            int,
            ...,
        ],
        str,
    ]:
        declared_utf16_size, cursor = (
            cls._read_uleb128(
                payload,
                data_offset,
            )
        )

        code_units: list[
            int
        ] = []

        while True:
            if cursor >= len(
                payload
            ):
                raise AndroidDexParsingError(
                    "unterminated DEX MUTF-8 string"
                )

            first = payload[
                cursor
            ]

            if first == 0:
                cursor += 1
                break

            if first <= 0x7F:
                code_units.append(
                    first
                )
                cursor += 1
                continue

            if (
                first & 0xE0
            ) == 0xC0:
                if (
                    cursor + 1
                    >= len(
                        payload
                    )
                ):
                    raise AndroidDexParsingError(
                        "truncated two-byte DEX MUTF-8 sequence"
                    )

                second = payload[
                    cursor + 1
                ]

                if (
                    second & 0xC0
                ) != 0x80:
                    raise AndroidDexParsingError(
                        "invalid DEX MUTF-8 continuation byte"
                    )

                value = (
                    (
                        first & 0x1F
                    )
                    << 6
                ) | (
                    second & 0x3F
                )

                if value == 0:
                    if (
                        first != 0xC0
                        or second != 0x80
                    ):
                        raise AndroidDexParsingError(
                            "invalid DEX MUTF-8 NUL encoding"
                        )
                elif value < 0x80:
                    raise AndroidDexParsingError(
                        "overlong two-byte DEX MUTF-8 sequence"
                    )

                code_units.append(
                    value
                )
                cursor += 2
                continue

            if (
                first & 0xF0
            ) == 0xE0:
                if (
                    cursor + 2
                    >= len(
                        payload
                    )
                ):
                    raise AndroidDexParsingError(
                        "truncated three-byte DEX MUTF-8 sequence"
                    )

                second = payload[
                    cursor + 1
                ]
                third = payload[
                    cursor + 2
                ]

                if (
                    (
                        second & 0xC0
                    )
                    != 0x80
                    or (
                        third & 0xC0
                    )
                    != 0x80
                ):
                    raise AndroidDexParsingError(
                        "invalid DEX MUTF-8 continuation byte"
                    )

                value = (
                    (
                        first & 0x0F
                    )
                    << 12
                ) | (
                    (
                        second & 0x3F
                    )
                    << 6
                ) | (
                    third & 0x3F
                )

                if value < 0x800:
                    raise AndroidDexParsingError(
                        "overlong three-byte DEX MUTF-8 sequence"
                    )

                code_units.append(
                    value
                )
                cursor += 3
                continue

            raise AndroidDexParsingError(
                "DEX MUTF-8 contains unsupported "
                "four-byte or malformed sequence"
            )

        if (
            len(
                code_units
            )
            != declared_utf16_size
        ):
            raise AndroidDexParsingError(
                "DEX MUTF-8 utf16_size does not match "
                "decoded UTF-16 code-unit count"
            )

        characters: list[
            str
        ] = []

        index = 0

        while index < len(
            code_units
        ):
            code_unit = code_units[
                index
            ]

            if (
                0xD800
                <= code_unit
                <= 0xDBFF
                and index + 1
                < len(
                    code_units
                )
                and 0xDC00
                <= code_units[
                    index + 1
                ]
                <= 0xDFFF
            ):
                low = code_units[
                    index + 1
                ]

                codepoint = (
                    0x10000
                    + (
                        (
                            code_unit
                            - 0xD800
                        )
                        << 10
                    )
                    + (
                        low
                        - 0xDC00
                    )
                )

                characters.append(
                    chr(
                        codepoint
                    )
                )
                index += 2
                continue

            #
            # Java/Dex strings may contain an unpaired surrogate.
            # Preserve the literal UTF-16 code unit rather than silently
            # normalizing or replacing it.
            #
            characters.append(
                chr(
                    code_unit
                )
            )
            index += 1

        return (
            declared_utf16_size,
            tuple(
                code_units
            ),
            "".join(
                characters
            ),
        )

    @classmethod
    def _parse_strings(
        cls,
        *,
        payload: bytes,
        header: AndroidDexHeader,
        byte_order: str,
    ) -> tuple[
        AndroidDexString,
        ...,
    ]:
        cls._validate_table(
            offset=header.string_ids_offset,
            count=header.string_ids_size,
            item_size=4,
            alignment=4,
            payload_size=len(
                payload
            ),
            label="DEX string_ids",
        )

        if (
            header.data_size
            > 0
        ):
            data_end = cls._checked_end(
                offset=header.data_offset,
                size=header.data_size,
                payload_size=len(
                    payload
                ),
                label="DEX data section",
            )
        else:
            data_end = (
                header.data_offset
            )

        strings = []

        for index in range(
            header.string_ids_size
        ):
            data_offset = struct.unpack_from(
                f"{byte_order}I",
                payload,
                (
                    header.string_ids_offset
                    + index * 4
                ),
            )[0]

            if (
                header.data_size == 0
                or data_offset
                < header.data_offset
                or data_offset
                >= data_end
            ):
                raise AndroidDexParsingError(
                    "DEX string_data_item lies outside "
                    "the declared data section"
                )

            (
                utf16_size,
                utf16_code_units,
                value,
            ) = cls._decode_mutf8(
                payload=payload,
                data_offset=data_offset,
            )

            strings.append(
                AndroidDexString(
                    index=index,
                    data_offset=(
                        data_offset
                    ),
                    utf16_size=(
                        utf16_size
                    ),
                    utf16_code_units=(
                        utf16_code_units
                    ),
                    value=value,
                )
            )

        return tuple(
            strings
        )

    @classmethod
    def _parse_types(
        cls,
        *,
        payload: bytes,
        header: AndroidDexHeader,
        byte_order: str,
        strings: tuple[
            AndroidDexString,
            ...,
        ],
    ) -> tuple[
        AndroidDexType,
        ...,
    ]:
        cls._validate_table(
            offset=header.type_ids_offset,
            count=header.type_ids_size,
            item_size=4,
            alignment=4,
            payload_size=len(
                payload
            ),
            label="DEX type_ids",
        )

        types = []

        for index in range(
            header.type_ids_size
        ):
            descriptor_index = (
                struct.unpack_from(
                    f"{byte_order}I",
                    payload,
                    (
                        header.type_ids_offset
                        + index * 4
                    ),
                )[0]
            )

            if (
                descriptor_index
                >= len(
                    strings
                )
            ):
                raise AndroidDexParsingError(
                    "DEX type descriptor string index "
                    "is out of range"
                )

            types.append(
                AndroidDexType(
                    index=index,
                    descriptor_index=(
                        descriptor_index
                    ),
                    descriptor=strings[
                        descriptor_index
                    ],
                )
            )

        return tuple(
            types
        )

    @classmethod
    def _parse_type_list(
        cls,
        *,
        payload: bytes,
        offset: int,
        byte_order: str,
        types: tuple[
            AndroidDexType,
            ...,
        ],
        header: AndroidDexHeader,
    ) -> tuple[
        tuple[
            int,
            ...,
        ],
        tuple[
            AndroidDexType,
            ...,
        ],
    ]:
        if offset == 0:
            return (
                (),
                (),
            )

        if offset % 4 != 0:
            raise AndroidDexParsingError(
                "DEX type_list is not four-byte aligned"
            )

        if (
            header.data_size == 0
        ):
            raise AndroidDexParsingError(
                "DEX type_list exists without a data section"
            )

        data_end = (
            header.data_offset
            + header.data_size
        )

        if (
            offset < header.data_offset
            or offset >= data_end
        ):
            raise AndroidDexParsingError(
                "DEX type_list lies outside the data section"
            )

        cls._checked_end(
            offset=offset,
            size=4,
            payload_size=len(
                payload
            ),
            label="DEX type_list size",
        )

        size = struct.unpack_from(
            f"{byte_order}I",
            payload,
            offset,
        )[0]

        cls._checked_end(
            offset=offset + 4,
            size=size * 2,
            payload_size=len(
                payload
            ),
            label="DEX type_list entries",
        )

        if (
            offset
            + 4
            + size * 2
            > data_end
        ):
            raise AndroidDexParsingError(
                "DEX type_list exceeds the declared data section"
            )

        indices = []
        resolved = []

        for index in range(
            size
        ):
            type_index = struct.unpack_from(
                f"{byte_order}H",
                payload,
                (
                    offset
                    + 4
                    + index * 2
                ),
            )[0]

            if type_index >= len(
                types
            ):
                raise AndroidDexParsingError(
                    "DEX type_list contains an out-of-range type index"
                )

            indices.append(
                type_index
            )

            resolved.append(
                types[
                    type_index
                ]
            )

        return (
            tuple(
                indices
            ),
            tuple(
                resolved
            ),
        )

    @classmethod
    def _parse_classes(
        cls,
        *,
        payload: bytes,
        header: AndroidDexHeader,
        byte_order: str,
        strings: tuple[
            AndroidDexString,
            ...,
        ],
        types: tuple[
            AndroidDexType,
            ...,
        ],
    ) -> tuple[
        AndroidDexClass,
        ...,
    ]:
        cls._validate_table(
            offset=header.class_defs_offset,
            count=header.class_defs_size,
            item_size=32,
            alignment=4,
            payload_size=len(
                payload
            ),
            label="DEX class_defs",
        )

        classes = []

        for definition_index in range(
            header.class_defs_size
        ):
            (
                class_type_index,
                access_flags,
                superclass_raw,
                interfaces_offset,
                source_file_raw,
                annotations_offset,
                class_data_offset,
                static_values_offset,
            ) = struct.unpack_from(
                f"{byte_order}8I",
                payload,
                (
                    header.class_defs_offset
                    + definition_index * 32
                ),
            )

            if class_type_index >= len(
                types
            ):
                raise AndroidDexParsingError(
                    "DEX class_idx is out of range"
                )

            if (
                superclass_raw
                == cls.NO_INDEX
            ):
                superclass_type_index = (
                    None
                )
                superclass_type = None
            else:
                if superclass_raw >= len(
                    types
                ):
                    raise AndroidDexParsingError(
                        "DEX superclass_idx is out of range"
                    )

                superclass_type_index = (
                    superclass_raw
                )
                superclass_type = types[
                    superclass_raw
                ]

            (
                interface_type_indices,
                interface_types,
            ) = cls._parse_type_list(
                payload=payload,
                offset=interfaces_offset,
                byte_order=byte_order,
                types=types,
                header=header,
            )

            if (
                source_file_raw
                == cls.NO_INDEX
            ):
                source_file_index = None
                source_file = None
            else:
                if source_file_raw >= len(
                    strings
                ):
                    raise AndroidDexParsingError(
                        "DEX source_file_idx is out of range"
                    )

                source_file_index = (
                    source_file_raw
                )
                source_file = strings[
                    source_file_raw
                ]

            for label, value in (
                (
                    "annotations_off",
                    annotations_offset,
                ),
                (
                    "class_data_off",
                    class_data_offset,
                ),
                (
                    "static_values_off",
                    static_values_offset,
                ),
            ):
                if (
                    value != 0
                    and value >= len(
                        payload
                    )
                ):
                    raise AndroidDexParsingError(
                        f"DEX {label} exceeds supplied payload"
                    )

            classes.append(
                AndroidDexClass(
                    definition_index=(
                        definition_index
                    ),
                    class_type_index=(
                        class_type_index
                    ),
                    class_type=types[
                        class_type_index
                    ],
                    access_flags=(
                        access_flags
                    ),
                    superclass_type_index=(
                        superclass_type_index
                    ),
                    superclass_type=(
                        superclass_type
                    ),
                    interfaces_offset=(
                        interfaces_offset
                    ),
                    interface_type_indices=(
                        interface_type_indices
                    ),
                    interface_types=(
                        interface_types
                    ),
                    source_file_index=(
                        source_file_index
                    ),
                    source_file=(
                        source_file
                    ),
                    annotations_offset=(
                        annotations_offset
                    ),
                    class_data_offset=(
                        class_data_offset
                    ),
                    static_values_offset=(
                        static_values_offset
                    ),
                )
            )

        return tuple(
            classes
        )

    def parse(
        self,
        *,
        payload: bytes,
        source: AndroidDexSource,
    ) -> ParsedAndroidDex:
        if not isinstance(
            payload,
            bytes,
        ):
            raise TypeError(
                "payload must be bytes"
            )

        if len(
            payload
        ) < self.STANDARD_HEADER_SIZE:
            raise AndroidDexParsingError(
                "DEX payload is smaller than the standard header"
            )

        if not isinstance(
            source,
            AndroidDexSource,
        ):
            raise TypeError(
                "source must be an AndroidDexSource"
            )

        magic = payload[
            0:8
        ]

        if not magic.startswith(
            b"dex\n"
        ):
            raise AndroidDexParsingError(
                "payload does not contain standard DEX magic"
            )

        if magic[
            7
        ] != 0:
            raise AndroidDexParsingError(
                "DEX magic is not NUL-terminated"
            )

        signature = payload[
            12:32
        ]

        #
        # Determine the byte order from the endian tag itself before
        # interpreting the remainder of the multibyte header.
        #
        # Standard DEX is little-endian. A byte-swapped DEX exposes the
        # reverse-endian constant when the tag bytes are first read in
        # canonical little-endian order.
        #
        canonical_endian_tag = struct.unpack_from(
            "<I",
            payload,
            40,
        )[0]

        if canonical_endian_tag == self.ENDIAN_CONSTANT:
            header_byte_order = "<"
            endian_encoding = AndroidDexEndianEncoding.LITTLE
        elif canonical_endian_tag == self.REVERSE_ENDIAN_CONSTANT:
            header_byte_order = ">"
            endian_encoding = (
                AndroidDexEndianEncoding.REVERSE_BYTE_SWAPPED
            )
        else:
            raise AndroidDexParsingError(
                "DEX contains unsupported endian_tag: "
                f"0x{canonical_endian_tag:08x}"
            )

        checksum = struct.unpack_from(
            f"{header_byte_order}I",
            payload,
            8,
        )[0]

        (
            file_size,
            header_size,
            endian_tag,
            link_size,
            link_offset,
            map_offset,
            string_ids_size,
            string_ids_offset,
            type_ids_size,
            type_ids_offset,
            proto_ids_size,
            proto_ids_offset,
            field_ids_size,
            field_ids_offset,
            method_ids_size,
            method_ids_offset,
            class_defs_size,
            class_defs_offset,
            data_size,
            data_offset,
        ) = struct.unpack_from(
            f"{header_byte_order}20I",
            payload,
            32,
        )

        if header_size < self.STANDARD_HEADER_SIZE:
            raise AndroidDexParsingError(
                "DEX header_size is smaller than the standard header: "
                f"{header_size}"
            )

        if header_size > len(
            payload
        ):
            raise AndroidDexParsingError(
                "DEX header exceeds supplied payload"
            )

        if file_size != len(
            payload
        ):
            raise AndroidDexParsingError(
                "DEX declared file size does not match supplied payload: "
                f"declared={file_size} actual={len(payload)}"
            )

        expected_decoded_endian_tag = self.ENDIAN_CONSTANT

        if endian_tag != expected_decoded_endian_tag:
            raise AndroidDexParsingError(
                "DEX endian decoding did not normalize endian_tag: "
                f"0x{endian_tag:08x}"
            )

        #
        # DEX header tables use a zero size/zero offset convention for
        # absence. Preserve that invariant structurally, without interpreting
        # the contents of any table yet.
        #
        for (
            name,
            size,
            offset,
        ) in (
            (
                "link",
                link_size,
                link_offset,
            ),
            (
                "string_ids",
                string_ids_size,
                string_ids_offset,
            ),
            (
                "type_ids",
                type_ids_size,
                type_ids_offset,
            ),
            (
                "proto_ids",
                proto_ids_size,
                proto_ids_offset,
            ),
            (
                "field_ids",
                field_ids_size,
                field_ids_offset,
            ),
            (
                "method_ids",
                method_ids_size,
                method_ids_offset,
            ),
            (
                "class_defs",
                class_defs_size,
                class_defs_offset,
            ),
            (
                "data",
                data_size,
                data_offset,
            ),
        ):
            if (
                size == 0
                and offset != 0
            ):
                raise AndroidDexParsingError(
                    f"DEX {name} has zero size with nonzero offset"
                )

            if (
                size != 0
                and offset == 0
            ):
                raise AndroidDexParsingError(
                    f"DEX {name} has nonzero size with zero offset"
                )

            if offset > file_size:
                raise AndroidDexParsingError(
                    f"DEX {name} offset exceeds declared file size"
                )

        header = AndroidDexHeader(
            magic=magic,
            checksum=checksum,
            signature=signature,
            file_size=file_size,
            header_size=header_size,
            endian_tag=endian_tag,
            endian_encoding=endian_encoding,
            link_size=link_size,
            link_offset=link_offset,
            map_offset=map_offset,
            string_ids_size=(
                string_ids_size
            ),
            string_ids_offset=(
                string_ids_offset
            ),
            type_ids_size=(
                type_ids_size
            ),
            type_ids_offset=(
                type_ids_offset
            ),
            proto_ids_size=(
                proto_ids_size
            ),
            proto_ids_offset=(
                proto_ids_offset
            ),
            field_ids_size=(
                field_ids_size
            ),
            field_ids_offset=(
                field_ids_offset
            ),
            method_ids_size=(
                method_ids_size
            ),
            method_ids_offset=(
                method_ids_offset
            ),
            class_defs_size=(
                class_defs_size
            ),
            class_defs_offset=(
                class_defs_offset
            ),
            data_size=data_size,
            data_offset=data_offset,
        )

        strings = self._parse_strings(
            payload=payload,
            header=header,
            byte_order=(
                header_byte_order
            ),
        )

        types = self._parse_types(
            payload=payload,
            header=header,
            byte_order=(
                header_byte_order
            ),
            strings=strings,
        )

        classes = self._parse_classes(
            payload=payload,
            header=header,
            byte_order=(
                header_byte_order
            ),
            strings=strings,
            types=types,
        )

        return ParsedAndroidDex(
            source=source,
            payload_size=len(
                payload
            ),
            header=header,
            strings=strings,
            types=types,
            classes=classes,
        )
