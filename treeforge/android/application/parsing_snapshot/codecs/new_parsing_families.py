from __future__ import annotations

import base64
from pathlib import PurePosixPath
from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.parsing.certificate import (
    AndroidCertificateEncoding,
    AndroidCertificateParsingResult,
    AndroidOtaCertificateArchiveMember,
    ParsedAndroidCertificateSource,
    ParsedAndroidOtaCertificateArchive,
    ParsedAndroidX509Certificate,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)
from treeforge.android.parsing.font import (
    AndroidFontContainerKind,
    AndroidFontNameRecord,
    AndroidFontParsingResult,
    AndroidFontTable,
    ParsedAndroidFont,
    ParsedAndroidFontFace,
)
from treeforge.android.parsing.input import (
    AndroidInputLexicalLine,
    AndroidInputLexicalLineKind,
    AndroidInputParsingResult,
    ParsedAndroidInputConfiguration,
)
from treeforge.android.parsing.dex import (
    ParsedAndroidDex,
)
from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveMember,
    AndroidJavaArchiveParsingResult,
    AndroidJavaManifestAttribute,
    AndroidJavaManifestLine,
    ParsedAndroidJavaArchive,
)
from treeforge.android.parsing.shell_script import (
    AndroidShellAssignment,
    AndroidShellClasspathEntry,
    AndroidShellCommandObservation,
    AndroidShellExecObservation,
    AndroidShellScriptParsingResult,
    ParsedAndroidShellScript,
)


def _encode_bytes(
    value: bytes,
) -> str:
    if not isinstance(
        value,
        bytes,
    ):
        raise TypeError(
            "snapshot byte payload must be bytes"
        )

    return base64.b64encode(
        value
    ).decode(
        "ascii"
    )


def _decode_bytes(
    value: object,
    *,
    field_name: str,
) -> bytes:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a base64 string"
        )

    try:
        return base64.b64decode(
            value,
            validate=True,
        )
    except ValueError as error:
        raise ValueError(
            f"{field_name} contains invalid base64"
        ) from error


def _required_source(
    decoder: SnapshotGraphDecoder,
    reference: object,
    *,
    field_name: str,
) -> AndroidModelSource:
    source = decoder.ref(
        reference
    )

    if not isinstance(
        source,
        AndroidModelSource,
    ):
        raise TypeError(
            f"{field_name} must restore as an AndroidModelSource"
        )

    return source


# ---------------------------------------------------------------------------
# Android input
# ---------------------------------------------------------------------------


