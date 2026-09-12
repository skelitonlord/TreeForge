from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.aconfig.model import (
    AndroidAconfigFlagMetadata,
    AndroidAconfigParsedFlag,
    AndroidAconfigParsingResult,
    AndroidAconfigProtobufUnknownField,
    AndroidAconfigTracepoint,
    ParsedAndroidAconfigConfiguration,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


class AndroidAconfigProtobufDecodeError(
    ValueError,
):
    """
    Raised when aconfig_flags.pb contains malformed protobuf wire data.
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
            raise AndroidAconfigProtobufDecodeError(
                "protobuf varint exceeds supported size"
            )

    raise AndroidAconfigProtobufDecodeError(
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
            raise AndroidAconfigProtobufDecodeError(
                "protobuf field number must be positive"
            )

        if wire_type == 4:
            if (
                nested_field_number
                != field_number
            ):
                raise AndroidAconfigProtobufDecodeError(
                    "mismatched protobuf end-group field"
                )

            return after_key

        position = _skip_value(
            data,
            after_key,
            nested_field_number,
            wire_type,
        )

    raise AndroidAconfigProtobufDecodeError(
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
            raise AndroidAconfigProtobufDecodeError(
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
            raise AndroidAconfigProtobufDecodeError(
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
        raise AndroidAconfigProtobufDecodeError(
            "unexpected protobuf end-group field"
        )

    if wire_type == 5:
        position = offset + 4

        if position > len(
            data
        ):
            raise AndroidAconfigProtobufDecodeError(
                "truncated fixed32 protobuf field"
            )

        return position

    raise AndroidAconfigProtobufDecodeError(
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
        raise AndroidAconfigProtobufDecodeError(
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
            raise AndroidAconfigProtobufDecodeError(
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
            raise AndroidAconfigProtobufDecodeError(
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
        raise AndroidAconfigProtobufDecodeError(
            "unexpected protobuf end-group field"
        )

    elif wire_type == 5:
        end = position + 4

        if end > len(
            data
        ):
            raise AndroidAconfigProtobufDecodeError(
                "truncated fixed32 protobuf field"
            )

        value = data[
            position:end
        ]
        position = end

    else:
        raise AndroidAconfigProtobufDecodeError(
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
        raise AndroidAconfigProtobufDecodeError(
            f"{field_name} must use protobuf "
            "length-delimited encoding"
        )

    try:
        return value.decode(
            "utf-8"
        )
    except UnicodeDecodeError as error:
        raise AndroidAconfigProtobufDecodeError(
            f"{field_name} contains invalid UTF-8"
        ) from error


def _decode_bool(
    value: int | bytes | None,
    *,
    field_name: str,
) -> bool:
    if not isinstance(
        value,
        int,
    ):
        raise AndroidAconfigProtobufDecodeError(
            f"{field_name} must use protobuf varint encoding"
        )

    return bool(
        value
    )


def _unknown_field(
    record: _WireRecord,
) -> AndroidAconfigProtobufUnknownField:
    return AndroidAconfigProtobufUnknownField(
        field_number=record.field_number,
        wire_type=record.wire_type,
        raw=record.raw,
    )


class AndroidAconfigProtobufParser:
    """
    Literal decoder for Android aconfig parsed_flags protobufs.

    Every aconfig_flags.pb source remains independent. Parsing preserves
    proto2 scalar presence, source order, tracepoint order, numeric enum
    values, and unknown fields. It does not merge, sort, deduplicate, validate
    effective state, or reconstruct aconfig source/build declarations.
    """

    def decode(
        self,
        raw: bytes,
    ) -> tuple[
        tuple[
            AndroidAconfigParsedFlag,
            ...,
        ],
        tuple[
            AndroidAconfigProtobufUnknownField,
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

        flags: list[
            AndroidAconfigParsedFlag
        ] = []

        unknown_fields: list[
            AndroidAconfigProtobufUnknownField
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
                flags.append(
                    self._decode_parsed_flag(
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
                flags
            ),
            tuple(
                unknown_fields
            ),
        )

    def _decode_metadata(
        self,
        raw: bytes,
    ) -> AndroidAconfigFlagMetadata:
        purpose_value = 0
        purpose_present = False

        unknown_fields: list[
            AndroidAconfigProtobufUnknownField
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
                and record.wire_type == 0
                and isinstance(
                    record.value,
                    int,
                )
            ):
                purpose_value = (
                    record.value
                )
                purpose_present = True

            else:
                unknown_fields.append(
                    _unknown_field(
                        record
                    )
                )

        return AndroidAconfigFlagMetadata(
            purpose_value=purpose_value,
            purpose_present=purpose_present,
            unknown_fields=tuple(
                unknown_fields
            ),
        )

    def _decode_tracepoint(
        self,
        raw: bytes,
    ) -> AndroidAconfigTracepoint:
        source = ""
        source_present = False

        state_value = 0
        state_present = False

        permission_value = 0
        permission_present = False

        unknown_fields: list[
            AndroidAconfigProtobufUnknownField
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
                source = _decode_string(
                    record.value,
                    field_name=(
                        "tracepoint.source"
                    ),
                )
                source_present = True

            elif (
                record.field_number == 2
                and record.wire_type == 0
                and isinstance(
                    record.value,
                    int,
                )
            ):
                state_value = (
                    record.value
                )
                state_present = True

            elif (
                record.field_number == 3
                and record.wire_type == 0
                and isinstance(
                    record.value,
                    int,
                )
            ):
                permission_value = (
                    record.value
                )
                permission_present = True

            else:
                unknown_fields.append(
                    _unknown_field(
                        record
                    )
                )

        return AndroidAconfigTracepoint(
            source=source,
            source_present=source_present,
            state_value=state_value,
            state_present=state_present,
            permission_value=permission_value,
            permission_present=(
                permission_present
            ),
            unknown_fields=tuple(
                unknown_fields
            ),
        )

    def _decode_parsed_flag(
        self,
        raw: bytes,
    ) -> AndroidAconfigParsedFlag:
        package = ""
        package_present = False

        name = ""
        name_present = False

        namespace = ""
        namespace_present = False

        description = ""
        description_present = False

        bugs: list[
            str
        ] = []

        state_value = 0
        state_present = False

        permission_value = 0
        permission_present = False

        tracepoints: list[
            AndroidAconfigTracepoint
        ] = []

        is_fixed_read_only = False
        is_fixed_read_only_present = False

        is_exported = False
        is_exported_present = False

        container = ""
        container_present = False

        metadata = None
        metadata_present = False

        unknown_fields: list[
            AndroidAconfigProtobufUnknownField
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
                package = _decode_string(
                    record.value,
                    field_name="parsed_flag.package",
                )
                package_present = True

            elif (
                record.field_number == 2
                and record.wire_type == 2
            ):
                name = _decode_string(
                    record.value,
                    field_name="parsed_flag.name",
                )
                name_present = True

            elif (
                record.field_number == 3
                and record.wire_type == 2
            ):
                namespace = _decode_string(
                    record.value,
                    field_name="parsed_flag.namespace",
                )
                namespace_present = True

            elif (
                record.field_number == 4
                and record.wire_type == 2
            ):
                description = _decode_string(
                    record.value,
                    field_name=(
                        "parsed_flag.description"
                    ),
                )
                description_present = True

            elif (
                record.field_number == 5
                and record.wire_type == 2
            ):
                bugs.append(
                    _decode_string(
                        record.value,
                        field_name=(
                            "parsed_flag.bug"
                        ),
                    )
                )

            elif (
                record.field_number == 6
                and record.wire_type == 0
                and isinstance(
                    record.value,
                    int,
                )
            ):
                state_value = (
                    record.value
                )
                state_present = True

            elif (
                record.field_number == 7
                and record.wire_type == 0
                and isinstance(
                    record.value,
                    int,
                )
            ):
                permission_value = (
                    record.value
                )
                permission_present = True

            elif (
                record.field_number == 8
                and record.wire_type == 2
                and isinstance(
                    record.value,
                    bytes,
                )
            ):
                tracepoints.append(
                    self._decode_tracepoint(
                        record.value
                    )
                )

            elif (
                record.field_number == 9
                and record.wire_type == 0
            ):
                is_fixed_read_only = (
                    _decode_bool(
                        record.value,
                        field_name=(
                            "parsed_flag."
                            "is_fixed_read_only"
                        ),
                    )
                )
                is_fixed_read_only_present = True

            elif (
                record.field_number == 10
                and record.wire_type == 0
            ):
                is_exported = (
                    _decode_bool(
                        record.value,
                        field_name=(
                            "parsed_flag.is_exported"
                        ),
                    )
                )
                is_exported_present = True

            elif (
                record.field_number == 11
                and record.wire_type == 2
            ):
                container = _decode_string(
                    record.value,
                    field_name=(
                        "parsed_flag.container"
                    ),
                )
                container_present = True

            elif (
                record.field_number == 12
                and record.wire_type == 2
                and isinstance(
                    record.value,
                    bytes,
                )
            ):
                metadata = (
                    self._decode_metadata(
                        record.value
                    )
                )
                metadata_present = True

            else:
                unknown_fields.append(
                    _unknown_field(
                        record
                    )
                )

        return AndroidAconfigParsedFlag(
            package=package,
            package_present=package_present,
            name=name,
            name_present=name_present,
            namespace=namespace,
            namespace_present=namespace_present,
            description=description,
            description_present=(
                description_present
            ),
            bugs=tuple(
                bugs
            ),
            state_value=state_value,
            state_present=state_present,
            permission_value=permission_value,
            permission_present=(
                permission_present
            ),
            tracepoints=tuple(
                tracepoints
            ),
            is_fixed_read_only=(
                is_fixed_read_only
            ),
            is_fixed_read_only_present=(
                is_fixed_read_only_present
            ),
            is_exported=is_exported,
            is_exported_present=(
                is_exported_present
            ),
            container=container,
            container_present=container_present,
            metadata=metadata,
            metadata_present=metadata_present,
            unknown_fields=tuple(
                unknown_fields
            ),
        )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidAconfigConfiguration:
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
            .ACONFIG_CONFIGURATION
        ):
            raise ValueError(
                "source must be an aconfig configuration source"
            )

        raw = (
            source.host_path.read_bytes()
        )

        flags, unknown_fields = (
            self.decode(
                raw
            )
        )

        return ParsedAndroidAconfigConfiguration(
            source=source,
            raw=raw,
            flags=flags,
            unknown_fields=unknown_fields,
        )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidAconfigParsingResult:
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
                .ACONFIG_CONFIGURATION
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
            raise AndroidAconfigProtobufDecodeError(
                "aconfig Parsing failed to conserve the complete "
                "canonical ACONFIG_CONFIGURATION source population"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed
        ):
            raise AndroidAconfigProtobufDecodeError(
                "aconfig Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return AndroidAconfigParsingResult(
            configurations=tuple(
                sorted(
                    parsed,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            )
        )
