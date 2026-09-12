from __future__ import annotations

from dataclasses import dataclass
from struct import unpack_from


class AndroidBinaryXmlError(
    ValueError,
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBinaryXmlAttribute:
    namespace: str | None
    name: str
    raw_string: str | None
    data_type: int
    data: int
    literal: str | int | bool | None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBinaryXmlElement:
    name: str
    namespace: str | None
    attributes: tuple[
        AndroidBinaryXmlAttribute,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBinaryXmlDocument:
    elements: tuple[
        AndroidBinaryXmlElement,
        ...,
    ]


class AndroidBinaryXmlParser:
    """
    Minimal generic Android binary-XML decoder.

    This decoder intentionally handles only structure required to recover
    literal element and attribute identity. It does not resolve resources.arsc
    references or reinterpret resource IDs.
    """

    RES_XML_TYPE = 0x0003
    RES_STRING_POOL_TYPE = 0x0001
    RES_XML_START_ELEMENT_TYPE = 0x0102

    UTF8_FLAG = 0x00000100

    TYPE_REFERENCE = 0x01
    TYPE_STRING = 0x03
    TYPE_INT_DEC = 0x10
    TYPE_INT_HEX = 0x11
    TYPE_INT_BOOLEAN = 0x12

    NO_INDEX = 0xFFFFFFFF

    def parse(
        self,
        payload: bytes,
    ) -> AndroidBinaryXmlDocument:
        if not isinstance(
            payload,
            bytes,
        ):
            raise TypeError(
                "payload must be bytes"
            )

        if len(
            payload
        ) < 8:
            raise AndroidBinaryXmlError(
                "binary XML payload is truncated"
            )

        chunk_type = self._u16(
            payload,
            0,
        )
        header_size = self._u16(
            payload,
            2,
        )
        total_size = self._u32(
            payload,
            4,
        )

        if chunk_type != self.RES_XML_TYPE:
            raise AndroidBinaryXmlError(
                "payload is not Android binary XML"
            )

        if (
            header_size < 8
            or total_size > len(
                payload
            )
            or total_size < header_size
        ):
            raise AndroidBinaryXmlError(
                "invalid binary XML root chunk"
            )

        strings: tuple[
            str,
            ...,
        ] | None = None

        elements = []

        offset = header_size

        while offset < total_size:
            if offset + 8 > total_size:
                raise AndroidBinaryXmlError(
                    "truncated binary XML chunk header"
                )

            current_type = self._u16(
                payload,
                offset,
            )
            current_header_size = self._u16(
                payload,
                offset + 2,
            )
            current_size = self._u32(
                payload,
                offset + 4,
            )

            if (
                current_header_size < 8
                or current_size < current_header_size
                or offset + current_size > total_size
            ):
                raise AndroidBinaryXmlError(
                    "invalid binary XML child chunk"
                )

            if (
                current_type
                == self.RES_STRING_POOL_TYPE
            ):
                strings = self._parse_string_pool(
                    payload,
                    offset,
                    current_size,
                )

            elif (
                current_type
                == self.RES_XML_START_ELEMENT_TYPE
            ):
                if strings is None:
                    raise AndroidBinaryXmlError(
                        "start element precedes string pool"
                    )

                elements.append(
                    self._parse_start_element(
                        payload,
                        offset,
                        current_size,
                        strings,
                    )
                )

            offset += current_size

        if strings is None:
            raise AndroidBinaryXmlError(
                "binary XML contains no string pool"
            )

        if not elements:
            raise AndroidBinaryXmlError(
                "binary XML contains no start elements"
            )

        return AndroidBinaryXmlDocument(
            elements=tuple(
                elements
            )
        )

    def _parse_string_pool(
        self,
        payload: bytes,
        offset: int,
        chunk_size: int,
    ) -> tuple[
        str,
        ...,
    ]:
        header_size = self._u16(
            payload,
            offset + 2,
        )

        if header_size < 28:
            raise AndroidBinaryXmlError(
                "invalid Android string-pool header"
            )

        string_count = self._u32(
            payload,
            offset + 8,
        )
        style_count = self._u32(
            payload,
            offset + 12,
        )
        flags = self._u32(
            payload,
            offset + 16,
        )
        strings_start = self._u32(
            payload,
            offset + 20,
        )
        styles_start = self._u32(
            payload,
            offset + 24,
        )

        offsets_start = (
            offset
            + header_size
        )

        offset_table_size = (
            string_count
            * 4
        )

        style_table_size = (
            style_count
            * 4
        )

        if (
            offsets_start
            + offset_table_size
            + style_table_size
            > offset
            + chunk_size
        ):
            raise AndroidBinaryXmlError(
                "truncated Android string-pool offsets"
            )

        strings_base = (
            offset
            + strings_start
        )

        string_offsets = tuple(
            self._u32(
                payload,
                offsets_start
                + index * 4,
            )
            for index
            in range(
                string_count
            )
        )

        is_utf8 = bool(
            flags
            & self.UTF8_FLAG
        )

        decoded = []

        for relative_offset in string_offsets:
            string_offset = (
                strings_base
                + relative_offset
            )

            if (
                string_offset < offset
                or string_offset >= (
                    offset
                    + chunk_size
                )
            ):
                raise AndroidBinaryXmlError(
                    "invalid Android string offset"
                )

            if is_utf8:
                value = self._decode_utf8_string(
                    payload,
                    string_offset,
                    offset + chunk_size,
                )
            else:
                value = self._decode_utf16_string(
                    payload,
                    string_offset,
                    offset + chunk_size,
                )

            decoded.append(
                value
            )

        return tuple(
            decoded
        )

    def _decode_utf8_string(
        self,
        payload: bytes,
        offset: int,
        limit: int,
    ) -> str:
        _, offset = self._read_length8(
            payload,
            offset,
            limit,
        )

        byte_length, offset = self._read_length8(
            payload,
            offset,
            limit,
        )

        end = (
            offset
            + byte_length
        )

        if end > limit:
            raise AndroidBinaryXmlError(
                "truncated UTF-8 Android string"
            )

        raw = payload[
            offset:end
        ]

        try:
            return raw.decode(
                "utf-8"
            )
        except UnicodeDecodeError as error:
            raise AndroidBinaryXmlError(
                "invalid UTF-8 Android string"
            ) from error

    def _decode_utf16_string(
        self,
        payload: bytes,
        offset: int,
        limit: int,
    ) -> str:
        code_unit_length, offset = self._read_length16(
            payload,
            offset,
            limit,
        )

        byte_length = (
            code_unit_length
            * 2
        )

        end = (
            offset
            + byte_length
        )

        if end > limit:
            raise AndroidBinaryXmlError(
                "truncated UTF-16 Android string"
            )

        raw = payload[
            offset:end
        ]

        try:
            return raw.decode(
                "utf-16le"
            )
        except UnicodeDecodeError as error:
            raise AndroidBinaryXmlError(
                "invalid UTF-16 Android string"
            ) from error

    def _parse_start_element(
        self,
        payload: bytes,
        offset: int,
        chunk_size: int,
        strings: tuple[
            str,
            ...,
        ],
    ) -> AndroidBinaryXmlElement:
        header_size = self._u16(
            payload,
            offset + 2,
        )

        # ResXMLTree_node is 16 bytes and ResXMLTree_attrExt
        # follows immediately.
        if header_size < 16:
            raise AndroidBinaryXmlError(
                "invalid start-element node header"
            )

        ext_offset = (
            offset
            + header_size
        )

        if ext_offset + 20 > offset + chunk_size:
            raise AndroidBinaryXmlError(
                "truncated start-element extension"
            )

        namespace_index = self._u32(
            payload,
            ext_offset,
        )
        name_index = self._u32(
            payload,
            ext_offset + 4,
        )
        attribute_start = self._u16(
            payload,
            ext_offset + 8,
        )
        attribute_size = self._u16(
            payload,
            ext_offset + 10,
        )
        attribute_count = self._u16(
            payload,
            ext_offset + 12,
        )

        if attribute_size < 20:
            raise AndroidBinaryXmlError(
                "invalid Android XML attribute size"
            )

        name = self._string(
            strings,
            name_index,
        )

        namespace = self._optional_string(
            strings,
            namespace_index,
        )

        attributes_offset = (
            ext_offset
            + attribute_start
        )

        attributes = []

        for index in range(
            attribute_count
        ):
            attribute_offset = (
                attributes_offset
                + index
                * attribute_size
            )

            if (
                attribute_offset
                + 20
                > offset
                + chunk_size
            ):
                raise AndroidBinaryXmlError(
                    "truncated Android XML attribute"
                )

            attr_namespace_index = self._u32(
                payload,
                attribute_offset,
            )
            attr_name_index = self._u32(
                payload,
                attribute_offset + 4,
            )
            raw_value_index = self._u32(
                payload,
                attribute_offset + 8,
            )

            typed_size = self._u16(
                payload,
                attribute_offset + 12,
            )

            if typed_size < 8:
                raise AndroidBinaryXmlError(
                    "invalid Android typed value"
                )

            data_type = payload[
                attribute_offset + 15
            ]

            data = self._u32(
                payload,
                attribute_offset + 16,
            )

            raw_string = self._optional_string(
                strings,
                raw_value_index,
            )

            literal = self._literal_value(
                strings=strings,
                raw_string=raw_string,
                data_type=data_type,
                data=data,
            )

            attributes.append(
                AndroidBinaryXmlAttribute(
                    namespace=self._optional_string(
                        strings,
                        attr_namespace_index,
                    ),
                    name=self._string(
                        strings,
                        attr_name_index,
                    ),
                    raw_string=raw_string,
                    data_type=data_type,
                    data=data,
                    literal=literal,
                )
            )

        return AndroidBinaryXmlElement(
            name=name,
            namespace=namespace,
            attributes=tuple(
                attributes
            ),
        )

    def _literal_value(
        self,
        *,
        strings: tuple[
            str,
            ...,
        ],
        raw_string: str | None,
        data_type: int,
        data: int,
    ) -> str | int | bool | None:
        if raw_string is not None:
            return raw_string

        if data_type == self.TYPE_STRING:
            return self._string(
                strings,
                data,
            )

        if data_type in {
            self.TYPE_INT_DEC,
            self.TYPE_INT_HEX,
        }:
            return data

        if data_type == self.TYPE_INT_BOOLEAN:
            return bool(
                data
            )

        # Resource references and other Android typed values are
        # intentionally retained only as type/data metadata.
        return None

    def _read_length8(
        self,
        payload: bytes,
        offset: int,
        limit: int,
    ) -> tuple[
        int,
        int,
    ]:
        if offset >= limit:
            raise AndroidBinaryXmlError(
                "truncated Android UTF-8 length"
            )

        first = payload[
            offset
        ]
        offset += 1

        if first & 0x80:
            if offset >= limit:
                raise AndroidBinaryXmlError(
                    "truncated Android UTF-8 length"
                )

            second = payload[
                offset
            ]
            offset += 1

            return (
                (
                    (
                        first
                        & 0x7F
                    )
                    << 8
                )
                | second,
                offset,
            )

        return (
            first,
            offset,
        )

    def _read_length16(
        self,
        payload: bytes,
        offset: int,
        limit: int,
    ) -> tuple[
        int,
        int,
    ]:
        if offset + 2 > limit:
            raise AndroidBinaryXmlError(
                "truncated Android UTF-16 length"
            )

        first = self._u16(
            payload,
            offset,
        )
        offset += 2

        if first & 0x8000:
            if offset + 2 > limit:
                raise AndroidBinaryXmlError(
                    "truncated Android UTF-16 length"
                )

            second = self._u16(
                payload,
                offset,
            )
            offset += 2

            return (
                (
                    (
                        first
                        & 0x7FFF
                    )
                    << 16
                )
                | second,
                offset,
            )

        return (
            first,
            offset,
        )

    def _optional_string(
        self,
        strings: tuple[
            str,
            ...,
        ],
        index: int,
    ) -> str | None:
        if index == self.NO_INDEX:
            return None

        return self._string(
            strings,
            index,
        )

    @staticmethod
    def _string(
        strings: tuple[
            str,
            ...,
        ],
        index: int,
    ) -> str:
        if (
            index < 0
            or index >= len(
                strings
            )
        ):
            raise AndroidBinaryXmlError(
                "Android XML string index is out of range"
            )

        return strings[
            index
        ]

    @staticmethod
    def _u16(
        payload: bytes,
        offset: int,
    ) -> int:
        try:
            return unpack_from(
                "<H",
                payload,
                offset,
            )[0]
        except Exception as error:
            raise AndroidBinaryXmlError(
                "truncated 16-bit Android XML value"
            ) from error

    @staticmethod
    def _u32(
        payload: bytes,
        offset: int,
    ) -> int:
        try:
            return unpack_from(
                "<I",
                payload,
                offset,
            )[0]
        except Exception as error:
            raise AndroidBinaryXmlError(
                "truncated 32-bit Android XML value"
            ) from error