class AndroidInputParsingResultCodec:
    type_tag = "android.input.result"
    python_type = AndroidInputParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidInputParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidInputParsingResult"
            )

        return {
            "configurations": [
                {
                    "source": encoder.ref(
                        configuration.source
                    ),
                    "raw": configuration.raw,
                    "lines": [
                        {
                            "source_line": line.source_line,
                            "raw": line.raw,
                            "content": line.content,
                            "kind": line.kind.value,
                            "tokens": list(
                                line.tokens
                            ),
                            "key": line.key,
                            "value": line.value,
                        }
                        for line
                        in configuration.lines
                    ],
                }
                for configuration
                in value.configurations
            ]
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        configurations_payload = payload[
            "configurations"
        ]

        if not isinstance(
            configurations_payload,
            list,
        ):
            raise TypeError(
                "input configurations must be a list"
            )

        configurations = []

        for configuration_payload in configurations_payload:
            if not isinstance(
                configuration_payload,
                dict,
            ):
                raise TypeError(
                    "input configuration payload must be an object"
                )

            lines_payload = configuration_payload[
                "lines"
            ]

            if not isinstance(
                lines_payload,
                list,
            ):
                raise TypeError(
                    "input lines must be a list"
                )

            lines = tuple(
                AndroidInputLexicalLine(
                    source_line=line_payload[
                        "source_line"
                    ],
                    raw=line_payload[
                        "raw"
                    ],
                    content=line_payload[
                        "content"
                    ],
                    kind=AndroidInputLexicalLineKind(
                        line_payload[
                            "kind"
                        ]
                    ),
                    tokens=tuple(
                        line_payload[
                            "tokens"
                        ]
                    ),
                    key=line_payload[
                        "key"
                    ],
                    value=line_payload[
                        "value"
                    ],
                )
                for line_payload in lines_payload
            )

            configurations.append(
                ParsedAndroidInputConfiguration(
                    source=_required_source(
                        decoder,
                        configuration_payload[
                            "source"
                        ],
                        field_name=(
                            "input configuration source"
                        ),
                    ),
                    raw=configuration_payload[
                        "raw"
                    ],
                    lines=lines,
                )
            )

        return AndroidInputParsingResult(
            configurations=tuple(
                configurations
            )
        )


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------


class AndroidFontParsingResultCodec:
    type_tag = "android.font.result"
    python_type = AndroidFontParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidFontParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidFontParsingResult"
            )

        return {
            "fonts": [
                {
                    "source": encoder.ref(
                        font.source
                    ),
                    "file_size": font.file_size,
                    "container_kind": (
                        font.container_kind.value
                    ),
                    "collection_version": (
                        font.collection_version
                    ),
                    "faces": [
                        {
                            "face_index": (
                                face.face_index
                            ),
                            "offset": face.offset,
                            "sfnt_version": (
                                _encode_bytes(
                                    face.sfnt_version
                                )
                            ),
                            "tables": [
                                {
                                    "tag": table.tag,
                                    "checksum": (
                                        table.checksum
                                    ),
                                    "offset": (
                                        table.offset
                                    ),
                                    "length": (
                                        table.length
                                    ),
                                }
                                for table
                                in face.tables
                            ],
                            "names": [
                                {
                                    "record_index": (
                                        name.record_index
                                    ),
                                    "platform_id": (
                                        name.platform_id
                                    ),
                                    "encoding_id": (
                                        name.encoding_id
                                    ),
                                    "language_id": (
                                        name.language_id
                                    ),
                                    "name_id": (
                                        name.name_id
                                    ),
                                    "raw_value": (
                                        _encode_bytes(
                                            name.raw_value
                                        )
                                    ),
                                    "decoded_value": (
                                        name.decoded_value
                                    ),
                                }
                                for name
                                in face.names
                            ],
                        }
                        for face
                        in font.faces
                    ],
                }
                for font
                in value.fonts
            ]
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        fonts_payload = payload[
            "fonts"
        ]

        if not isinstance(
            fonts_payload,
            list,
        ):
            raise TypeError(
                "font population must be a list"
            )

        fonts = []

        for font_payload in fonts_payload:
            if not isinstance(
                font_payload,
                dict,
            ):
                raise TypeError(
                    "font payload must be an object"
                )

            faces = []

            for face_payload in font_payload[
                "faces"
            ]:
                tables = tuple(
                    AndroidFontTable(
                        tag=table_payload[
                            "tag"
                        ],
                        checksum=table_payload[
                            "checksum"
                        ],
                        offset=table_payload[
                            "offset"
                        ],
                        length=table_payload[
                            "length"
                        ],
                    )
                    for table_payload
                    in face_payload[
                        "tables"
                    ]
                )

                names = tuple(
                    AndroidFontNameRecord(
                        record_index=name_payload[
                            "record_index"
                        ],
                        platform_id=name_payload[
                            "platform_id"
                        ],
                        encoding_id=name_payload[
                            "encoding_id"
                        ],
                        language_id=name_payload[
                            "language_id"
                        ],
                        name_id=name_payload[
                            "name_id"
                        ],
                        raw_value=_decode_bytes(
                            name_payload[
                                "raw_value"
                            ],
                            field_name=(
                                "font name raw_value"
                            ),
                        ),
                        decoded_value=name_payload[
                            "decoded_value"
                        ],
                    )
                    for name_payload
                    in face_payload[
                        "names"
                    ]
                )

                faces.append(
                    ParsedAndroidFontFace(
                        face_index=face_payload[
                            "face_index"
                        ],
                        offset=face_payload[
                            "offset"
                        ],
                        sfnt_version=_decode_bytes(
                            face_payload[
                                "sfnt_version"
                            ],
                            field_name=(
                                "font sfnt_version"
                            ),
                        ),
                        tables=tables,
                        names=names,
                    )
                )

            fonts.append(
                ParsedAndroidFont(
                    source=_required_source(
                        decoder,
                        font_payload[
                            "source"
                        ],
                        field_name=(
                            "font source"
                        ),
                    ),
                    file_size=font_payload[
                        "file_size"
                    ],
                    container_kind=(
                        AndroidFontContainerKind(
                            font_payload[
                                "container_kind"
                            ]
                        )
                    ),
                    collection_version=(
                        font_payload[
                            "collection_version"
                        ]
                    ),
                    faces=tuple(
                        faces
                    ),
                )
            )

        return AndroidFontParsingResult(
            fonts=tuple(
                fonts
            )
        )


# ---------------------------------------------------------------------------
# Shell scripts
# ---------------------------------------------------------------------------


class AndroidShellScriptParsingResultCodec:
    type_tag = "android.shell_script.result"
    python_type = AndroidShellScriptParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidShellScriptParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidShellScriptParsingResult"
            )

        return {
            "scripts": [
                {
                    "source": encoder.ref(
                        script.source
                    ),
                    "raw": script.raw,
                    "shebang": script.shebang,
                    "assignments": [
                        {
                            "index": assignment.index,
                            "line_number": (
                                assignment.line_number
                            ),
                            "name": assignment.name,
                            "raw_value": (
                                assignment.raw_value
                            ),
                            "resolved_value": (
                                assignment.resolved_value
                            ),
                            "exported": (
                                assignment.exported
                            ),
                        }
                        for assignment
                        in script.assignments
                    ],
                    "classpath_entries": [
                        {
                            "assignment_index": (
                                entry.assignment_index
                            ),
                            "index": entry.index,
                            "raw_component": (
                                entry.raw_component
                            ),
                            "resolved_component": (
                                entry.resolved_component
                            ),
                            "resolved_path": (
                                None
                                if entry.resolved_path
                                is None
                                else str(
                                    entry.resolved_path
                                )
                            ),
                        }
                        for entry
                        in script.classpath_entries
                    ],
                    "command_observations": [
                        {
                            "index": observation.index,
                            "line_number": (
                                observation.line_number
                            ),
                            "raw": observation.raw,
                            "argv": list(
                                observation.argv
                            ),
                            "resolved_argv": list(
                                observation.resolved_argv
                            ),
                        }
                        for observation
                        in script.command_observations
                    ],
                    "exec_observations": [
                        {
                            "index": observation.index,
                            "line_number": (
                                observation.line_number
                            ),
                            "raw": observation.raw,
                            "argv": list(
                                observation.argv
                            ),
                            "resolved_argv": list(
                                observation.resolved_argv
                            ),
                        }
                        for observation
                        in script.exec_observations
                    ],
                }
                for script in value.scripts
            ]
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        raw_scripts = payload.get(
            "scripts",
            [],
        )

        if not isinstance(
            raw_scripts,
            list,
        ):
            raise TypeError(
                "shell-script scripts must be a list"
            )

        scripts = []

        for raw_script in raw_scripts:
            if not isinstance(
                raw_script,
                dict,
            ):
                raise TypeError(
                    "shell-script entry must be a dict"
                )

            source = _required_source(
                decoder,
                raw_script[
                    "source"
                ],
                field_name=(
                    "shell-script source"
                ),
            )

            assignments = tuple(
                AndroidShellAssignment(
                    index=int(
                        item[
                            "index"
                        ]
                    ),
                    line_number=int(
                        item[
                            "line_number"
                        ]
                    ),
                    name=item[
                        "name"
                    ],
                    raw_value=item[
                        "raw_value"
                    ],
                    resolved_value=item.get(
                        "resolved_value"
                    ),
                    exported=bool(
                        item.get(
                            "exported",
                            False,
                        )
                    ),
                )
                for item
                in raw_script.get(
                    "assignments",
                    [],
                )
            )

            classpath_entries = tuple(
                AndroidShellClasspathEntry(
                    assignment_index=int(
                        item[
                            "assignment_index"
                        ]
                    ),
                    index=int(
                        item[
                            "index"
                        ]
                    ),
                    raw_component=item[
                        "raw_component"
                    ],
                    resolved_component=item.get(
                        "resolved_component"
                    ),
                    resolved_path=(
                        None
                        if item.get(
                            "resolved_path"
                        )
                        is None
                        else PurePosixPath(
                            item[
                                "resolved_path"
                            ]
                        )
                    ),
                )
                for item
                in raw_script.get(
                    "classpath_entries",
                    [],
                )
            )

            command_observations = tuple(
                AndroidShellCommandObservation(
                    index=int(
                        item[
                            "index"
                        ]
                    ),
                    line_number=int(
                        item[
                            "line_number"
                        ]
                    ),
                    raw=item[
                        "raw"
                    ],
                    argv=tuple(
                        item.get(
                            "argv",
                            [],
                        )
                    ),
                    resolved_argv=tuple(
                        item.get(
                            "resolved_argv",
                            [],
                        )
                    ),
                )
                for item
                in raw_script.get(
                    "command_observations",
                    [],
                )
            )

            exec_observations = tuple(
                AndroidShellExecObservation(
                    index=int(
                        item[
                            "index"
                        ]
                    ),
                    line_number=int(
                        item[
                            "line_number"
                        ]
                    ),
                    raw=item[
                        "raw"
                    ],
                    argv=tuple(
                        item.get(
                            "argv",
                            [],
                        )
                    ),
                    resolved_argv=tuple(
                        item.get(
                            "resolved_argv",
                            [],
                        )
                    ),
                )
                for item
                in raw_script.get(
                    "exec_observations",
                    [],
                )
            )

            scripts.append(
                ParsedAndroidShellScript(
                    source=source,
                    raw=raw_script[
                        "raw"
                    ],
                    shebang=raw_script[
                        "shebang"
                    ],
                    assignments=assignments,
                    classpath_entries=(
                        classpath_entries
                    ),
                    command_observations=(
                        command_observations
                    ),
                    exec_observations=(
                        exec_observations
                    ),
                )
            )

        return AndroidShellScriptParsingResult(
            scripts=tuple(
                scripts
            )
        )


# ---------------------------------------------------------------------------
# Installed Java archives
# ---------------------------------------------------------------------------


class AndroidJavaArchiveParsingResultCodec:
    type_tag = "android.java_archive.result"
    python_type = AndroidJavaArchiveParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidJavaArchiveParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidJavaArchiveParsingResult"
            )

        return {
            "archives": [
                {
                    "source": encoder.ref(
                        archive.source
                    ),
                    "file_size": (
                        archive.file_size
                    ),
                    "members": [
                        {
                            "index": member.index,
                            "filename": (
                                member.filename
                            ),
                            "compression_method": (
                                member.compression_method
                            ),
                            "crc32": member.crc32,
                            "compressed_size": (
                                member.compressed_size
                            ),
                            "uncompressed_size": (
                                member.uncompressed_size
                            ),
                            "external_attributes": (
                                member.external_attributes
                            ),
                            "is_directory": (
                                member.is_directory
                            ),
                        }
                        for member
                        in archive.members
                    ],
                    "manifest_raw": (
                        None
                        if archive.manifest_raw
                        is None
                        else _encode_bytes(
                            archive.manifest_raw
                        )
                    ),
                    "manifest_text": (
                        archive.manifest_text
                    ),
                    "manifest_attributes": [
                        {
                            "index": attribute.index,
                            "name": attribute.name,
                            "value": attribute.value,
                        }
                        for attribute
                        in archive.manifest_attributes
                    ],
                    "manifest_lines": [
                        {
                            "index": line.index,
                            "raw": line.raw,
                            "parsed": line.parsed,
                            "name": line.name,
                            "value": line.value,
                        }
                        for line
                        in archive.manifest_lines
                    ],
                    "dex_entries": list(
                        archive.dex_entries
                    ),
                    "dex_files": [
                        encoder.ref(
                            dex_file
                        )
                        for dex_file
                        in archive.dex_files
                    ],
                    "has_android_resource_table": (
                        archive.has_android_resource_table
                    ),
                    "android_resource_member_count": (
                        archive.android_resource_member_count
                    ),
                }
                for archive
                in value.archives
            ]
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        archives_payload = payload[
            "archives"
        ]

        if not isinstance(
            archives_payload,
            list,
        ):
            raise TypeError(
                "Java archive population must be a list"
            )

        archives = []

        for archive_payload in archives_payload:
            manifest_raw_payload = archive_payload[
                "manifest_raw"
            ]

            manifest_raw = (
                None
                if manifest_raw_payload is None
                else _decode_bytes(
                    manifest_raw_payload,
                    field_name=(
                        "Java archive manifest_raw"
                    ),
                )
            )

            source = _required_source(
                decoder,
                archive_payload[
                    "source"
                ],
                field_name=(
                    "Java archive source"
                ),
            )

            dex_files = tuple(
                decoder.ref(
                    reference
                )
                for reference
                in archive_payload.get(
                    "dex_files",
                    [],
                )
            )

            if not all(
                isinstance(
                    dex_file,
                    ParsedAndroidDex,
                )
                for dex_file
                in dex_files
            ):
                raise TypeError(
                    "restored Java archive DEX population "
                    "contains invalid types"
                )

            archives.append(
                ParsedAndroidJavaArchive(
                    source=source,
                    file_size=archive_payload[
                        "file_size"
                    ],
                    members=tuple(
                        AndroidJavaArchiveMember(
                            index=member_payload[
                                "index"
                            ],
                            filename=member_payload[
                                "filename"
                            ],
                            compression_method=(
                                member_payload[
                                    "compression_method"
                                ]
                            ),
                            crc32=member_payload[
                                "crc32"
                            ],
                            compressed_size=(
                                member_payload[
                                    "compressed_size"
                                ]
                            ),
                            uncompressed_size=(
                                member_payload[
                                    "uncompressed_size"
                                ]
                            ),
                            external_attributes=(
                                member_payload[
                                    "external_attributes"
                                ]
                            ),
                            is_directory=(
                                member_payload[
                                    "is_directory"
                                ]
                            ),
                        )
                        for member_payload
                        in archive_payload[
                            "members"
                        ]
                    ),
                    manifest_raw=manifest_raw,
                    manifest_text=archive_payload[
                        "manifest_text"
                    ],
                    manifest_attributes=tuple(
                        AndroidJavaManifestAttribute(
                            index=attribute_payload[
                                "index"
                            ],
                            name=attribute_payload[
                                "name"
                            ],
                            value=attribute_payload[
                                "value"
                            ],
                        )
                        for attribute_payload
                        in archive_payload[
                            "manifest_attributes"
                        ]
                    ),
                    manifest_lines=tuple(
                        AndroidJavaManifestLine(
                            index=line_payload[
                                "index"
                            ],
                            raw=line_payload[
                                "raw"
                            ],
                            parsed=line_payload[
                                "parsed"
                            ],
                            name=line_payload.get(
                                "name"
                            ),
                            value=line_payload.get(
                                "value"
                            ),
                        )
                        for line_payload
                        in archive_payload.get(
                            "manifest_lines",
                            [],
                        )
                    ),
                    dex_entries=tuple(
                        archive_payload[
                            "dex_entries"
                        ]
                    ),
                    dex_files=dex_files,
                    has_android_resource_table=(
                        archive_payload[
                            "has_android_resource_table"
                        ]
                    ),
                    android_resource_member_count=(
                        archive_payload[
                            "android_resource_member_count"
                        ]
                    ),
                )
            )

        return AndroidJavaArchiveParsingResult(
            archives=tuple(
                archives
            )
        )


# ---------------------------------------------------------------------------
# Certificates/security
# ---------------------------------------------------------------------------


def _encode_x509(
    value: ParsedAndroidX509Certificate,
) -> dict[str, Any]:
    return {
        "index": value.index,
        "raw_der": _encode_bytes(
            value.raw_der
        ),
        "sha256_fingerprint": (
            value.sha256_fingerprint
        ),
        "sha1_fingerprint": (
            value.sha1_fingerprint
        ),
        "serial_number": (
            value.serial_number
        ),
        "signature_algorithm_oid": (
            value.signature_algorithm_oid
        ),
        "issuer_der": _encode_bytes(
            value.issuer_der
        ),
        "subject_der": _encode_bytes(
            value.subject_der
        ),
        "not_before_raw": (
            value.not_before_raw
        ),
        "not_after_raw": (
            value.not_after_raw
        ),
        "subject_public_key_algorithm_oid": (
            value.subject_public_key_algorithm_oid
        ),
        "subject_public_key_info_sha256": (
            value.subject_public_key_info_sha256
        ),
    }


def _decode_x509(
    payload: object,
) -> ParsedAndroidX509Certificate:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "X.509 snapshot payload must be an object"
        )

    return ParsedAndroidX509Certificate(
        index=payload[
            "index"
        ],
        raw_der=_decode_bytes(
            payload[
                "raw_der"
            ],
            field_name=(
                "X.509 raw_der"
            ),
        ),
        sha256_fingerprint=payload[
            "sha256_fingerprint"
        ],
        sha1_fingerprint=payload[
            "sha1_fingerprint"
        ],
        serial_number=payload[
            "serial_number"
        ],
        signature_algorithm_oid=payload[
            "signature_algorithm_oid"
        ],
        issuer_der=_decode_bytes(
            payload[
                "issuer_der"
            ],
            field_name=(
                "X.509 issuer_der"
            ),
        ),
        subject_der=_decode_bytes(
            payload[
                "subject_der"
            ],
            field_name=(
                "X.509 subject_der"
            ),
        ),
        not_before_raw=payload[
            "not_before_raw"
        ],
        not_after_raw=payload[
            "not_after_raw"
        ],
        subject_public_key_algorithm_oid=payload[
            "subject_public_key_algorithm_oid"
        ],
        subject_public_key_info_sha256=payload[
            "subject_public_key_info_sha256"
        ],
    )


