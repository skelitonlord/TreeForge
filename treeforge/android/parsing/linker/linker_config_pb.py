from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.linker.model import (
    AndroidLinkerProtobufContribution,
    AndroidLinkerProtobufUnknownField,
    ParsedAndroidLinkerProtobufConfiguration,
)


class AndroidLinkerProtobufDecodeError(
    ValueError,
):
    """Raised when linker.config.pb contains malformed protobuf wire data."""


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
            raise AndroidLinkerProtobufDecodeError(
                "protobuf varint exceeds supported size"
            )

    raise AndroidLinkerProtobufDecodeError(
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
            raise AndroidLinkerProtobufDecodeError(
                "protobuf field number must be positive"
            )

        if wire_type == 4:
            if (
                nested_field_number
                != field_number
            ):
                raise AndroidLinkerProtobufDecodeError(
                    "mismatched protobuf end-group field"
                )

            return after_key

        position = _skip_value(
            data,
            after_key,
            nested_field_number,
            wire_type,
        )

    raise AndroidLinkerProtobufDecodeError(
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
            raise AndroidLinkerProtobufDecodeError(
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
            raise AndroidLinkerProtobufDecodeError(
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
        raise AndroidLinkerProtobufDecodeError(
            "unexpected protobuf end-group field"
        )

    if wire_type == 5:
        position = offset + 4

        if position > len(
            data
        ):
            raise AndroidLinkerProtobufDecodeError(
                "truncated fixed32 protobuf field"
            )

        return position

    raise AndroidLinkerProtobufDecodeError(
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
        raise AndroidLinkerProtobufDecodeError(
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
            raise AndroidLinkerProtobufDecodeError(
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
            raise AndroidLinkerProtobufDecodeError(
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
        raise AndroidLinkerProtobufDecodeError(
            "unexpected protobuf end-group field"
        )

    elif wire_type == 5:
        end = position + 4

        if end > len(
            data
        ):
            raise AndroidLinkerProtobufDecodeError(
                "truncated fixed32 protobuf field"
            )

        value = data[
            position:end
        ]
        position = end

    else:
        raise AndroidLinkerProtobufDecodeError(
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
        raise AndroidLinkerProtobufDecodeError(
            f"{field_name} must use protobuf "
            "length-delimited encoding"
        )

    try:
        return value.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise AndroidLinkerProtobufDecodeError(
            f"{field_name} contains invalid UTF-8"
        ) from error


def _unknown_field(
    record: _WireRecord,
) -> AndroidLinkerProtobufUnknownField:
    return AndroidLinkerProtobufUnknownField(
        field_number=record.field_number,
        wire_type=record.wire_type,
        raw=record.raw,
    )


def _decode_contribution(
    raw: bytes,
) -> AndroidLinkerProtobufContribution:
    namespace = ""
    paths: list[
        str
    ] = []

    unknown_fields: list[
        AndroidLinkerProtobufUnknownField
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
            namespace = _decode_string(
                record.value,
                field_name=(
                    "LinkerConfig.Contribution.namespace"
                ),
            )

        elif (
            record.field_number == 2
            and record.wire_type == 2
        ):
            paths.append(
                _decode_string(
                    record.value,
                    field_name=(
                        "LinkerConfig.Contribution.paths"
                    ),
                )
            )

        else:
            unknown_fields.append(
                _unknown_field(
                    record
                )
            )

    return AndroidLinkerProtobufContribution(
        namespace=namespace,
        paths=tuple(
            paths
        ),
        unknown_fields=tuple(
            unknown_fields
        ),
        raw=raw,
    )


def _decode_payload(
    raw: bytes,
) -> dict[str, object]:
    if not isinstance(
        raw,
        bytes,
    ):
        raise TypeError(
            "raw must be bytes"
        )

    permitted_paths: list[
        str
    ] = []

    provide_libs: list[
        str
    ] = []

    require_libs: list[
        str
    ] = []

    contributions: list[
        AndroidLinkerProtobufContribution
    ] = []

    unknown_fields: list[
        AndroidLinkerProtobufUnknownField
    ] = []

    visible = False
    visible_present = False

    position = 0

    while position < len(
        raw
    ):
        record, position = _read_record(
            raw,
            position,
        )

        if record.field_number == 1:
            if record.wire_type != 2:
                raise AndroidLinkerProtobufDecodeError(
                    "LinkerConfig.permittedPaths must use "
                    "length-delimited encoding"
                )

            permitted_paths.append(
                _decode_string(
                    record.value,
                    field_name=(
                        "LinkerConfig.permittedPaths"
                    ),
                )
            )

        elif record.field_number == 2:
            if (
                record.wire_type != 0
                or not isinstance(
                    record.value,
                    int,
                )
            ):
                raise AndroidLinkerProtobufDecodeError(
                    "LinkerConfig.visible must use "
                    "varint encoding"
                )

            visible = bool(
                record.value
            )
            visible_present = True

        elif record.field_number == 3:
            if record.wire_type != 2:
                raise AndroidLinkerProtobufDecodeError(
                    "LinkerConfig.provideLibs must use "
                    "length-delimited encoding"
                )

            provide_libs.append(
                _decode_string(
                    record.value,
                    field_name=(
                        "LinkerConfig.provideLibs"
                    ),
                )
            )

        elif record.field_number == 4:
            if record.wire_type != 2:
                raise AndroidLinkerProtobufDecodeError(
                    "LinkerConfig.requireLibs must use "
                    "length-delimited encoding"
                )

            require_libs.append(
                _decode_string(
                    record.value,
                    field_name=(
                        "LinkerConfig.requireLibs"
                    ),
                )
            )

        elif record.field_number == 5:
            if (
                record.wire_type != 2
                or not isinstance(
                    record.value,
                    bytes,
                )
            ):
                raise AndroidLinkerProtobufDecodeError(
                    "LinkerConfig.contributions must use "
                    "length-delimited encoding"
                )

            contributions.append(
                _decode_contribution(
                    record.value
                )
            )

        else:
            unknown_fields.append(
                _unknown_field(
                    record
                )
            )

    return {
        "permitted_paths": tuple(
            permitted_paths
        ),
        "visible": visible,
        "visible_present": visible_present,
        "provide_libs": tuple(
            provide_libs
        ),
        "require_libs": tuple(
            require_libs
        ),
        "contributions": tuple(
            contributions
        ),
        "unknown_fields": tuple(
            unknown_fields
        ),
    }


class AndroidLinkerConfigProtobufParser:
    """
    Decode Android linker.config.pb using its generic protobuf contract.

    This implementation is intentionally independent of generated protobuf
    bindings, protoc, AOSP source availability, device identity, and Android
    version knowledge.

    Parsing preserves unsupported future fields as exact wire records.
    """

    def parse(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidLinkerProtobufConfiguration:
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
            .LINKER_CONFIGURATION
        ):
            raise ValueError(
                "source must be a linker configuration source"
            )

        if (
            source.android_path.name
            != "linker.config.pb"
        ):
            raise ValueError(
                "source must identify linker.config.pb"
            )

        path = source.host_path

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"linker protobuf source is not a file: {path}"
            )

        raw = path.read_bytes()

        decoded = _decode_payload(
            raw
        )

        return ParsedAndroidLinkerProtobufConfiguration(
            source=source,
            raw=raw,
            permitted_paths=decoded[
                "permitted_paths"
            ],
            visible=decoded[
                "visible"
            ],
            visible_present=decoded[
                "visible_present"
            ],
            provide_libs=decoded[
                "provide_libs"
            ],
            require_libs=decoded[
                "require_libs"
            ],
            contributions=decoded[
                "contributions"
            ],
            unknown_fields=decoded[
                "unknown_fields"
            ],
        )

    def parse_sources(
        self,
        sources: tuple[
            AndroidModelSource,
            ...,
        ],
    ) -> tuple[
        ParsedAndroidLinkerProtobufConfiguration,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                AndroidModelSource,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only AndroidModelSource entries"
            )

        protobuf_sources = tuple(
            source
            for source in sources
            if (
                source.kind
                is AndroidModelSourceKind
                .LINKER_CONFIGURATION
                and source.android_path.name
                == "linker.config.pb"
            )
        )

        parsed = tuple(
            self.parse(
                source
            )
            for source in protobuf_sources
        )

        expected_source_ids = {
            id(source)
            for source
            in protobuf_sources
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
            raise AndroidLinkerProtobufDecodeError(
                "linker.config.pb Parsing failed to conserve the "
                "complete selected canonical source population"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed
        ):
            raise AndroidLinkerProtobufDecodeError(
                "linker.config.pb Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return tuple(
            sorted(
                parsed,
                key=lambda item: (
                    item.source.source_name,
                    item.source.android_path.as_posix(),
                ),
            )
        )
