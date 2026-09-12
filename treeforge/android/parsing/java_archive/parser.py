from __future__ import annotations

from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.parsing.dex import (
    AndroidDexParser,
    AndroidDexSource,
    AndroidDexSourceKind,
)


from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.java_archive.model import (
    AndroidJavaArchiveMember,
    AndroidJavaArchiveParsingResult,
    AndroidJavaManifestAttribute,
    AndroidJavaManifestLine,
    ParsedAndroidJavaArchive,
)


class AndroidJavaArchiveParsingError(ValueError):
    """
    Raised when a positively identified installed JAR cannot be represented
    faithfully as a ZIP/JAR container.
    """


class AndroidJavaArchiveParser:
    """
    Parse intrinsic installed JAR/ZIP structure.

    Parsing records exact source identity, central-directory entries,
    MANIFEST.MF bytes and lexical attributes, DEX member identity, and
    Android resource-container presence.

    It does not decode DEX semantics, infer classpath participation, assign
    source ownership, infer build modules, or reconcile archives.
    """

    _MANIFEST_PATH = (
        "META-INF/MANIFEST.MF"
    )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidJavaArchiveParsingResult:
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
                is AndroidModelSourceKind.JAVA_ARCHIVE
            )
        )

        archives = tuple(
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
            id(archive.source)
            for archive
            in archives
        }

        if (
            expected_source_ids
            != actual_source_ids
        ):
            raise AndroidJavaArchiveParsingError(
                "Java archive Parsing failed to conserve the "
                "complete canonical JAVA_ARCHIVE source population"
            )

        if len(
            actual_source_ids
        ) != len(
            archives
        ):
            raise AndroidJavaArchiveParsingError(
                "Java archive Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return AndroidJavaArchiveParsingResult(
            archives=tuple(
                sorted(
                    archives,
                    key=lambda archive: (
                        archive.source.identity_key
                    ),
                )
            )
        )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidJavaArchive:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            source.kind
            is not AndroidModelSourceKind.JAVA_ARCHIVE
        ):
            raise ValueError(
                "source must be a JAVA_ARCHIVE source"
            )

        try:
            file_size = (
                source.host_path.stat().st_size
            )

            with ZipFile(
                source.host_path,
                "r",
            ) as archive:
                infos = tuple(
                    archive.infolist()
                )

                members = tuple(
                    AndroidJavaArchiveMember(
                        index=index,
                        filename=info.filename,
                        compression_method=(
                            info.compress_type
                        ),
                        crc32=info.CRC,
                        compressed_size=(
                            info.compress_size
                        ),
                        uncompressed_size=(
                            info.file_size
                        ),
                        external_attributes=(
                            info.external_attr
                        ),
                        is_directory=(
                            info.is_dir()
                        ),
                    )
                    for index, info
                    in enumerate(
                        infos
                    )
                )

                member_names = tuple(
                    info.filename
                    for info in infos
                )

                manifest_raw = (
                    archive.read(
                        self._MANIFEST_PATH
                    )
                    if self._MANIFEST_PATH
                    in member_names
                    else None
                )

                dex_parser = AndroidDexParser()

                dex_files = tuple(
                    dex_parser.parse(
                        payload=archive.read(
                            infos[
                                member.index
                            ]
                        ),
                        source=AndroidDexSource(
                            kind=(
                                AndroidDexSourceKind
                                .JAVA_ARCHIVE_MEMBER
                            ),
                            parent=source,
                            parent_source_name=(
                                source.source_name
                            ),
                            parent_android_path=(
                                source.android_path
                            ),
                            member_name=(
                                member.filename
                            ),
                            member_index=(
                                member.index
                            ),
                        ),
                    )
                    for member
                    in members
                    if (
                        not member.is_directory
                        and self._is_dex_member(
                            member.filename
                        )
                    )
                )

        except (
            OSError,
            BadZipFile,
            KeyError,
        ) as error:
            raise AndroidJavaArchiveParsingError(
                "unable to parse installed Java archive "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        if file_size < 1:
            raise AndroidJavaArchiveParsingError(
                "installed Java archive is empty: "
                f"{source.source_name}:"
                f"{source.android_path}"
            )

        (
            manifest_text,
            manifest_attributes,
            manifest_lines,
        ) = self._parse_manifest(
            manifest_raw
        )

        dex_entries = tuple(
            member.filename
            for member in members
            if (
                not member.is_directory
                and self._is_dex_member(
                    member.filename
                )
            )
        )

        resource_member_count = sum(
            1
            for member in members
            if (
                not member.is_directory
                and (
                    member.filename
                    == "resources.arsc"
                    or member.filename.startswith(
                        "res/"
                    )
                )
            )
        )

        return ParsedAndroidJavaArchive(
            source=source,
            file_size=file_size,
            members=members,
            manifest_raw=manifest_raw,
            manifest_text=manifest_text,
            manifest_attributes=(
                manifest_attributes
            ),
            manifest_lines=(
                manifest_lines
            ),
            dex_entries=dex_entries,
            dex_files=dex_files,
            has_android_resource_table=(
                any(
                    member.filename
                    == "resources.arsc"
                    for member in members
                    if not member.is_directory
                )
            ),
            android_resource_member_count=(
                resource_member_count
            ),
        )

    @staticmethod
    def _is_dex_member(
        filename: str,
    ) -> bool:
        if filename == "classes.dex":
            return True

        if (
            filename.startswith(
                "classes"
            )
            and filename.endswith(
                ".dex"
            )
        ):
            middle = filename[
                len("classes"):
                -len(".dex")
            ]

            return bool(
                middle
            ) and middle.isdigit()

        return False

    @classmethod
    def _parse_manifest(
        cls,
        raw: bytes | None,
    ) -> tuple[
        str | None,
        tuple[
            AndroidJavaManifestAttribute,
            ...,
        ],
        tuple[
            AndroidJavaManifestLine,
            ...,
        ],
    ]:
        if raw is None:
            return (
                None,
                (),
                (),
            )

        try:
            text = raw.decode(
                "utf-8"
            )
        except UnicodeDecodeError:
            return (
                None,
                (),
                (),
            )

        physical_lines = (
            text
            .replace(
                "\r\n",
                "\n",
            )
            .replace(
                "\r",
                "\n",
            )
            .split(
                "\n"
            )
        )

        logical_lines: list[
            str
        ] = []

        for line in physical_lines:
            if (
                line.startswith(" ")
                and logical_lines
            ):
                logical_lines[-1] += (
                    line[1:]
                )
            else:
                logical_lines.append(
                    line
                )

        attributes = []
        lines = []

        for line in logical_lines:
            if not line:
                continue

            name, separator, value = (
                line.partition(
                    ":"
                )
            )

            if (
                not separator
                or not name
            ):
                lines.append(
                    AndroidJavaManifestLine(
                        index=len(lines),
                        raw=line,
                        parsed=False,
                    )
                )
                continue

            if value.startswith(
                " "
            ):
                value = value[1:]

            attributes.append(
                AndroidJavaManifestAttribute(
                    index=len(
                        attributes
                    ),
                    name=name,
                    value=value,
                )
            )

            lines.append(
                AndroidJavaManifestLine(
                    index=len(lines),
                    raw=line,
                    parsed=True,
                    name=name,
                    value=value,
                )
            )

        return (
            text,
            tuple(
                attributes
            ),
            tuple(
                lines
            ),
        )

