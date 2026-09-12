from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath


class AndroidDexEndianEncoding(
    StrEnum
):
    LITTLE = "little"
    REVERSE_BYTE_SWAPPED = "reverse_byte_swapped"


class AndroidDexSourceKind(
    StrEnum
):
    """
    Physical container form supplying one exact DEX payload.

    This is structural provenance only. Runtime/classpath/package meaning
    belongs to later Parsing joins or Android Device Universe.
    """

    STANDALONE = "standalone"
    JAVA_ARCHIVE_MEMBER = "java_archive_member"
    APK_MEMBER = "apk_member"
    VDEX_CONTAINED = "vdex_contained"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDexHeader:
    """
    Literal standard DEX header fields.

    Parsing preserves only facts encoded directly by the DEX payload.
    No class, method, package, classpath, or runtime interpretation occurs
    here.
    """

    magic: bytes
    checksum: int
    signature: bytes

    file_size: int
    header_size: int
    endian_tag: int
    endian_encoding: AndroidDexEndianEncoding

    link_size: int
    link_offset: int
    map_offset: int

    string_ids_size: int
    string_ids_offset: int

    type_ids_size: int
    type_ids_offset: int

    proto_ids_size: int
    proto_ids_offset: int

    field_ids_size: int
    field_ids_offset: int

    method_ids_size: int
    method_ids_offset: int

    class_defs_size: int
    class_defs_offset: int

    data_size: int
    data_offset: int

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.magic,
                bytes,
            )
            or len(
                self.magic
            )
            != 8
        ):
            raise ValueError(
                "DEX magic must be exactly eight bytes"
            )

        if not self.magic.startswith(
            b"dex\n"
        ):
            raise ValueError(
                "DEX magic must use the standard dex newline prefix"
            )

        if (
            not isinstance(
                self.signature,
                bytes,
            )
            or len(
                self.signature
            )
            != 20
        ):
            raise ValueError(
                "DEX signature must be exactly twenty bytes"
            )

        if not isinstance(
            self.endian_encoding,
            AndroidDexEndianEncoding,
        ):
            raise TypeError(
                "endian_encoding must be an AndroidDexEndianEncoding"
            )

        for name in (
            "checksum",
            "file_size",
            "header_size",
            "endian_tag",
            "link_size",
            "link_offset",
            "map_offset",
            "string_ids_size",
            "string_ids_offset",
            "type_ids_size",
            "type_ids_offset",
            "proto_ids_size",
            "proto_ids_offset",
            "field_ids_size",
            "field_ids_offset",
            "method_ids_size",
            "method_ids_offset",
            "class_defs_size",
            "class_defs_offset",
            "data_size",
            "data_offset",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if self.header_size < 0x70:
            raise ValueError(
                "DEX header_size must be at least 0x70"
            )

        if self.file_size < self.header_size:
            raise ValueError(
                "DEX file_size must not be smaller than header_size"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDexSource:
    """
    Exact structural provenance for one DEX payload.

    DEX payloads may be filesystem files, archive members, or bytes embedded
    in another binary container.  This model preserves that parent/child
    relationship without pretending every DEX is an AndroidModelSource.
    """

    kind: AndroidDexSourceKind

    # Exact canonical parent object supplied by the owning Parsing
    # population.  The concrete type depends on the container kind:
    # AndroidModelSource for Java archives today, and later the exact APK
    # or OAT parent object for those producers.
    #
    # Stable source/path fields remain separately preserved below so
    # deterministic identity never depends on Python object ids.
    parent: object

    parent_source_name: str
    parent_android_path: PurePosixPath

    member_name: str | None = None
    member_index: int | None = None

    embedded_offset: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidDexSourceKind,
        ):
            raise TypeError(
                "kind must be an AndroidDexSourceKind"
            )

        if self.parent is None:
            raise ValueError(
                "parent must retain the exact canonical parent object"
            )

        if (
            not isinstance(
                self.parent_source_name,
                str,
            )
            or not self.parent_source_name
        ):
            raise ValueError(
                "parent_source_name must be a non-empty string"
            )

        if not isinstance(
            self.parent_android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "parent_android_path must be a PurePosixPath"
            )

        if not self.parent_android_path.is_absolute():
            raise ValueError(
                "parent_android_path must be absolute"
            )

        if self.member_name is not None:
            if (
                not isinstance(
                    self.member_name,
                    str,
                )
                or not self.member_name
            ):
                raise ValueError(
                    "member_name must be a non-empty string or None"
                )

        if self.member_index is not None:
            if (
                isinstance(
                    self.member_index,
                    bool,
                )
                or not isinstance(
                    self.member_index,
                    int,
                )
                or self.member_index < 0
            ):
                raise ValueError(
                    "member_index must be a non-negative integer or None"
                )

        if self.embedded_offset is not None:
            if (
                isinstance(
                    self.embedded_offset,
                    bool,
                )
                or not isinstance(
                    self.embedded_offset,
                    int,
                )
                or self.embedded_offset < 0
            ):
                raise ValueError(
                    "embedded_offset must be a non-negative integer or None"
                )

        if self.kind in {
            AndroidDexSourceKind.JAVA_ARCHIVE_MEMBER,
            AndroidDexSourceKind.APK_MEMBER,
        }:
            if (
                self.member_name is None
                or self.member_index is None
            ):
                raise ValueError(
                    "archive-member DEX sources require member_name "
                    "and member_index"
                )

            if self.embedded_offset is not None:
                raise ValueError(
                    "archive-member DEX sources must not carry "
                    "embedded_offset"
                )

        elif self.kind is AndroidDexSourceKind.VDEX_CONTAINED:
            if self.embedded_offset is None:
                raise ValueError(
                    "VDEX-contained DEX sources require embedded_offset"
                )

            if (
                self.member_name is not None
                or self.member_index is not None
            ):
                raise ValueError(
                    "VDEX-contained DEX sources must not carry "
                    "archive member identity"
                )

        elif self.kind is AndroidDexSourceKind.STANDALONE:
            if (
                self.member_name is not None
                or self.member_index is not None
                or self.embedded_offset is not None
            ):
                raise ValueError(
                    "standalone DEX sources must not carry child-container "
                    "identity"
                )

    @property
    def identity_key(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        child = (
            self.member_name
            if self.member_name is not None
            else (
                str(
                    self.embedded_offset
                )
                if self.embedded_offset is not None
                else ""
            )
        )

        child_index = (
            str(
                self.member_index
            )
            if self.member_index is not None
            else ""
        )

        return (
            self.kind.value,
            self.parent_source_name,
            self.parent_android_path.as_posix(),
            child,
            child_index,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDexString:
    """
    One exact DEX string_id/string_data_item observation.

    ``utf16_code_units`` preserves the literal UTF-16 code-unit sequence
    represented by DEX MUTF-8. ``value`` is the corresponding Python string
    representation used by later semantic joins.
    """

    index: int
    data_offset: int
    utf16_size: int
    utf16_code_units: tuple[int, ...]
    value: str

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "index",
            "data_offset",
            "utf16_size",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.utf16_code_units,
            tuple,
        ):
            raise TypeError(
                "utf16_code_units must be a tuple"
            )

        if len(
            self.utf16_code_units
        ) != self.utf16_size:
            raise ValueError(
                "utf16_code_units must exactly conserve utf16_size"
            )

        for code_unit in self.utf16_code_units:
            if (
                isinstance(
                    code_unit,
                    bool,
                )
                or not isinstance(
                    code_unit,
                    int,
                )
                or not 0 <= code_unit <= 0xFFFF
            ):
                raise ValueError(
                    "UTF-16 code units must be integers in "
                    "the range 0x0000..0xffff"
                )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDexType:
    """
    One exact DEX type_id entry and its canonical descriptor string.
    """

    index: int
    descriptor_index: int
    descriptor: AndroidDexString

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "index",
            "descriptor_index",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.descriptor,
            AndroidDexString,
        ):
            raise TypeError(
                "descriptor must be an AndroidDexString"
            )

        if (
            self.descriptor.index
            != self.descriptor_index
        ):
            raise ValueError(
                "descriptor_index must match descriptor identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDexClass:
    """
    One exact DEX class_def plus the resolved type identities needed for
    later structural relationship joins.

    No Java/AIDL/VINTF meaning is assigned here.
    """

    definition_index: int

    class_type_index: int
    class_type: AndroidDexType
    access_flags: int

    superclass_type_index: int | None
    superclass_type: AndroidDexType | None

    interfaces_offset: int
    interface_type_indices: tuple[int, ...]
    interface_types: tuple[AndroidDexType, ...]

    source_file_index: int | None
    source_file: AndroidDexString | None

    annotations_offset: int
    class_data_offset: int
    static_values_offset: int

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "definition_index",
            "class_type_index",
            "access_flags",
            "interfaces_offset",
            "annotations_offset",
            "class_data_offset",
            "static_values_offset",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.class_type,
            AndroidDexType,
        ):
            raise TypeError(
                "class_type must be an AndroidDexType"
            )

        if (
            self.class_type.index
            != self.class_type_index
        ):
            raise ValueError(
                "class_type_index must match class_type identity"
            )

        if (
            self.superclass_type_index
            is None
        ) != (
            self.superclass_type
            is None
        ):
            raise ValueError(
                "superclass index/object presence must match"
            )

        if self.superclass_type_index is not None:
            if (
                isinstance(
                    self.superclass_type_index,
                    bool,
                )
                or not isinstance(
                    self.superclass_type_index,
                    int,
                )
                or self.superclass_type_index < 0
            ):
                raise ValueError(
                    "superclass_type_index must be a "
                    "non-negative integer or None"
                )

            if not isinstance(
                self.superclass_type,
                AndroidDexType,
            ):
                raise TypeError(
                    "superclass_type must be an AndroidDexType or None"
                )

            if (
                self.superclass_type.index
                != self.superclass_type_index
            ):
                raise ValueError(
                    "superclass_type_index must match "
                    "superclass_type identity"
                )

        if not isinstance(
            self.interface_type_indices,
            tuple,
        ):
            raise TypeError(
                "interface_type_indices must be a tuple"
            )

        if not isinstance(
            self.interface_types,
            tuple,
        ):
            raise TypeError(
                "interface_types must be a tuple"
            )

        if (
            len(
                self.interface_type_indices
            )
            != len(
                self.interface_types
            )
        ):
            raise ValueError(
                "interface type indexes and objects must conserve "
                "one-to-one identity"
            )

        for type_index, type_object in zip(
            self.interface_type_indices,
            self.interface_types,
            strict=True,
        ):
            if (
                isinstance(
                    type_index,
                    bool,
                )
                or not isinstance(
                    type_index,
                    int,
                )
                or type_index < 0
            ):
                raise ValueError(
                    "interface type indexes must be "
                    "non-negative integers"
                )

            if not isinstance(
                type_object,
                AndroidDexType,
            ):
                raise TypeError(
                    "interface_types must contain "
                    "AndroidDexType instances"
                )

            if type_object.index != type_index:
                raise ValueError(
                    "interface type index/object identity mismatch"
                )

        if (
            self.source_file_index
            is None
        ) != (
            self.source_file
            is None
        ):
            raise ValueError(
                "source-file index/object presence must match"
            )

        if self.source_file_index is not None:
            if (
                isinstance(
                    self.source_file_index,
                    bool,
                )
                or not isinstance(
                    self.source_file_index,
                    int,
                )
                or self.source_file_index < 0
            ):
                raise ValueError(
                    "source_file_index must be a "
                    "non-negative integer or None"
                )

            if not isinstance(
                self.source_file,
                AndroidDexString,
            ):
                raise TypeError(
                    "source_file must be an AndroidDexString or None"
                )

            if (
                self.source_file.index
                != self.source_file_index
            ):
                raise ValueError(
                    "source_file_index must match source_file identity"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidDex:
    """
    One structurally decoded DEX payload.

    `payload_size` is the actual number of supplied bytes. `header.file_size`
    is the size declared by the DEX itself; both are retained so Parsing can
    enforce exact structural conservation.
    """

    source: AndroidDexSource

    payload_size: int
    header: AndroidDexHeader

    strings: tuple[
        AndroidDexString,
        ...,
    ] = ()

    types: tuple[
        AndroidDexType,
        ...,
    ] = ()

    classes: tuple[
        AndroidDexClass,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidDexSource,
        ):
            raise TypeError(
                "source must be an AndroidDexSource"
            )

        if (
            isinstance(
                self.payload_size,
                bool,
            )
            or not isinstance(
                self.payload_size,
                int,
            )
            or self.payload_size < 1
        ):
            raise ValueError(
                "payload_size must be a positive integer"
            )

        if not isinstance(
            self.header,
            AndroidDexHeader,
        ):
            raise TypeError(
                "header must be an AndroidDexHeader"
            )

        if (
            self.header.file_size
            != self.payload_size
        ):
            raise ValueError(
                "DEX declared file_size must exactly match supplied "
                "payload size"
            )

        for name in (
            "strings",
            "types",
            "classes",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                tuple,
            ):
                raise TypeError(
                    f"{name} must be a tuple"
                )

        if (
            len(
                self.strings
            )
            != self.header.string_ids_size
        ):
            raise ValueError(
                "decoded DEX strings must exactly conserve "
                "string_ids_size"
            )

        if (
            len(
                self.types
            )
            != self.header.type_ids_size
        ):
            raise ValueError(
                "decoded DEX types must exactly conserve "
                "type_ids_size"
            )

        if (
            len(
                self.classes
            )
            != self.header.class_defs_size
        ):
            raise ValueError(
                "decoded DEX classes must exactly conserve "
                "class_defs_size"
            )

        for index, string in enumerate(
            self.strings
        ):
            if not isinstance(
                string,
                AndroidDexString,
            ):
                raise TypeError(
                    "strings must contain AndroidDexString instances"
                )

            if string.index != index:
                raise ValueError(
                    "DEX string identities must be contiguous "
                    "and preserve source order"
                )

        for index, type_item in enumerate(
            self.types
        ):
            if not isinstance(
                type_item,
                AndroidDexType,
            ):
                raise TypeError(
                    "types must contain AndroidDexType instances"
                )

            if type_item.index != index:
                raise ValueError(
                    "DEX type identities must be contiguous "
                    "and preserve source order"
                )

            if (
                type_item.descriptor_index
                >= len(
                    self.strings
                )
            ):
                raise ValueError(
                    "DEX type descriptor index is out of range"
                )

            if (
                type_item.descriptor
                is not self.strings[
                    type_item.descriptor_index
                ]
            ):
                raise ValueError(
                    "DEX type must retain exact canonical "
                    "descriptor-string object identity"
                )

        for index, class_item in enumerate(
            self.classes
        ):
            if not isinstance(
                class_item,
                AndroidDexClass,
            ):
                raise TypeError(
                    "classes must contain AndroidDexClass instances"
                )

            if class_item.definition_index != index:
                raise ValueError(
                    "DEX class identities must be contiguous "
                    "and preserve class_def order"
                )

            if (
                class_item.class_type_index
                >= len(
                    self.types
                )
                or class_item.class_type
                is not self.types[
                    class_item.class_type_index
                ]
            ):
                raise ValueError(
                    "DEX class must retain exact canonical "
                    "class-type object identity"
                )

            if (
                class_item.superclass_type_index
                is not None
            ):
                if (
                    class_item.superclass_type_index
                    >= len(
                        self.types
                    )
                    or class_item.superclass_type
                    is not self.types[
                        class_item.superclass_type_index
                    ]
                ):
                    raise ValueError(
                        "DEX class must retain exact canonical "
                        "superclass-type object identity"
                    )

            for type_index, type_object in zip(
                class_item.interface_type_indices,
                class_item.interface_types,
                strict=True,
            ):
                if (
                    type_index
                    >= len(
                        self.types
                    )
                    or type_object
                    is not self.types[
                        type_index
                    ]
                ):
                    raise ValueError(
                        "DEX class must retain exact canonical "
                        "interface-type object identity"
                    )

            if (
                class_item.source_file_index
                is not None
            ):
                if (
                    class_item.source_file_index
                    >= len(
                        self.strings
                    )
                    or class_item.source_file
                    is not self.strings[
                        class_item.source_file_index
                    ]
                ):
                    raise ValueError(
                        "DEX class must retain exact canonical "
                        "source-file string identity"
                    )
