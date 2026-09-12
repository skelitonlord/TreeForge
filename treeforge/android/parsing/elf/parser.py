from __future__ import annotations

from treeforge.android.parsing.elf.model import (
    AndroidElfEmbeddedReferenceKind,
    ParsedAndroidElfEmbeddedReference,
)

from io import BytesIO
from pathlib import PurePosixPath

from elftools.common.exceptions import (
    ELFError,
)
from elftools.elf.elffile import (
    ELFFile,
)
from elftools.elf.sections import (
    AttributesSection,
    NoteSection,
)

from treeforge.android.extraction import (
    AndroidExtractionResult,
    ExtractionOperation,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
    FilesystemMetadataInventoryEntry,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)

from treeforge.android.parsing.elf.model import (
    AndroidElfClass,
    AndroidElfEndianness,
    AndroidElfParsingResult,
    ParsedAndroidElf,
    ParsedAndroidElfAttribute,
    ParsedAndroidElfAttributeSection,
    ParsedAndroidElfNote,
    ParsedAndroidElfNoteSection,
    ParsedAndroidElfSource,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


class AndroidElfParsingError(
    ValueError,
):
    pass


class AndroidElfParser:
    # Decode intrinsic ELF structure only.
    ELF_MAGIC = bytes((0x7F, 0x45, 0x4C, 0x46))

    def is_elf(
        self,
        source: ParsedAndroidElfSource,
    ) -> bool:
        try:
            with source.host_path.open("rb") as stream:
                return (
                    stream.read(
                        len(
                            self.ELF_MAGIC
                        )
                    )
                    == self.ELF_MAGIC
                )
        except OSError as error:
            raise AndroidElfParsingError(
                "unable to inspect ELF candidate: "
                f"{source.host_path}"
            ) from error

    def parse(
        self,
        source: ParsedAndroidElfSource,
    ) -> ParsedAndroidElf:
        if not isinstance(
            source,
            ParsedAndroidElfSource,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElfSource"
            )

        try:
            content = (
                source.host_path.read_bytes()
            )

            elf = ELFFile(
                BytesIO(
                    content
                )
            )

            elf_class = self._elf_class(
                elf.elfclass
            )

            endianness = (
                AndroidElfEndianness.LITTLE
                if elf.little_endian
                else AndroidElfEndianness.BIG
            )

            machine = str(
                elf.header[
                    "e_machine"
                ]
            )

            elf_type = str(
                elf.header[
                    "e_type"
                ]
            )

            e_flags = int(
                elf.header[
                    "e_flags"
                ]
            )

            soname, needed = (
                self._dynamic_metadata(
                    elf
                )
            )

            interpreter = (
                self._interpreter(
                    elf
                )
            )

            soong_intermediate_components = (
                self._soong_intermediate_components(
                    content
                )
            )

            embedded_references = (
                self._embedded_references(
                    elf
                )
            )

            comments = (
                self._comments(
                    elf
                )
            )

            note_sections = (
                self._note_sections(
                    elf
                )
            )

            attribute_sections = (
                self._attribute_sections(
                    elf
                )
            )

        except (
            ELFError,
            OSError,
            ValueError,
        ) as error:
            raise AndroidElfParsingError(
                "failed to parse ELF source "
                f"{source.source_name}:"
                f"{source.display_path}: "
                f"{error}"
            ) from error

        return ParsedAndroidElf(
            source=source,
            elf_class=elf_class,
            endianness=endianness,
            machine=machine,
            elf_type=elf_type,
            soname=soname,
            needed=needed,
            interpreter=interpreter,
            soong_intermediate_components=soong_intermediate_components,
            e_flags=e_flags,
            embedded_references=embedded_references,
            comments=comments,
            note_sections=note_sections,
            attribute_sections=attribute_sections,
        )

    @staticmethod
    def _stable_metadata_value(
        value,
    ) -> str:
        if value is None:
            return "null"

        if isinstance(
            value,
            bytes,
        ):
            return (
                "bytes:"
                + value.hex()
            )

        if isinstance(
            value,
            bytearray,
        ):
            return (
                "bytes:"
                + bytes(
                    value
                ).hex()
            )

        if isinstance(
            value,
            str,
        ):
            return value

        if isinstance(
            value,
            bool,
        ):
            return (
                "true"
                if value
                else "false"
            )

        if isinstance(
            value,
            int,
        ):
            return str(
                value
            )

        if isinstance(
            value,
            dict,
        ):
            return (
                "{"
                + ",".join(
                    (
                        AndroidElfParser
                        ._stable_metadata_value(
                            key
                        )
                        + ":"
                        + AndroidElfParser
                        ._stable_metadata_value(
                            item
                        )
                    )
                    for key, item
                    in sorted(
                        value.items(),
                        key=lambda pair: (
                            str(
                                pair[0]
                            )
                        ),
                    )
                )
                + "}"
            )

        if isinstance(
            value,
            (tuple, list),
        ):
            return (
                "["
                + ",".join(
                    AndroidElfParser
                    ._stable_metadata_value(
                        item
                    )
                    for item in value
                )
                + "]"
            )

        if hasattr(
            value,
            "items",
        ):
            try:
                return (
                    AndroidElfParser
                    ._stable_metadata_value(
                        dict(
                            value.items()
                        )
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        return repr(
            value
        )


    @staticmethod
    def _embedded_reference_kind(
        value: str,
    ) -> AndroidElfEmbeddedReferenceKind | None:
        """
        Classify lexical form only.

        This deliberately does not know about sensors, USF, AoC,
        Android services, or any specific device.
        """

        if value.startswith("/"):
            return (
                AndroidElfEmbeddedReferenceKind
                .ABSOLUTE_PATH
            )

        if (
            "." in value
            and not any(
                character.isspace()
                for character in value
            )
            and all(
                (
                    character.isalnum()
                    or character
                    in "._-:+@"
                )
                for character
                in value
            )
        ):
            return (
                AndroidElfEmbeddedReferenceKind
                .DOTTED_IDENTIFIER
            )

        words = value.split()

        if (
            2 <= len(words) <= 6
            and len(value) <= 80
            and all(
                (
                    character.isalnum()
                    or character
                    in " _-"
                )
                for character
                in value
            )
        ):
            return (
                AndroidElfEmbeddedReferenceKind
                .PLAIN_LABEL
            )

        return None

    @classmethod
    def _embedded_references(
        cls,
        elf: ELFFile,
    ) -> tuple[
        ParsedAndroidElfEmbeddedReference,
        ...,
    ]:
        """
        Recover bounded lexical references from runtime-carried ELF data.

        Only SHF_ALLOC, non-executable sections participate. This avoids
        turning debug/symbol payloads or arbitrary file bytes into a giant
        generic strings database.

        Accepted records are NUL-delimited printable ASCII values whose
        lexical form is intrinsically path-like, identifier-like, or a short
        plain label.
        """

        shf_alloc = 0x2
        shf_execinstr = 0x4

        references: list[
            ParsedAndroidElfEmbeddedReference
        ] = []

        for section_index, section in enumerate(
            elf.iter_sections()
        ):
            section_name = section.name

            if not section_name:
                continue

            section_type = section.header[
                "sh_type"
            ]

            if section_type == "SHT_NOBITS":
                continue

            section_flags = int(
                section.header[
                    "sh_flags"
                ]
            )

            if not (
                section_flags
                & shf_alloc
            ):
                continue

            if (
                section_flags
                & shf_execinstr
            ):
                continue

            data = bytes(
                section.data()
            )

            section_file_offset = int(
                section.header[
                    "sh_offset"
                ]
            )

            offset = 0

            while offset < len(data):
                end = data.find(
                    b"\x00",
                    offset,
                )

                if end < 0:
                    end = len(data)

                raw = data[
                    offset:end
                ]

                if (
                    4 <= len(raw) <= 512
                    and all(
                        0x20 <= byte <= 0x7E
                        for byte in raw
                    )
                ):
                    value = raw.decode(
                        "ascii"
                    )

                    kind = (
                        cls
                        ._embedded_reference_kind(
                            value
                        )
                    )

                    if kind is not None:
                        references.append(
                            ParsedAndroidElfEmbeddedReference(
                                kind=kind,
                                section_index=(
                                    section_index
                                ),
                                section_name=(
                                    section_name
                                ),
                                section_byte_offset=(
                                    offset
                                ),
                                file_byte_offset=(
                                    section_file_offset
                                    + offset
                                ),
                                value=value,
                            )
                        )

                offset = end + 1

        return tuple(
            references
        )

    @staticmethod
    def _comments(
        elf: ELFFile,
    ) -> tuple[str, ...]:
        section = (
            elf.get_section_by_name(
                ".comment"
            )
        )

        if section is None:
            return ()

        values: list[
            str
        ] = []

        for raw in (
            section.data()
            .split(
                b"\x00"
            )
        ):
            if not raw:
                continue

            try:
                value = raw.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                value = raw.decode(
                    "utf-8",
                    errors="surrogateescape",
                )

            if (
                value
                and value not in values
            ):
                values.append(
                    value
                )

        return tuple(
            values
        )

    @staticmethod
    def _note_sections(
        elf: ELFFile,
    ) -> tuple[
        ParsedAndroidElfNoteSection,
        ...,
    ]:
        sections: list[
            ParsedAndroidElfNoteSection
        ] = []

        for section in elf.iter_sections():
            if not isinstance(
                section,
                NoteSection,
            ):
                continue

            notes = tuple(
                ParsedAndroidElfNote(
                    index=index,
                    owner=str(
                        note.get(
                            "n_name",
                            "",
                        )
                    ),
                    note_type=str(
                        note.get(
                            "n_type",
                            "",
                        )
                    ),
                    descriptor=(
                        AndroidElfParser
                        ._stable_metadata_value(
                            note.get(
                                "n_desc"
                            )
                        )
                    ),
                )
                for index, note
                in enumerate(
                    section.iter_notes()
                )
            )

            sections.append(
                ParsedAndroidElfNoteSection(
                    section_name=(
                        section.name
                    ),
                    data=bytes(
                        section.data()
                    ),
                    notes=notes,
                )
            )

        return tuple(
            sections
        )

    @staticmethod
    def _attribute_sections(
        elf: ELFFile,
    ) -> tuple[
        ParsedAndroidElfAttributeSection,
        ...,
    ]:
        sections: list[
            ParsedAndroidElfAttributeSection
        ] = []

        for section in elf.iter_sections():
            if not isinstance(
                section,
                AttributesSection,
            ):
                continue

            attributes: list[
                ParsedAndroidElfAttribute
            ] = []

            for subsection_index, subsection in enumerate(
                section.iter_subsections()
            ):
                for (
                    subsubsection_index,
                    subsubsection,
                ) in enumerate(
                    subsection.iter_subsubsections()
                ):
                    for attribute_index, attribute in enumerate(
                        subsubsection.iter_attributes()
                    ):
                        attributes.append(
                            ParsedAndroidElfAttribute(
                                subsection_index=(
                                    subsection_index
                                ),
                                subsubsection_index=(
                                    subsubsection_index
                                ),
                                attribute_index=(
                                    attribute_index
                                ),
                                tag=str(
                                    attribute.tag
                                ),
                                value=(
                                    AndroidElfParser
                                    ._stable_metadata_value(
                                        attribute.value
                                    )
                                ),
                                extra=(
                                    AndroidElfParser
                                    ._stable_metadata_value(
                                        attribute.extra
                                    )
                                    if (
                                        attribute.extra
                                        is not None
                                    )
                                    else None
                                ),
                            )
                        )

            sections.append(
                ParsedAndroidElfAttributeSection(
                    section_name=(
                        section.name
                    ),
                    data=bytes(
                        section.data()
                    ),
                    attributes=tuple(
                        attributes
                    ),
                )
            )

        return tuple(
            sections
        )

    @staticmethod
    def _soong_intermediate_components(
        content: bytes,
    ) -> tuple[str, ...]:
        """
        Recover literal ``android_*`` path components embedded within
        ``out/soong/.intermediates`` paths.

        Parsing proves only that each value is an ``android_*`` component
        carried by a canonical Soong intermediates path. It does not decide
        whether the component is an Android/Soong build tuple. Device-level
        build-tuple interpretation belongs to Universe.
        """

        carrier = b"out/soong/.intermediates/"
        component_prefix = b"android_"

        allowed = frozenset(
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            b"abcdefghijklmnopqrstuvwxyz"
            b"0123456789"
            b"._+-"
        )

        values: list[str] = []
        carrier_offset = 0

        while True:
            carrier_start = content.find(
                carrier,
                carrier_offset,
            )

            if carrier_start < 0:
                break

            # Embedded paths are NUL-delimited in ordinary ELF string
            # populations.  Limit inspection to this one carrier string
            # so unrelated later android_* strings cannot be consumed.
            string_end = content.find(
                b"\x00",
                carrier_start,
            )

            if string_end < 0:
                string_end = len(content)

            path_content = content[
                carrier_start:string_end
            ]

            search_offset = 0

            while True:
                relative_start = path_content.find(
                    b"/" + component_prefix,
                    search_offset,
                )

                if relative_start < 0:
                    break

                start = (
                    relative_start
                    + 1
                )

                end = start

                while (
                    end < len(path_content)
                    and path_content[end] in allowed
                ):
                    end += 1

                if (
                    end < len(path_content)
                    and path_content[end]
                    == ord("/")
                ):
                    raw_value = path_content[
                        start:end
                    ]

                    try:
                        value = raw_value.decode(
                            "ascii"
                        )
                    except UnicodeDecodeError:
                        value = ""

                    if (
                        value
                        and value.startswith(
                            "android_"
                        )
                        and value not in values
                    ):
                        values.append(
                            value
                        )

                search_offset = max(
                    end,
                    relative_start + 1,
                )

            carrier_offset = (
                string_end + 1
            )

        return tuple(
            values
        )

    @staticmethod
    def _elf_class(
        value: int,
    ) -> AndroidElfClass:
        if value == 32:
            return AndroidElfClass.ELF32

        if value == 64:
            return AndroidElfClass.ELF64

        raise AndroidElfParsingError(
            "unsupported ELF class: "
            f"{value}"
        )

    @staticmethod
    def _dynamic_metadata(
        elf: ELFFile,
    ) -> tuple[
        str | None,
        tuple[str, ...],
    ]:
        dynamic = (
            elf.get_section_by_name(
                ".dynamic"
            )
        )

        if dynamic is None:
            return (
                None,
                (),
            )

        soname: str | None = None
        needed: list[str] = []

        for tag in dynamic.iter_tags():
            tag_name = (
                tag.entry.d_tag
            )

            if tag_name == "DT_SONAME":
                value = str(
                    tag.soname
                )

                if value:
                    soname = value

                continue

            if tag_name == "DT_NEEDED":
                dependency = str(
                    tag.needed
                )

                if (
                    dependency
                    and dependency not in needed
                ):
                    needed.append(
                        dependency
                    )

        return (
            soname,
            tuple(
                needed
            ),
        )

    @staticmethod
    def _interpreter(
        elf: ELFFile,
    ) -> str | None:
        for segment in elf.iter_segments():
            if (
                segment.header.p_type
                != "PT_INTERP"
            ):
                continue

            value = (
                segment.get_interp_name()
            )

            if not value:
                return None

            return str(
                value
            )

        return None


class AndroidElfPopulationParser:
    # Parse the complete ELF population visible through canonical
    # parser-ready filesystem roots and canonical Extraction ELF artifacts.
    def __init__(
        self,
        *,
        elf_parser: AndroidElfParser | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.elf_parser = (
            elf_parser
            if elf_parser is not None
            else AndroidElfParser()
        )

        self.progress_callback = (
            progress_callback
        )

    def parse(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
        filesystem_inventory: FilesystemMetadataInventory,
        extraction: AndroidExtractionResult,
    ) -> AndroidElfParsingResult:
        if not isinstance(
            filesystems,
            tuple,
        ):
            raise TypeError(
                "filesystems must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidParserFilesystemSource,
            )
            for value in filesystems
        ):
            raise TypeError(
                "filesystems must contain only "
                "AndroidParserFilesystemSource"
            )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise TypeError(
                "extraction must be an AndroidExtractionResult"
            )

        parsed: list[
            ParsedAndroidElf
        ] = []

        seen: set[
            tuple[
                str,
                PurePosixPath,
            ]
        ] = set()

        for filesystem_source in sorted(
            filesystems,
            key=lambda value: (
                value.source_name
            ),
        ):
            metadata_inventory_entry = (
                self._metadata_inventory_entry(
                    filesystem_source,
                    filesystem_inventory,
                )
            )

            for view in filesystem_source.views:
                candidates = sorted(
                    view.filesystem.walk(),
                    key=lambda path: (
                        path.as_posix()
                    ),
                )

                for host_path in candidates:
                    # ELF Parsing operates on canonical regular-file
                    # filesystem entries. Symlink aliases remain represented
                    # by Filesystem Metadata and must not create independent
                    # physical ELF identities merely because Path.is_file()
                    # follows their targets.
                    if (
                        not host_path.is_file()
                        or host_path.is_symlink()
                    ):
                        continue

                    android_path = (
                        view.android_path_for(
                            host_path
                        )
                    )

                    identity = (
                        filesystem_source.source_name,
                        android_path,
                    )

                    if identity in seen:
                        continue

                    seen.add(
                        identity
                    )

                    metadata_entry = (
                        self._metadata_entry(
                            filesystem_source,
                            metadata_inventory_entry,
                            host_path,
                        )
                    )

                    source = (
                        ParsedAndroidElfSource(
                            filesystem_source=(
                                filesystem_source
                            ),
                            android_path=android_path,
                            host_path=host_path,
                            metadata_entry=metadata_entry,
                        )
                    )

                    if not self.elf_parser.is_elf(
                        source
                    ):
                        continue

                    parsed_elf = (
                        self.elf_parser.parse(
                            source
                        )
                    )

                    parsed.append(
                        parsed_elf
                    )

                    self._report_progress(
                        parsed_elf,
                        processed=len(parsed),
                    )

        embedded_artifacts = tuple(
            sorted(
                (
                    artifact
                    for artifact
                    in extraction.artifacts
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .EMBEDDED_ELF_EXTRACTION
                    )
                ),
                key=lambda artifact: (
                    (
                        artifact.parent.path.as_posix()
                        if artifact.parent is not None
                        else ""
                    ),
                    artifact.semantic_name or "",
                    artifact.path.as_posix(),
                ),
            )
        )

        for artifact in embedded_artifacts:
            source = (
                ParsedAndroidElfSource(
                    filesystem_source=None,
                    android_path=None,
                    host_path=artifact.path,
                    metadata_entry=None,
                    extraction_artifact=artifact,
                )
            )

            if not self.elf_parser.is_elf(
                source
            ):
                raise AndroidElfParsingError(
                    "canonical EMBEDDED_ELF_EXTRACTION artifact "
                    "does not contain ELF magic: "
                    f"{artifact.path}"
                )

            parsed_elf = (
                self.elf_parser.parse(
                    source
                )
            )

            if (
                parsed_elf.source
                .extraction_artifact
                is not artifact
            ):
                raise AndroidElfParsingError(
                    "ELF Parsing failed to preserve exact "
                    "canonical Extraction artifact identity"
                )

            parsed.append(
                parsed_elf
            )

            self._report_progress(
                parsed_elf,
                processed=len(parsed),
            )

        expected_embedded_ids = {
            id(artifact)
            for artifact
            in embedded_artifacts
        }

        parsed_embedded = tuple(
            value
            for value
            in parsed
            if (
                value.source
                .is_extraction_backed
            )
        )

        actual_embedded_ids = {
            id(
                value.source
                .extraction_artifact
            )
            for value
            in parsed_embedded
        }

        if (
            expected_embedded_ids
            != actual_embedded_ids
        ):
            raise AndroidElfParsingError(
                "ELF Parsing failed to conserve the complete "
                "EMBEDDED_ELF_EXTRACTION population"
            )

        if len(
            actual_embedded_ids
        ) != len(
            parsed_embedded
        ):
            raise AndroidElfParsingError(
                "ELF Parsing duplicated a canonical "
                "EMBEDDED_ELF_EXTRACTION artifact"
            )

        return AndroidElfParsingResult(
            elf_files=tuple(
                sorted(
                    parsed,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            )
        )

    def _report_progress(
        self,
        parsed: ParsedAndroidElf,
        *,
        processed: int,
    ) -> None:
        if self.progress_callback is None:
            return

        source = parsed.source

        identity = (
            f"{source.source_name}:"
            f"{source.display_path}"
        )

        details = [
            parsed.elf_class.value,
            parsed.machine,
            parsed.elf_type,
        ]

        if parsed.soname is not None:
            details.append(
                f"SONAME={parsed.soname}"
            )

        if parsed.interpreter is not None:
            details.append(
                f"INTERP={parsed.interpreter}"
            )

        if parsed.needed:
            details.append(
                f"NEEDED={len(parsed.needed)}"
            )

        self.progress_callback(
            ProgressEvent(
                stage="ELF Parsing",
                state=ProgressState.RUNNING,
                current=processed,
                total=None,
                detail="ELF metadata",
                subject=identity,
                operation="decoding ELF metadata",
                item=" · ".join(details),
                processed=processed,
            )
        )

    @staticmethod
    def _metadata_inventory_entry(
        filesystem_source: AndroidParserFilesystemSource,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> FilesystemMetadataInventoryEntry | None:
        """
        Resolve filesystem metadata by exact canonical Extraction identity.

        Partition ownership is provenance context only and must not be used
        to rediscover physical filesystem identity.
        """

        try:
            return filesystem_inventory.entry_for_artifact(
                filesystem_source.artifact
            )
        except KeyError:
            return None

    @staticmethod
    def _metadata_entry(
        filesystem_source: AndroidParserFilesystemSource,
        filesystem_inventory_entry: (
            FilesystemMetadataInventoryEntry
            | None
        ),
        host_path,
    ) -> FilesystemMetadataEntry | None:
        if filesystem_inventory_entry is None:
            return None

        try:
            relative_path = (
                host_path.relative_to(
                    filesystem_source.filesystem.root
                )
            )
        except ValueError:
            return None

        physical_path = (
            "/"
            + relative_path.as_posix()
        )

        entry = (
            filesystem_inventory_entry
            .result
            .metadata
            .get(
                physical_path
            )
        )

        if entry is None:
            return None

        if (
            entry.entry_type
            is not FilesystemEntryType.FILE
        ):
            return None

        return entry
