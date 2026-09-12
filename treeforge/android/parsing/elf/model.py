from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadataEntry,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


class AndroidElfClass(StrEnum):
    ELF32 = "elf32"
    ELF64 = "elf64"


class AndroidElfEndianness(StrEnum):
    LITTLE = "little"
    BIG = "big"


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElfNote:
    index: int
    owner: str
    note_type: str
    descriptor: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise ValueError(
                "ELF note index must be a non-negative integer"
            )

        for field_name in (
            "owner",
            "note_type",
            "descriptor",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElfNoteSection:
    section_name: str
    data: bytes
    notes: tuple[
        ParsedAndroidElfNote,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.section_name,
                str,
            )
            or not self.section_name
        ):
            raise ValueError(
                "ELF note section_name must be a non-empty string"
            )

        if not isinstance(
            self.data,
            bytes,
        ):
            raise TypeError(
                "ELF note section data must be bytes"
            )

        if not isinstance(
            self.notes,
            tuple,
        ):
            raise TypeError(
                "ELF note section notes must be a tuple"
            )

        if not all(
            isinstance(
                note,
                ParsedAndroidElfNote,
            )
            for note in self.notes
        ):
            raise TypeError(
                "ELF note section notes must contain only "
                "ParsedAndroidElfNote entries"
            )

        indexes = tuple(
            note.index
            for note in self.notes
        )

        if indexes != tuple(
            range(
                len(self.notes)
            )
        ):
            raise ValueError(
                "ELF notes must use contiguous canonical indexes"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElfAttribute:
    subsection_index: int
    subsubsection_index: int
    attribute_index: int
    tag: str
    value: str
    extra: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "subsection_index",
            "subsubsection_index",
            "attribute_index",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            not isinstance(
                self.tag,
                str,
            )
            or not self.tag
        ):
            raise ValueError(
                "ELF attribute tag must be a non-empty string"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "ELF attribute value must be a string"
            )

        if (
            self.extra is not None
            and not isinstance(
                self.extra,
                str,
            )
        ):
            raise TypeError(
                "ELF attribute extra must be a string or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElfAttributeSection:
    section_name: str
    data: bytes
    attributes: tuple[
        ParsedAndroidElfAttribute,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.section_name,
                str,
            )
            or not self.section_name
        ):
            raise ValueError(
                "ELF attribute section_name must be a non-empty string"
            )

        if not isinstance(
            self.data,
            bytes,
        ):
            raise TypeError(
                "ELF attribute section data must be bytes"
            )

        if not isinstance(
            self.attributes,
            tuple,
        ):
            raise TypeError(
                "ELF attribute section attributes must be a tuple"
            )

        if not all(
            isinstance(
                attribute,
                ParsedAndroidElfAttribute,
            )
            for attribute in self.attributes
        ):
            raise TypeError(
                "ELF attribute section attributes must contain only "
                "ParsedAndroidElfAttribute entries"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElfSource:
    # Exact Parsing-stage identity for one physical ELF source.
    filesystem_source: AndroidParserFilesystemSource | None
    android_path: PurePosixPath | None
    host_path: Path
    metadata_entry: FilesystemMetadataEntry | None = None
    extraction_artifact: ExtractedArtifact | None = None

    def __post_init__(self) -> None:
        filesystem_backed = (
            self.filesystem_source
            is not None
        )

        extraction_backed = (
            self.extraction_artifact
            is not None
        )

        if (
            filesystem_backed
            == extraction_backed
        ):
            raise ValueError(
                "ELF source must have exactly one canonical origin: "
                "filesystem_source or extraction_artifact"
            )

        if not isinstance(
            self.host_path,
            Path,
        ):
            raise TypeError(
                "host_path must be a Path"
            )

        if filesystem_backed:
            if not isinstance(
                self.filesystem_source,
                AndroidParserFilesystemSource,
            ):
                raise TypeError(
                    "filesystem_source must be an "
                    "AndroidParserFilesystemSource"
                )

            if not isinstance(
                self.android_path,
                PurePosixPath,
            ):
                raise TypeError(
                    "filesystem-backed ELF android_path must be "
                    "a PurePosixPath"
                )

            if not self.android_path.is_absolute():
                raise ValueError(
                    "android_path must be absolute"
                )

            if (
                self.android_path
                == PurePosixPath("/")
            ):
                raise ValueError(
                    "android_path must identify a file"
                )

            try:
                self.host_path.relative_to(
                    self.filesystem_source.filesystem.root
                )
            except ValueError as error:
                raise ValueError(
                    "host_path must belong to the canonical "
                    "parser filesystem"
                ) from error

        else:
            if self.android_path is not None:
                raise ValueError(
                    "extraction-backed ELF must not invent "
                    "an Android filesystem path"
                )

            if not isinstance(
                self.extraction_artifact,
                ExtractedArtifact,
            ):
                raise TypeError(
                    "extraction_artifact must be an ExtractedArtifact"
                )

            if (
                self.extraction_artifact.operation
                is not ExtractionOperation
                .EMBEDDED_ELF_EXTRACTION
            ):
                raise ValueError(
                    "extraction-backed ELF source must be produced by "
                    "EMBEDDED_ELF_EXTRACTION"
                )

            if (
                self.host_path
                != self.extraction_artifact.path
            ):
                raise ValueError(
                    "host_path must match the exact canonical "
                    "Extraction artifact"
                )

            if self.metadata_entry is not None:
                raise ValueError(
                    "extraction-backed ELF source cannot carry "
                    "filesystem metadata"
                )

        if (
            self.metadata_entry is not None
            and not isinstance(
                self.metadata_entry,
                FilesystemMetadataEntry,
            )
        ):
            raise TypeError(
                "metadata_entry must be a "
                "FilesystemMetadataEntry or None"
            )

    @property
    def is_filesystem_backed(
        self,
    ) -> bool:
        return (
            self.filesystem_source
            is not None
        )

    @property
    def is_extraction_backed(
        self,
    ) -> bool:
        return (
            self.extraction_artifact
            is not None
        )

    @property
    def source_name(self) -> str:
        if self.filesystem_source is not None:
            return (
                self.filesystem_source
                .source_name
            )

        artifact = (
            self.extraction_artifact
        )

        assert artifact is not None

        parent = (
            artifact.parent
        )

        parent_identity = (
            (
                parent.semantic_name
                or parent.path.name
            )
            if parent is not None
            else "extraction"
        )

        child_identity = (
            artifact.semantic_name
            or artifact.path.name
        )

        return (
            "extraction:"
            f"{parent_identity}:"
            f"{child_identity}"
        )

    @property
    def display_path(
        self,
    ) -> str:
        if self.android_path is not None:
            return (
                self.android_path
                .as_posix()
            )

        return self.host_path.as_posix()

    @property
    def identity_key(
        self,
    ) -> tuple[
        str,
        str,
    ]:
        if self.filesystem_source is not None:
            assert (
                self.android_path
                is not None
            )

            return (
                self.filesystem_source.source_name,
                self.android_path.as_posix(),
            )

        artifact = (
            self.extraction_artifact
        )

        assert artifact is not None

        return (
            "extraction",
            artifact.path.as_posix(),
        )

    @property
    def partition(self):
        if self.filesystem_source is None:
            return None

        return (
            self.filesystem_source
            .partition
        )

    @property
    def partition_name(self) -> str | None:
        if self.filesystem_source is None:
            return None

        return (
            self.filesystem_source
            .partition_name
        )

    @property
    def artifact(self):
        if (
            self.extraction_artifact
            is not None
        ):
            return self.extraction_artifact

        assert (
            self.filesystem_source
            is not None
        )

        return (
            self.filesystem_source
            .artifact
        )



class AndroidElfEmbeddedReferenceKind(
    StrEnum
):
    """
    Intrinsic lexical form of one runtime-carried ELF reference.

    No Android/device-level meaning is assigned here.
    """

    ABSOLUTE_PATH = "absolute_path"
    DOTTED_IDENTIFIER = "dotted_identifier"
    PLAIN_LABEL = "plain_label"


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElfEmbeddedReference:
    """
    One canonical lexical reference carried by a runtime-allocated,
    non-executable ELF section.

    Section and byte offsets retain exact physical provenance.
    """

    kind: AndroidElfEmbeddedReferenceKind

    section_index: int
    section_name: str

    section_byte_offset: int
    file_byte_offset: int

    value: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            AndroidElfEmbeddedReferenceKind,
        ):
            raise TypeError(
                "kind must be an AndroidElfEmbeddedReferenceKind"
            )

        for field_name in (
            "section_index",
            "section_byte_offset",
            "file_byte_offset",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            not isinstance(
                self.section_name,
                str,
            )
            or not self.section_name
        ):
            raise ValueError(
                "section_name must be a non-empty string"
            )

        if (
            not isinstance(
                self.value,
                str,
            )
            or not self.value
        ):
            raise ValueError(
                "value must be a non-empty string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidElf:
    # Intrinsic facts decoded from one exact ELF source.
    source: ParsedAndroidElfSource
    elf_class: AndroidElfClass
    endianness: AndroidElfEndianness
    machine: str
    elf_type: str
    soname: str | None = None
    needed: tuple[str, ...] = ()
    interpreter: str | None = None
    soong_intermediate_components: tuple[str, ...] = ()
    e_flags: int = 0

    embedded_references: tuple[
        ParsedAndroidElfEmbeddedReference,
        ...,
    ] = ()

    comments: tuple[str, ...] = ()
    note_sections: tuple[
        ParsedAndroidElfNoteSection,
        ...,
    ] = ()
    attribute_sections: tuple[
        ParsedAndroidElfAttributeSection,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElfSource,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElfSource"
            )

        if not isinstance(
            self.elf_class,
            AndroidElfClass,
        ):
            raise TypeError(
                "elf_class must be an AndroidElfClass"
            )

        if not isinstance(
            self.endianness,
            AndroidElfEndianness,
        ):
            raise TypeError(
                "endianness must be an AndroidElfEndianness"
            )

        for field_name in (
            "machine",
            "elf_type",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        for field_name in (
            "soname",
            "interpreter",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )

            if (
                isinstance(
                    value,
                    str,
                )
                and not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.needed,
            tuple,
        ):
            raise TypeError(
                "needed must be a tuple"
            )

        if not all(
            isinstance(
                dependency,
                str,
            )
            and dependency.strip()
            for dependency in self.needed
        ):
            raise ValueError(
                "needed entries must be non-empty strings"
            )

        if len(
            self.needed
        ) != len(
            set(
                self.needed
            )
        ):
            raise ValueError(
                "needed must not contain duplicates"
            )

        if not isinstance(
            self.soong_intermediate_components,
            tuple,
        ):
            raise TypeError(
                "soong_intermediate_components must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value.strip()
            for value in self.soong_intermediate_components
        ):
            raise ValueError(
                "soong_intermediate_components entries must be non-empty strings"
            )

        if len(
            self.soong_intermediate_components
        ) != len(
            set(
                self.soong_intermediate_components
            )
        ):
            raise ValueError(
                "soong_intermediate_components must not contain duplicates"
            )

        if (
            isinstance(
                self.e_flags,
                bool,
            )
            or not isinstance(
                self.e_flags,
                int,
            )
            or self.e_flags < 0
        ):
            raise ValueError(
                "e_flags must be a non-negative integer"
            )

        if not isinstance(
            self.embedded_references,
            tuple,
        ):
            raise TypeError(
                "embedded_references must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedAndroidElfEmbeddedReference,
            )
            for value
            in self.embedded_references
        ):
            raise TypeError(
                "embedded_references must contain only "
                "ParsedAndroidElfEmbeddedReference values"
            )

        reference_keys = tuple(
            (
                value.section_index,
                value.section_byte_offset,
                value.file_byte_offset,
                value.kind.value,
                value.value,
            )
            for value
            in self.embedded_references
        )

        if reference_keys != tuple(
            sorted(
                reference_keys
            )
        ):
            raise ValueError(
                "embedded_references must preserve canonical "
                "ELF section/offset order"
            )

        if len(
            reference_keys
        ) != len(
            set(
                reference_keys
            )
        ):
            raise ValueError(
                "embedded_references must not contain duplicates"
            )

        if not isinstance(
            self.comments,
            tuple,
        ):
            raise TypeError(
                "comments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            for value in self.comments
        ):
            raise ValueError(
                "comments must contain only non-empty strings"
            )

        if not isinstance(
            self.note_sections,
            tuple,
        ):
            raise TypeError(
                "note_sections must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedAndroidElfNoteSection,
            )
            for value in self.note_sections
        ):
            raise TypeError(
                "note_sections must contain only "
                "ParsedAndroidElfNoteSection entries"
            )

        if not isinstance(
            self.attribute_sections,
            tuple,
        ):
            raise TypeError(
                "attribute_sections must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedAndroidElfAttributeSection,
            )
            for value in self.attribute_sections
        ):
            raise TypeError(
                "attribute_sections must contain only "
                "ParsedAndroidElfAttributeSection entries"
            )

    @property
    def bitness(self) -> int:
        if self.elf_class is AndroidElfClass.ELF32:
            return 32

        return 64

    @property
    def is_shared_object(self) -> bool:
        return self.elf_type == "ET_DYN"

    @property
    def is_executable(self) -> bool:
        return self.elf_type == "ET_EXEC"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidElfParsingResult:
    # Complete deterministic ELF population observed by Parsing.
    elf_files: tuple[
        ParsedAndroidElf,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.elf_files,
            tuple,
        ):
            raise TypeError(
                "elf_files must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedAndroidElf,
            )
            for value in self.elf_files
        ):
            raise TypeError(
                "elf_files must contain only ParsedAndroidElf"
            )

        canonical = tuple(
            sorted(
                self.elf_files,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if canonical != self.elf_files:
            raise ValueError(
                "elf_files must use canonical source/path order"
            )

        identities = tuple(
            value.source.identity_key
            for value in self.elf_files
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "elf_files must not contain duplicate sources"
            )

        embedded_artifact_ids = tuple(
            id(
                value.source
                .extraction_artifact
            )
            for value
            in self.elf_files
            if (
                value.source
                .is_extraction_backed
            )
        )

        if len(
            embedded_artifact_ids
        ) != len(
            set(
                embedded_artifact_ids
            )
        ):
            raise ValueError(
                "extraction-backed ELF files must preserve "
                "unique canonical Extraction artifact identities"
            )

    @property
    def count(self) -> int:
        return len(
            self.elf_files
        )


    @property
    def filesystem_elf_count(
        self,
    ) -> int:
        return sum(
            1
            for value in self.elf_files
            if (
                value.source
                .is_filesystem_backed
            )
        )

    @property
    def extraction_elf_count(
        self,
    ) -> int:
        return sum(
            1
            for value in self.elf_files
            if (
                value.source
                .is_extraction_backed
            )
        )

    @property
    def extraction_elf_files(
        self,
    ) -> tuple[
        ParsedAndroidElf,
        ...,
    ]:
        return tuple(
            value
            for value in self.elf_files
            if (
                value.source
                .is_extraction_backed
            )
        )

    @property
    def elf32_files(
        self,
    ) -> tuple[ParsedAndroidElf, ...]:
        return tuple(
            value
            for value in self.elf_files
            if value.bitness == 32
        )

    @property
    def elf64_files(
        self,
    ) -> tuple[ParsedAndroidElf, ...]:
        return tuple(
            value
            for value in self.elf_files
            if value.bitness == 64
        )

    @property
    def elf32_count(self) -> int:
        return len(
            self.elf32_files
        )

    @property
    def elf64_count(self) -> int:
        return len(
            self.elf64_files
        )

    @property
    def machines(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    value.machine
                    for value in self.elf_files
                }
            )
        )