class AndroidCertificateParsingResultCodec:
    type_tag = "android.certificate.result"
    python_type = AndroidCertificateParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidCertificateParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidCertificateParsingResult"
            )

        return {
            "sources": [
                {
                    "source": encoder.ref(
                        source.source
                    ),
                    "raw": _encode_bytes(
                        source.raw
                    ),
                    "encoding": (
                        source.encoding.value
                    ),
                    "certificates": [
                        _encode_x509(
                            certificate
                        )
                        for certificate
                        in source.certificates
                    ],
                }
                for source
                in value.sources
            ],
            "ota_archives": [
                {
                    "source": encoder.ref(
                        archive.source
                    ),
                    "file_size": (
                        archive.file_size
                    ),
                    "members": [
                        {
                            "index": member.index,
                            "filename": (
                                member.filename
                            ),
                            "compression_method": (
                                member.compression_method
                            ),
                            "crc32": member.crc32,
                            "compressed_size": (
                                member.compressed_size
                            ),
                            "uncompressed_size": (
                                member.uncompressed_size
                            ),
                            "sha256": member.sha256,
                            "certificates": [
                                _encode_x509(
                                    certificate
                                )
                                for certificate
                                in member.certificates
                            ],
                        }
                        for member
                        in archive.members
                    ],
                }
                for archive
                in value.ota_archives
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        sources_payload = payload[
            "sources"
        ]
        archives_payload = payload[
            "ota_archives"
        ]

        if not isinstance(
            sources_payload,
            list,
        ):
            raise TypeError(
                "certificate sources must be a list"
            )

        if not isinstance(
            archives_payload,
            list,
        ):
            raise TypeError(
                "OTA certificate archives must be a list"
            )

        sources = tuple(
            ParsedAndroidCertificateSource(
                source=_required_source(
                    decoder,
                    source_payload[
                        "source"
                    ],
                    field_name=(
                        "certificate source"
                    ),
                ),
                raw=_decode_bytes(
                    source_payload[
                        "raw"
                    ],
                    field_name=(
                        "certificate source raw"
                    ),
                ),
                encoding=(
                    AndroidCertificateEncoding(
                        source_payload[
                            "encoding"
                        ]
                    )
                ),
                certificates=tuple(
                    _decode_x509(
                        certificate_payload
                    )
                    for certificate_payload
                    in source_payload[
                        "certificates"
                    ]
                ),
            )
            for source_payload
            in sources_payload
        )

        ota_archives = tuple(
            ParsedAndroidOtaCertificateArchive(
                source=_required_source(
                    decoder,
                    archive_payload[
                        "source"
                    ],
                    field_name=(
                        "OTA certificate archive source"
                    ),
                ),
                file_size=archive_payload[
                    "file_size"
                ],
                members=tuple(
                    AndroidOtaCertificateArchiveMember(
                        index=member_payload[
                            "index"
                        ],
                        filename=member_payload[
                            "filename"
                        ],
                        compression_method=(
                            member_payload[
                                "compression_method"
                            ]
                        ),
                        crc32=member_payload[
                            "crc32"
                        ],
                        compressed_size=(
                            member_payload[
                                "compressed_size"
                            ]
                        ),
                        uncompressed_size=(
                            member_payload[
                                "uncompressed_size"
                            ]
                        ),
                        sha256=member_payload[
                            "sha256"
                        ],
                        certificates=tuple(
                            _decode_x509(
                                certificate_payload
                            )
                            for certificate_payload
                            in member_payload[
                                "certificates"
                            ]
                        ),
                    )
                    for member_payload
                    in archive_payload[
                        "members"
                    ]
                ),
            )
            for archive_payload
            in archives_payload
        )

        return AndroidCertificateParsingResult(
            sources=sources,
            ota_archives=ota_archives,
        )


NEW_PARSING_FAMILY_CODECS = (
    AndroidInputParsingResultCodec(),
    AndroidFontParsingResultCodec(),
    AndroidJavaArchiveParsingResultCodec(),
    AndroidCertificateParsingResultCodec(),
)
