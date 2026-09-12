from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


class AndroidFontContainerKind(StrEnum):
    SFNT = "sfnt"
    TRUE_TYPE_COLLECTION = "true_type_collection"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFontTable:
    """
    One literal SFNT table-directory entry.

    Offsets and lengths are intrinsic container evidence only.
    """

    tag: str
    checksum: int
    offset: int
    length: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.tag, str)
            or len(self.tag) != 4
        ):
            raise ValueError(
                "font table tag must contain exactly four characters"
            )

        for field_name, value in (
            ("checksum", self.checksum),
            ("offset", self.offset),
            ("length", self.length),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFontNameRecord:
    """
    One exact record from an SFNT name table.

    ``raw_value`` preserves encoded source bytes. ``decoded_value`` is only
    a literal text decoding where the platform encoding is known.
    """

    record_index: int

    platform_id: int
    encoding_id: int
    language_id: int
    name_id: int

    raw_value: bytes
    decoded_value: str | None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("record_index", self.record_index),
            ("platform_id", self.platform_id),
            ("encoding_id", self.encoding_id),
            ("language_id", self.language_id),
            ("name_id", self.name_id),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if not isinstance(
            self.raw_value,
            bytes,
        ):
            raise TypeError(
                "raw_value must be bytes"
            )

        if (
            self.decoded_value is not None
            and not isinstance(
                self.decoded_value,
                str,
            )
        ):
            raise TypeError(
                "decoded_value must be a string or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidFontFace:
    """
    One exact SFNT face.

    A standalone TTF/OTF contains one face. A TTC may contain multiple
    independently indexed SFNT faces.
    """

    face_index: int
    offset: int

    sfnt_version: bytes

    tables: tuple[
        AndroidFontTable,
        ...,
    ] = ()

    names: tuple[
        AndroidFontNameRecord,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            isinstance(self.face_index, bool)
            or not isinstance(self.face_index, int)
            or self.face_index < 0
        ):
            raise ValueError(
                "face_index must be a non-negative integer"
            )

        if (
            isinstance(self.offset, bool)
            or not isinstance(self.offset, int)
            or self.offset < 0
        ):
            raise ValueError(
                "offset must be a non-negative integer"
            )

        if (
            not isinstance(self.sfnt_version, bytes)
            or len(self.sfnt_version) != 4
        ):
            raise ValueError(
                "sfnt_version must contain exactly four bytes"
            )

        if (
            not isinstance(self.tables, tuple)
            or not all(
                isinstance(
                    table,
                    AndroidFontTable,
                )
                for table in self.tables
            )
        ):
            raise TypeError(
                "tables must contain only AndroidFontTable values"
            )

        if (
            not isinstance(self.names, tuple)
            or not all(
                isinstance(
                    name,
                    AndroidFontNameRecord,
                )
                for name in self.names
            )
        ):
            raise TypeError(
                "names must contain only AndroidFontNameRecord values"
            )

        table_tags = tuple(
            table.tag
            for table in self.tables
        )

        if len(table_tags) != len(
            set(table_tags)
        ):
            raise ValueError(
                "one font face must not contain duplicate SFNT table tags"
            )

        expected_name_indexes = tuple(
            range(
                len(self.names)
            )
        )

        actual_name_indexes = tuple(
            name.record_index
            for name in self.names
        )

        if actual_name_indexes != expected_name_indexes:
            raise ValueError(
                "font name records must preserve canonical record order"
            )

    @property
    def table_count(self) -> int:
        return len(
            self.tables
        )

    @property
    def name_record_count(self) -> int:
        return len(
            self.names
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidFont:
    """
    One canonically identified installed font container.

    Parsing retains exact source identity and intrinsic SFNT/TTC structure.
    Font selection, fallback, source ownership, package ownership, and build
    realization remain downstream concerns.
    """

    source: AndroidModelSource

    file_size: int
    container_kind: AndroidFontContainerKind

    collection_version: int | None = None

    faces: tuple[
        ParsedAndroidFontFace,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            self.source.kind
            is not AndroidModelSourceKind.FONT
        ):
            raise ValueError(
                "source must be a FONT source"
            )

        if (
            isinstance(self.file_size, bool)
            or not isinstance(self.file_size, int)
            or self.file_size < 1
        ):
            raise ValueError(
                "file_size must be a positive integer"
            )

        if not isinstance(
            self.container_kind,
            AndroidFontContainerKind,
        ):
            raise TypeError(
                "container_kind must be an AndroidFontContainerKind"
            )

        if (
            self.collection_version is not None
            and (
                isinstance(
                    self.collection_version,
                    bool,
                )
                or not isinstance(
                    self.collection_version,
                    int,
                )
                or self.collection_version < 0
            )
        ):
            raise ValueError(
                "collection_version must be a non-negative integer or None"
            )

        if (
            self.container_kind
            is AndroidFontContainerKind.SFNT
            and self.collection_version is not None
        ):
            raise ValueError(
                "standalone SFNT font must not have collection_version"
            )

        if (
            self.container_kind
            is AndroidFontContainerKind.TRUE_TYPE_COLLECTION
            and self.collection_version is None
        ):
            raise ValueError(
                "TTC font requires collection_version"
            )

        if (
            not isinstance(self.faces, tuple)
            or not self.faces
            or not all(
                isinstance(
                    face,
                    ParsedAndroidFontFace,
                )
                for face in self.faces
            )
        ):
            raise TypeError(
                "faces must contain ParsedAndroidFontFace values"
            )

        expected_face_indexes = tuple(
            range(
                len(self.faces)
            )
        )

        actual_face_indexes = tuple(
            face.face_index
            for face in self.faces
        )

        if actual_face_indexes != expected_face_indexes:
            raise ValueError(
                "font faces must preserve canonical face order"
            )

    @property
    def face_count(self) -> int:
        return len(
            self.faces
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFontParsingResult:
    """
    Canonical deterministic population of installed SFNT/TTC fonts.
    """

    fonts: tuple[
        ParsedAndroidFont,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.fonts, tuple)
            or not all(
                isinstance(
                    font,
                    ParsedAndroidFont,
                )
                for font in self.fonts
            )
        ):
            raise TypeError(
                "fonts must contain only ParsedAndroidFont values"
            )

        canonical = tuple(
            sorted(
                self.fonts,
                key=lambda font: (
                    font.source.identity_key
                ),
            )
        )

        if canonical != self.fonts:
            raise ValueError(
                "fonts must use canonical source order"
            )

        identities = tuple(
            font.source.identity_key
            for font in self.fonts
        )

        if len(identities) != len(
            set(identities)
        ):
            raise ValueError(
                "font source identities must be unique"
            )

        source_object_ids = tuple(
            id(
                font.source
            )
            for font
            in self.fonts
        )

        if len(
            source_object_ids
        ) != len(
            set(
                source_object_ids
            )
        ):
            raise ValueError(
                "fonts must preserve unique canonical "
                "AndroidModelSource object identities"
            )

    @property
    def source_count(self) -> int:
        return len(
            self.fonts
        )

    @property
    def face_count(self) -> int:
        return sum(
            font.face_count
            for font in self.fonts
        )

    @property
    def table_count(self) -> int:
        return sum(
            face.table_count
            for font in self.fonts
            for face in font.faces
        )

    @property
    def name_record_count(self) -> int:
        return sum(
            face.name_record_count
            for font in self.fonts
            for face in font.faces
        )
