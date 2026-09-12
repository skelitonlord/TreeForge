from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.classpath.model import (
    AndroidClasspathJar,
    AndroidClasspathParsingResult,
    AndroidClasspathProtobufUnknownField,
    ParsedAndroidClasspathConfiguration,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


class AndroidClasspathProtobufDecodeError(
    ValueError,
):
    """
    Raised when classpaths.proto data contains malformed protobuf wire data.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class _WireRecord:
    field_number: int
    wire_type: int
    value: int | bytes | None
    raw: bytes


def _read_varint(
    data: bytes,
    offset: int,
) -> tuple[
    int,
    int,
]:
    value = 0
    shift = 0
    position = offset

    while position < len(
        data
    ):
        byte = data[
            position
        ]
        position += 1

        value |= (
            byte & 0x7F
        ) << shift

        if not (
            byte & 0x80
        ):
            return (
                value,
                position,
            )

        shift += 7

        if shift >= 70:
            raise AndroidClasspathProtobufDecodeError(
                "protobuf varint exceeds supported size"
            )

    raise AndroidClasspathProtobufDecodeError(
        "truncated protobuf varint"
    )


def _skip_group(
    data: bytes,
    offset: int,
    field_number: int,
) -> int:
    position = offset

    while position < len(
        data
    ):
        key, after_key = _read_varint(
            data,
            position,
        )

        nested_field_number = (
            key >> 3
        )
        wire_type = (
            key & 0x07
        )

        if nested_field_number < 1:
            raise AndroidClasspathProtobufDecodeError(
                "protobuf field number must be positive"
            )

        if wire_type == 4:
            if (
                nested_field_number
                != field_number
            ):
                raise AndroidClasspathProtobufDecodeError(
                    "mismatched protobuf end-group field"
                )

            return after_key

        position = _skip_value(
            data,
            after_key,
            nested_field_number,
            wire_type,
        )

    raise AndroidClasspathProtobufDecodeError(
        "unterminated protobuf group"
    )


def _skip_value(
    data: bytes,
    offset: int,
    field_number: int,
    wire_type: int,
) -> int:
    if wire_type == 0:
        _, position = _read_varint(
            data,
            offset,
        )

        return position

    if wire_type == 1:
        position = offset + 8

        if position > len(
            data
        ):
            raise AndroidClasspathProtobufDecodeError(
                "truncated fixed64 protobuf field"
            )

        return position

    if wire_type == 2:
        size, position = _read_varint(
            data,
            offset,
        )

        end = position + size

        if end > len(
            data
        ):
            raise AndroidClasspathProtobufDecodeError(
                "truncated length-delimited protobuf field"
            )

        return end

    if wire_type == 3:
        return _skip_group(
            data,
            offset,
            field_number,
        )

    if wire_type == 4:
        raise AndroidClasspathProtobufDecodeError(
            "unexpected protobuf end-group field"
        )

    if wire_type == 5:
        position = offset + 4

        if position > len(
            data
        ):
            raise AndroidClasspathProtobufDecodeError(
                "truncated fixed32 protobuf field"
            )

        return position

    raise AndroidClasspathProtobufDecodeError(
        f"unsupported protobuf wire type: {wire_type}"
    )


def _read_record(
    data: bytes,
    offset: int,
) -> tuple[
    _WireRecord,
    int,
]:
    start = offset

    key, position = _read_varint(
        data,
        offset,
    )

    field_number = (
        key >> 3
    )
    wire_type = (
        key & 0x07
    )

    if field_number < 1:
        raise AndroidClasspathProtobufDecodeError(
            "protobuf field number must be positive"
        )

    value: int | bytes | None

    if wire_type == 0:
        value, position = _read_varint(
            data,
            position,
        )

    elif wire_type == 1:
        end = position + 8

        if end > len(
            data
        ):
            raise AndroidClasspathProtobufDecodeError(
                "truncated fixed64 protobuf field"
            )

        value = data[
            position:end
        ]
        position = end

    elif wire_type == 2:
        size, position = _read_varint(
            data,
            position,
        )

        end = position + size

        if end > len(
            data
        ):
            raise AndroidClasspathProtobufDecodeError(
                "truncated length-delimited protobuf field"
            )

        value = data[
            position:end
        ]
        position = end

    elif wire_type == 3:
        position = _skip_group(
            data,
            position,
            field_number,
        )
        value = None

    elif wire_type == 4:
        raise AndroidClasspathProtobufDecodeError(
            "unexpected protobuf end-group field"
        )

    elif wire_type == 5:
        end = position + 4

        if end > len(
            data
        ):
            raise AndroidClasspathProtobufDecodeError(
                "truncated fixed32 protobuf field"
            )

        value = data[
            position:end
        ]
        position = end

    else:
        raise AndroidClasspathProtobufDecodeError(
            f"unsupported protobuf wire type: {wire_type}"
        )

    return (
        _WireRecord(
            field_number=field_number,
            wire_type=wire_type,
            value=value,
            raw=data[
                start:position
            ],
        ),
        position,
    )


def _decode_string(
    value: int | bytes | None,
    *,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        bytes,
    ):
        raise AndroidClasspathProtobufDecodeError(
            f"{field_name} must use protobuf "
            "length-delimited encoding"
        )

    try:
        return value.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise AndroidClasspathProtobufDecodeError(
            f"{field_name} contains invalid UTF-8"
        ) from error


def _unknown_field(
    record: _WireRecord,
) -> AndroidClasspathProtobufUnknownField:
    return AndroidClasspathProtobufUnknownField(
        field_number=record.field_number,
        wire_type=record.wire_type,
        raw=record.raw,
    )


class AndroidClasspathProtobufParser:
    """
    Literal decoder for packages/modules/common/proto/classpaths.proto.

    Parsing records each fragment independently and preserves wire presence,
    source order, and unknown fields. It does not merge fragments or evaluate
    API-level applicability.
    """

    def decode(
        self,
        raw: bytes,
    ) -> tuple[
        tuple[
            AndroidClasspathJar,
            ...,
        ],
        tuple[
            AndroidClasspathProtobufUnknownField,
            ...,
        ],
    ]:
        if not isinstance(
            raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        jars: list[
            AndroidClasspathJar
        ] = []

        unknown_fields: list[
            AndroidClasspathProtobufUnknownField
        ] = []

        position = 0

        while position < len(
            raw
        ):
            record, position = _read_record(
                raw,
                position,
            )

            if (
                record.field_number == 1
                and record.wire_type == 2
                and isinstance(
                    record.value,
                    bytes,
                )
            ):
                jars.append(
                    self._decode_jar(
                        record.value
                    )
                )

            else:
                unknown_fields.append(
                    _unknown_field(
                        record
                    )
                )

        return (
            tuple(
                jars
            ),
            tuple(
                unknown_fields
            ),
        )

    def _decode_jar(
        self,
        raw: bytes,
    ) -> AndroidClasspathJar:
        path = ""
        path_present = False

        classpath_value = 0
        classpath_present = False

        min_sdk_version = ""
        min_sdk_version_present = False

        max_sdk_version = ""
        max_sdk_version_present = False

        unknown_fields: list[
            AndroidClasspathProtobufUnknownField
        ] = []

        position = 0

        while position < len(
            raw
        ):
            record, position = _read_record(
                raw,
                position,
            )

            if (
                record.field_number == 1
                and record.wire_type == 2
            ):
                path = _decode_string(
                    record.value,
                    field_name="Jar.path",
                )
                path_present = True

            elif (
                record.field_number == 2
                and record.wire_type == 0
                and isinstance(
                    record.value,
                    int,
                )
            ):
                classpath_value = (
                    record.value
                )
                classpath_present = True

            elif (
                record.field_number == 3
                and record.wire_type == 2
            ):
                min_sdk_version = _decode_string(
                    record.value,
                    field_name=(
                        "Jar.min_sdk_version"
                    ),
                )
                min_sdk_version_present = True

            elif (
                record.field_number == 4
                and record.wire_type == 2
            ):
                max_sdk_version = _decode_string(
                    record.value,
                    field_name=(
                        "Jar.max_sdk_version"
                    ),
                )
                max_sdk_version_present = True

            else:
                unknown_fields.append(
                    _unknown_field(
                        record
                    )
                )

        return AndroidClasspathJar(
            path=path,
            path_present=path_present,
            classpath_value=classpath_value,
            classpath_present=classpath_present,
            min_sdk_version=min_sdk_version,
            min_sdk_version_present=(
                min_sdk_version_present
            ),
            max_sdk_version=max_sdk_version,
            max_sdk_version_present=(
                max_sdk_version_present
            ),
            unknown_fields=tuple(
                unknown_fields
            ),
        )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidClasspathConfiguration:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            source.kind
            is not AndroidModelSourceKind
            .CLASSPATH_CONFIGURATION
        ):
            raise ValueError(
                "source must be a classpath configuration source"
            )

        raw = source.host_path.read_bytes()

        jars, unknown_fields = self.decode(
            raw
        )

        return ParsedAndroidClasspathConfiguration(
            source=source,
            raw=raw,
            jars=jars,
            unknown_fields=unknown_fields,
        )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidClasspathParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source
            in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .CLASSPATH_CONFIGURATION
            )
        )

        parsed = tuple(
            self.parse_source(
                source
            )
            for source
            in sources
        )

        expected_source_ids = {
            id(source)
            for source
            in sources
        }

        actual_source_ids = {
            id(value.source)
            for value
            in parsed
        }

        if (
            expected_source_ids
            != actual_source_ids
        ):
            raise AndroidClasspathProtobufDecodeError(
                "classpath Parsing failed to conserve the complete "
                "canonical CLASSPATH_CONFIGURATION source population"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed
        ):
            raise AndroidClasspathProtobufDecodeError(
                "classpath Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return AndroidClasspathParsingResult(
            configurations=tuple(
                sorted(
                    parsed,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            )
        )
