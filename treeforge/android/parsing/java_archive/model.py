from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.dex import (
    AndroidDexSourceKind,
    ParsedAndroidDex,
)


from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidJavaArchiveMember:
    """
    One exact ZIP/JAR central-directory member.

    Member order and literal ZIP metadata are intrinsic archive evidence.
    """

    index: int
    filename: str
    compression_method: int
    crc32: int
    compressed_size: int
    uncompressed_size: int
    external_attributes: int
    is_directory: bool

    def __post_init__(self) -> None:
        for field_name, value in (
            ("index", self.index),
            ("compression_method", self.compression_method),
            ("crc32", self.crc32),
            ("compressed_size", self.compressed_size),
            ("uncompressed_size", self.uncompressed_size),
            ("external_attributes", self.external_attributes),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            not isinstance(self.filename, str)
            or not self.filename
        ):
            raise ValueError(
                "filename must be a non-empty string"
            )

        if not isinstance(
            self.is_directory,
            bool,
        ):
            raise TypeError(
                "is_directory must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidJavaManifestLine:
    """
    One exact unfolded logical MANIFEST.MF line.

    ``name`` and ``value`` are populated only when the line has valid
    attribute syntax. Otherwise the exact logical line remains explicitly
    represented with ``parsed=False``.
    """

    index: int
    raw: str
    parsed: bool
    name: str | None = None
    value: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.parsed,
            bool,
        ):
            raise TypeError(
                "parsed must be a bool"
            )

        if self.parsed:
            if (
                not isinstance(self.name, str)
                or not self.name
            ):
                raise ValueError(
                    "parsed manifest line requires a non-empty name"
                )

            if not isinstance(
                self.value,
                str,
            ):
                raise TypeError(
                    "parsed manifest line requires a string value"
                )

        elif (
            self.name is not None
            or self.value is not None
        ):
            raise ValueError(
                "unparsed manifest line must not carry name/value"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidJavaManifestAttribute:
    """
    One literal logical MANIFEST.MF attribute.

    Continuation lines are unfolded mechanically. No Java package or runtime
    meaning is assigned in Parsing.
    """

    index: int
    name: str
    value: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if (
            not isinstance(self.name, str)
            or not self.name
        ):
            raise ValueError(
                "name must be a non-empty string"
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
class ParsedAndroidJavaArchive:
    """
    One canonically identified installed Java archive.

    Parsing preserves exact filesystem source identity, ZIP member structure,
    literal manifest evidence, DEX member identity, and Android resource
    container presence.

    Classpath membership, package ownership, source-vs-prebuilt decisions,
    dependency meaning, and build realization remain downstream concerns.
    """

    source: AndroidModelSource
    file_size: int

    members: tuple[
        AndroidJavaArchiveMember,
        ...,
    ] = ()

    manifest_raw: bytes | None = None
    manifest_text: str | None = None

    manifest_attributes: tuple[
        AndroidJavaManifestAttribute,
        ...,
    ] = ()

    manifest_lines: tuple[
        AndroidJavaManifestLine,
        ...,
    ] = ()

    dex_entries: tuple[
        str,
        ...,
    ] = ()

    dex_files: tuple[
        ParsedAndroidDex,
        ...,
    ] = ()

    has_android_resource_table: bool = False
    android_resource_member_count: int = 0

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
            is not AndroidModelSourceKind.JAVA_ARCHIVE
        ):
            raise ValueError(
                "source must be a JAVA_ARCHIVE source"
            )

        if (
            isinstance(self.file_size, bool)
            or not isinstance(self.file_size, int)
            or self.file_size < 1
        ):
            raise ValueError(
                "file_size must be a positive integer"
            )

        if (
            not isinstance(self.members, tuple)
            or not all(
                isinstance(
                    member,
                    AndroidJavaArchiveMember,
                )
                for member in self.members
            )
        ):
            raise TypeError(
                "members must contain only AndroidJavaArchiveMember values"
            )

        expected_indexes = tuple(
            range(
                len(self.members)
            )
        )

        actual_indexes = tuple(
            member.index
            for member in self.members
        )

        if actual_indexes != expected_indexes:
            raise ValueError(
                "archive members must preserve central-directory order"
            )

        if (
            self.manifest_raw is not None
            and not isinstance(
                self.manifest_raw,
                bytes,
            )
        ):
            raise TypeError(
                "manifest_raw must be bytes or None"
            )

        if (
            self.manifest_text is not None
            and not isinstance(
                self.manifest_text,
                str,
            )
        ):
            raise TypeError(
                "manifest_text must be a string or None"
            )

        if (
            self.manifest_raw is None
            and (
                self.manifest_text is not None
                or self.manifest_attributes
            )
        ):
            raise ValueError(
                "decoded manifest evidence requires manifest_raw"
            )

        if (
            not isinstance(
                self.manifest_attributes,
                tuple,
            )
            or not all(
                isinstance(
                    attribute,
                    AndroidJavaManifestAttribute,
                )
                for attribute in self.manifest_attributes
            )
        ):
            raise TypeError(
                "manifest_attributes must contain only "
                "AndroidJavaManifestAttribute values"
            )

        if (
            not isinstance(
                self.manifest_lines,
                tuple,
            )
            or not all(
                isinstance(
                    line,
                    AndroidJavaManifestLine,
                )
                for line
                in self.manifest_lines
            )
        ):
            raise TypeError(
                "manifest_lines must contain only "
                "AndroidJavaManifestLine values"
            )

        expected_line_indexes = tuple(
            range(
                len(
                    self.manifest_lines
                )
            )
        )

        actual_line_indexes = tuple(
            line.index
            for line
            in self.manifest_lines
        )

        if (
            actual_line_indexes
            != expected_line_indexes
        ):
            raise ValueError(
                "manifest lines must preserve canonical order"
            )

        expected_attribute_indexes = tuple(
            range(
                len(self.manifest_attributes)
            )
        )

        actual_attribute_indexes = tuple(
            attribute.index
            for attribute in self.manifest_attributes
        )

        if (
            actual_attribute_indexes
            != expected_attribute_indexes
        ):
            raise ValueError(
                "manifest attributes must preserve canonical order"
            )

        if (
            not isinstance(self.dex_entries, tuple)
            or not all(
                isinstance(value, str)
                and value
                for value in self.dex_entries
            )
        ):
            raise TypeError(
                "dex_entries must contain non-empty strings"
            )

        if len(
            self.dex_entries
        ) != len(
            set(
                self.dex_entries
            )
        ):
            raise ValueError(
                "dex_entries must not contain duplicate names"
            )

        if (
            not isinstance(
                self.dex_files,
                tuple,
            )
            or not all(
                isinstance(
                    dex_file,
                    ParsedAndroidDex,
                )
                for dex_file
                in self.dex_files
            )
        ):
            raise TypeError(
                "dex_files must contain only ParsedAndroidDex values"
            )

        if len(
            self.dex_files
        ) != len(
            self.dex_entries
        ):
            raise ValueError(
                "parsed Java archive DEX population must exactly match "
                "the discovered DEX member population"
            )

        expected_dex_entries = tuple(
            self.dex_entries
        )

        actual_dex_entries = tuple(
            dex_file.source.member_name
            for dex_file
            in self.dex_files
        )

        if actual_dex_entries != expected_dex_entries:
            raise ValueError(
                "parsed Java archive DEX files must preserve exact "
                "DEX member order and identity"
            )

        member_by_index = {
            member.index: member
            for member
            in self.members
        }

        seen_dex_identities = set()

        for dex_file in self.dex_files:
            dex_source = dex_file.source

            if (
                dex_source.kind
                is not AndroidDexSourceKind.JAVA_ARCHIVE_MEMBER
            ):
                raise ValueError(
                    "Java archive dex_files must use "
                    "JAVA_ARCHIVE_MEMBER provenance"
                )

            if dex_source.parent is not self.source:
                raise ValueError(
                    "Java archive DEX must reuse the exact canonical "
                    "AndroidModelSource parent object"
                )

            if (
                dex_source.parent_source_name
                != self.source.source_name
                or dex_source.parent_android_path
                != self.source.android_path
            ):
                raise ValueError(
                    "Java archive DEX stable parent identity must exactly "
                    "match the canonical archive source"
                )

            if dex_source.member_index is None:
                raise ValueError(
                    "Java archive DEX source must retain member index"
                )

            member = member_by_index.get(
                dex_source.member_index
            )

            if (
                member is None
                or member.filename
                != dex_source.member_name
            ):
                raise ValueError(
                    "Java archive DEX source must retain exact "
                    "central-directory member identity"
                )

            if member.is_directory:
                raise ValueError(
                    "Java archive DEX source cannot reference a directory"
                )

            identity = dex_source.identity_key

            if identity in seen_dex_identities:
                raise ValueError(
                    "Java archive DEX source identities must be unique"
                )

            seen_dex_identities.add(
                identity
            )

        if not isinstance(
            self.has_android_resource_table,
            bool,
        ):
            raise TypeError(
                "has_android_resource_table must be a bool"
            )

        if (
            isinstance(
                self.android_resource_member_count,
                bool,
            )
            or not isinstance(
                self.android_resource_member_count,
                int,
            )
            or self.android_resource_member_count < 0
        ):
            raise ValueError(
                "android_resource_member_count must be "
                "a non-negative integer"
            )

    @property
    def member_count(self) -> int:
        return len(
            self.members
        )

    @property
    def dex_count(self) -> int:
        return len(
            self.dex_files
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidJavaArchiveParsingResult:
    """
    Canonical deterministic population of installed Java archives.
    """

    archives: tuple[
        ParsedAndroidJavaArchive,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.archives, tuple)
            or not all(
                isinstance(
                    archive,
                    ParsedAndroidJavaArchive,
                )
                for archive in self.archives
            )
        ):
            raise TypeError(
                "archives must contain only ParsedAndroidJavaArchive values"
            )

        canonical = tuple(
            sorted(
                self.archives,
                key=lambda archive: (
                    archive.source.identity_key
                ),
            )
        )

        if canonical != self.archives:
            raise ValueError(
                "archives must use canonical source order"
            )

        identities = tuple(
            archive.source.identity_key
            for archive in self.archives
        )

        if len(identities) != len(
            set(identities)
        ):
            raise ValueError(
                "Java archive source identities must be unique"
            )

        source_object_ids = tuple(
            id(
                archive.source
            )
            for archive
            in self.archives
        )

        if len(
            source_object_ids
        ) != len(
            set(
                source_object_ids
            )
        ):
            raise ValueError(
                "Java archives must preserve unique canonical "
                "AndroidModelSource object identities"
            )

    @property
    def source_count(self) -> int:
        return len(
            self.archives
        )

    @property
    def member_count(self) -> int:
        return sum(
            archive.member_count
            for archive in self.archives
        )

    @property
    def dex_member_count(self) -> int:
        """
        Return the complete structurally discovered DEX-member population.
        """

        return sum(
            len(
                archive.dex_entries
            )
            for archive
            in self.archives
        )

    @property
    def dex_count(self) -> int:
        """
        Return the complete successfully decoded DEX population.
        """

        return sum(
            len(
                archive.dex_files
            )
            for archive
            in self.archives
        )

    @property
    def unresolved_dex_count(self) -> int:
        """
        Return discovered DEX members lacking a decoded DEX representation.
        """

        return (
            self.dex_member_count
            - self.dex_count
        )

    @property
    def multidex_count(self) -> int:
        return sum(
            1
            for archive in self.archives
            if archive.dex_count > 1
        )

    @property
    def manifest_count(self) -> int:
        return sum(
            1
            for archive in self.archives
            if archive.manifest_raw is not None
        )
