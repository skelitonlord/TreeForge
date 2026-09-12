from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.init.provenance import (
    SourceLocation,
    SourceOrigin,
)
from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidFstab,
    ParsedAndroidInitSource,
    ParsedAndroidPropertyFile,
    ParsedAndroidUeventd,
    ParsedAndroidVintfSource,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.fstab import (
    AndroidFstabDeclaration,
    AndroidFstabUnparsedLine,
)
from treeforge.android.parsing.init import (
    AndroidInitAction,
    AndroidInitCommand,
    AndroidInitImport,
    AndroidInitService,
    AndroidInitServiceOption,
    AndroidInitUnparsedLine,
)
from treeforge.android.parsing.vintf import (
    ParsedVintfDocument,
    VintfXmlAttribute,
    VintfXmlElement,
)
from treeforge.android.properties import (
    AndroidPropertyDeclaration,
    AndroidPropertySourceKind,
    AndroidPropertyUnparsedLine,
)


def _path(
    value: Path | None,
) -> str | None:
    return (
        str(value)
        if value is not None
        else None
    )


def _pure_path(
    value: PurePosixPath | None,
) -> str | None:
    return (
        str(value)
        if value is not None
        else None
    )


def _decode_path(
    value: object,
) -> Path | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "path payload must be a string or None"
        )

    return Path(
        value
    )


def _decode_pure_path(
    value: object,
) -> PurePosixPath | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "Android path payload must be "
            "a string or None"
        )

    return PurePosixPath(
        value
    )


def _strings(
    value: object,
    *,
    field: str,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError(
            f"{field} must be a list"
        )

    if not all(
        isinstance(
            item,
            str,
        )
        for item in value
    ):
        raise TypeError(
            f"{field} must contain only strings"
        )

    return tuple(
        value
    )


def _source_location_to_dict(
    value: SourceLocation,
) -> dict[str, Any]:
    return {
        "file": _path(
            value.file
        ),
        "line": value.line,
        "column": value.column,
        "origin": value.origin.value,
        "imported_from": _path(
            value.imported_from
        ),
        "android_path": _pure_path(
            value.android_path
        ),
    }


def _source_location_from_dict(
    payload: object,
) -> SourceLocation:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "SourceLocation payload must be a dict"
        )

    return SourceLocation(
        file=_decode_path(
            payload.get(
                "file"
            )
        ),
        line=payload.get(
            "line"
        ),
        column=payload.get(
            "column"
        ),
        origin=SourceOrigin(
            payload[
                "origin"
            ]
        ),
        imported_from=_decode_path(
            payload.get(
                "imported_from"
            )
        ),
        android_path=_decode_pure_path(
            payload.get(
                "android_path"
            )
        ),
    )


def _init_import_to_dict(
    value: AndroidInitImport,
) -> dict[str, Any]:
    return {
        "path": value.path,
        "location": _source_location_to_dict(
            value.location
        ),
        "raw": value.raw,
    }


def _init_import_from_dict(
    payload: dict[str, Any],
) -> AndroidInitImport:
    return AndroidInitImport(
        path=payload[
            "path"
        ],
        location=_source_location_from_dict(
            payload[
                "location"
            ]
        ),
        raw=payload[
            "raw"
        ],
    )


def _service_option_to_dict(
    value: AndroidInitServiceOption,
) -> dict[str, Any]:
    return {
        "keyword": value.keyword,
        "arguments": list(
            value.arguments
        ),
        "location": _source_location_to_dict(
            value.location
        ),
        "raw": value.raw,
    }


def _service_option_from_dict(
    payload: dict[str, Any],
) -> AndroidInitServiceOption:
    return AndroidInitServiceOption(
        keyword=payload[
            "keyword"
        ],
        arguments=_strings(
            payload[
                "arguments"
            ],
            field="arguments",
        ),
        location=_source_location_from_dict(
            payload[
                "location"
            ]
        ),
        raw=payload[
            "raw"
        ],
    )


def _service_to_dict(
    value: AndroidInitService,
) -> dict[str, Any]:
    return {
        "name": value.name,
        "executable": value.executable,
        "arguments": list(
            value.arguments
        ),
        "options": [
            _service_option_to_dict(
                option
            )
            for option in value.options
        ],
        "location": _source_location_to_dict(
            value.location
        ),
        "raw_header": value.raw_header,
    }


def _service_from_dict(
    payload: dict[str, Any],
) -> AndroidInitService:
    options = payload[
        "options"
    ]

    if not isinstance(
        options,
        list,
    ):
        raise TypeError(
            "service options must be a list"
        )

    return AndroidInitService(
        name=payload[
            "name"
        ],
        executable=payload[
            "executable"
        ],
        arguments=_strings(
            payload[
                "arguments"
            ],
            field="arguments",
        ),
        options=tuple(
            _service_option_from_dict(
                option
            )
            for option in options
        ),
        location=_source_location_from_dict(
            payload[
                "location"
            ]
        ),
        raw_header=payload[
            "raw_header"
        ],
    )


def _command_to_dict(
    value: AndroidInitCommand,
) -> dict[str, Any]:
    return {
        "keyword": value.keyword,
        "arguments": list(
            value.arguments
        ),
        "location": _source_location_to_dict(
            value.location
        ),
        "raw": value.raw,
    }


def _command_from_dict(
    payload: dict[str, Any],
) -> AndroidInitCommand:
    return AndroidInitCommand(
        keyword=payload[
            "keyword"
        ],
        arguments=_strings(
            payload[
                "arguments"
            ],
            field="arguments",
        ),
        location=_source_location_from_dict(
            payload[
                "location"
            ]
        ),
        raw=payload[
            "raw"
        ],
    )


def _action_to_dict(
    value: AndroidInitAction,
) -> dict[str, Any]:
    return {
        "trigger": value.trigger,
        "commands": [
            _command_to_dict(
                command
            )
            for command in value.commands
        ],
        "location": _source_location_to_dict(
            value.location
        ),
        "raw_header": value.raw_header,
    }


def _action_from_dict(
    payload: dict[str, Any],
) -> AndroidInitAction:
    commands = payload[
        "commands"
    ]

    if not isinstance(
        commands,
        list,
    ):
        raise TypeError(
            "action commands must be a list"
        )

    return AndroidInitAction(
        trigger=payload[
            "trigger"
        ],
        commands=tuple(
            _command_from_dict(
                command
            )
            for command in commands
        ),
        location=_source_location_from_dict(
            payload[
                "location"
            ]
        ),
        raw_header=payload[
            "raw_header"
        ],
    )


def _init_unparsed_to_dict(
    value: AndroidInitUnparsedLine,
) -> dict[str, Any]:
    return {
        "line_number": value.line_number,
        "raw": value.raw,
        "reason": value.reason,
    }


def _init_unparsed_from_dict(
    payload: dict[str, Any],
) -> AndroidInitUnparsedLine:
    return AndroidInitUnparsedLine(
        line_number=payload[
            "line_number"
        ],
        raw=payload[
            "raw"
        ],
        reason=payload[
            "reason"
        ],
    )


def _fstab_declaration_to_dict(
    value: AndroidFstabDeclaration,
) -> dict[str, Any]:
    return {
        "device": value.device,
        "mount_point": value.mount_point,
        "fs_type": value.fs_type,
        "mount_options": list(
            value.mount_options
        ),
        "fs_mgr_flags": list(
            value.fs_mgr_flags
        ),
        "line_number": value.line_number,
        "raw": value.raw,
    }


def _fstab_declaration_from_dict(
    payload: dict[str, Any],
) -> AndroidFstabDeclaration:
    return AndroidFstabDeclaration(
        device=payload[
            "device"
        ],
        mount_point=payload[
            "mount_point"
        ],
        fs_type=payload[
            "fs_type"
        ],
        mount_options=_strings(
            payload[
                "mount_options"
            ],
            field="mount_options",
        ),
        fs_mgr_flags=_strings(
            payload[
                "fs_mgr_flags"
            ],
            field="fs_mgr_flags",
        ),
        line_number=payload[
            "line_number"
        ],
        raw=payload[
            "raw"
        ],
    )


def _fstab_unparsed_to_dict(
    value: AndroidFstabUnparsedLine,
) -> dict[str, Any]:
    return {
        "line_number": value.line_number,
        "raw": value.raw,
        "reason": value.reason,
    }


def _fstab_unparsed_from_dict(
    payload: dict[str, Any],
) -> AndroidFstabUnparsedLine:
    return AndroidFstabUnparsedLine(
        line_number=payload[
            "line_number"
        ],
        raw=payload[
            "raw"
        ],
        reason=payload[
            "reason"
        ],
    )


def _property_declaration_to_dict(
    value: AndroidPropertyDeclaration,
) -> dict[str, Any]:
    return {
        "key": value.key,
        "value": value.value,
        "line_number": value.line_number,
        "raw": value.raw,
    }


def _property_declaration_from_dict(
    payload: dict[str, Any],
) -> AndroidPropertyDeclaration:
    return AndroidPropertyDeclaration(
        key=payload[
            "key"
        ],
        value=payload[
            "value"
        ],
        line_number=payload[
            "line_number"
        ],
        raw=payload[
            "raw"
        ],
    )


def _property_unparsed_to_dict(
    value: AndroidPropertyUnparsedLine,
) -> dict[str, Any]:
    return {
        "line_number": value.line_number,
        "raw": value.raw,
        "reason": value.reason,
    }


def _property_unparsed_from_dict(
    payload: dict[str, Any],
) -> AndroidPropertyUnparsedLine:
    return AndroidPropertyUnparsedLine(
        line_number=payload[
            "line_number"
        ],
        raw=payload[
            "raw"
        ],
        reason=payload[
            "reason"
        ],
    )


def _vintf_element_to_dict(
    value: VintfXmlElement,
) -> dict[str, Any]:
    return {
        "tag": value.tag,
        "attributes": [
            {
                "name": attribute.name,
                "value": attribute.value,
            }
            for attribute in value.attributes
        ],
        "text": value.text,
        "tail": value.tail,
        "children": [
            _vintf_element_to_dict(
                child
            )
            for child in value.children
        ],
    }


def _vintf_element_from_dict(
    payload: dict[str, Any],
) -> VintfXmlElement:
    attributes = payload[
        "attributes"
    ]

    children = payload[
        "children"
    ]

    if not isinstance(
        attributes,
        list,
    ):
        raise TypeError(
            "VINTF attributes must be a list"
        )

    if not isinstance(
        children,
        list,
    ):
        raise TypeError(
            "VINTF children must be a list"
        )

    return VintfXmlElement(
        tag=payload[
            "tag"
        ],
        attributes=tuple(
            VintfXmlAttribute(
                name=attribute[
                    "name"
                ],
                value=attribute[
                    "value"
                ],
            )
            for attribute in attributes
        ),
        text=payload.get(
            "text"
        ),
        tail=payload.get(
            "tail"
        ),
        children=tuple(
            _vintf_element_from_dict(
                child
            )
            for child in children
        ),
    )


def _decode_filesystem_source(
    decoder: SnapshotGraphDecoder,
    reference: object,
) -> AndroidParserFilesystemSource:
    source = decoder.ref(
        reference
    )

    if not isinstance(
        source,
        AndroidParserFilesystemSource,
    ):
        raise TypeError(
            "restored filesystem_source must be an "
            "AndroidParserFilesystemSource"
        )

    return source


class ParsedAndroidInitSourceCodec:
    type_tag = "android.parsed.init_source"
    python_type = ParsedAndroidInitSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidInitSource,
        ):
            raise TypeError(
                "value must be a ParsedAndroidInitSource"
            )

        return {
            "source_path": str(
                value.source_path
            ),
            "raw": value.raw,
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "source": (
                encoder.ref(
                    value.source
                )
                if value.source is not None
                else None
            ),
            "android_path": _pure_path(
                value.android_path
            ),
            "imports": [
                _init_import_to_dict(
                    item
                )
                for item in value.imports
            ],
            "services": [
                _service_to_dict(
                    item
                )
                for item in value.services
            ],
            "actions": [
                _action_to_dict(
                    item
                )
                for item in value.actions
            ],
            "unparsed_lines": [
                _init_unparsed_to_dict(
                    item
                )
                for item in value.unparsed_lines
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidInitSource(
            source=(
                decoder.ref(
                    payload["source"]
                )
                if payload["source"] is not None
                else None
            ),
            source_path=Path(
                payload[
                    "source_path"
                ]
            ),
            raw=payload[
                "raw"
            ],
            filesystem_source=_decode_filesystem_source(
                decoder,
                payload[
                    "filesystem_source"
                ],
            ),
            android_path=_decode_pure_path(
                payload.get(
                    "android_path"
                )
            ),
            imports=tuple(
                _init_import_from_dict(
                    item
                )
                for item in payload[
                    "imports"
                ]
            ),
            services=tuple(
                _service_from_dict(
                    item
                )
                for item in payload[
                    "services"
                ]
            ),
            actions=tuple(
                _action_from_dict(
                    item
                )
                for item in payload[
                    "actions"
                ]
            ),
            unparsed_lines=tuple(
                _init_unparsed_from_dict(
                    item
                )
                for item in payload[
                    "unparsed_lines"
                ]
            ),
        )


class ParsedAndroidFstabCodec:
    type_tag = "android.parsed.fstab"
    python_type = ParsedAndroidFstab

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidFstab,
        ):
            raise TypeError(
                "value must be a ParsedAndroidFstab"
            )

        return {
            "source_path": str(
                value.source_path
            ),
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "source": (
                encoder.ref(
                    value.source
                )
                if value.source is not None
                else None
            ),
            "android_path": _pure_path(
                value.android_path
            ),
            "declarations": [
                _fstab_declaration_to_dict(
                    item
                )
                for item in value.declarations
            ],
            "unparsed_lines": [
                _fstab_unparsed_to_dict(
                    item
                )
                for item in value.unparsed_lines
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidFstab(
            source=(
                decoder.ref(
                    payload["source"]
                )
                if payload["source"] is not None
                else None
            ),
            source_path=Path(
                payload[
                    "source_path"
                ]
            ),
            filesystem_source=_decode_filesystem_source(
                decoder,
                payload[
                    "filesystem_source"
                ],
            ),
            declarations=tuple(
                _fstab_declaration_from_dict(
                    item
                )
                for item in payload[
                    "declarations"
                ]
            ),
            unparsed_lines=tuple(
                _fstab_unparsed_from_dict(
                    item
                )
                for item in payload[
                    "unparsed_lines"
                ]
            ),
            android_path=_decode_pure_path(
                payload.get(
                    "android_path"
                )
            ),
        )


class ParsedAndroidPropertyFileCodec:
    type_tag = "android.parsed.property_file"
    python_type = ParsedAndroidPropertyFile

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidPropertyFile,
        ):
            raise TypeError(
                "value must be a ParsedAndroidPropertyFile"
            )

        return {
            "kind": value.kind.value,
            "source_path": str(
                value.source_path
            ),
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "source": (
                encoder.ref(
                    value.source
                )
                if value.source is not None
                else None
            ),
            "android_path": _pure_path(
                value.android_path
            ),
            "declarations": [
                _property_declaration_to_dict(
                    item
                )
                for item in value.declarations
            ],
            "unparsed_lines": [
                _property_unparsed_to_dict(
                    item
                )
                for item in value.unparsed_lines
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidPropertyFile(
            source=(
                decoder.ref(
                    payload["source"]
                )
                if payload["source"] is not None
                else None
            ),
            kind=AndroidPropertySourceKind(
                payload[
                    "kind"
                ]
            ),
            source_path=Path(
                payload[
                    "source_path"
                ]
            ),
            filesystem_source=_decode_filesystem_source(
                decoder,
                payload[
                    "filesystem_source"
                ],
            ),
            android_path=_decode_pure_path(
                payload.get(
                    "android_path"
                )
            ),
            declarations=tuple(
                _property_declaration_from_dict(
                    item
                )
                for item in payload[
                    "declarations"
                ]
            ),
            unparsed_lines=tuple(
                _property_unparsed_from_dict(
                    item
                )
                for item in payload[
                    "unparsed_lines"
                ]
            ),
        )


class ParsedAndroidVintfSourceCodec:
    type_tag = "android.parsed.vintf_source"
    python_type = ParsedAndroidVintfSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidVintfSource,
        ):
            raise TypeError(
                "value must be a ParsedAndroidVintfSource"
            )

        return {
            "source_path": str(
                value.source_path
            ),
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "source": (
                encoder.ref(
                    value.source
                )
                if value.source is not None
                else None
            ),
            "android_path": _pure_path(
                value.android_path
            ),
            "parsed": {
                "source_path": str(
                    value.parsed.source_path
                ),
                "raw": value.parsed.raw,
                "root": _vintf_element_to_dict(
                    value.parsed.root
                ),
            },
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        parsed = payload[
            "parsed"
        ]

        if not isinstance(
            parsed,
            dict,
        ):
            raise TypeError(
                "parsed VINTF payload must be a dict"
            )

        return ParsedAndroidVintfSource(
            source=(
                decoder.ref(
                    payload["source"]
                )
                if payload["source"] is not None
                else None
            ),
            source_path=Path(
                payload[
                    "source_path"
                ]
            ),
            parsed=ParsedVintfDocument(
                source_path=Path(
                    parsed[
                        "source_path"
                    ]
                ),
                raw=parsed[
                    "raw"
                ],
                root=_vintf_element_from_dict(
                    parsed[
                        "root"
                    ]
                ),
            ),
            filesystem_source=_decode_filesystem_source(
                decoder,
                payload[
                    "filesystem_source"
                ],
            ),
            android_path=_decode_pure_path(
                payload.get(
                    "android_path"
                )
            ),
        )


# Ueventd's declaration union has several concrete declaration types.
# Its already-audited leaf model needs its own exact union serializer before
# this codec can safely encode declarations. Keep the graph codec registered
# only after that helper is added.
#
# We deliberately leave ParsedAndroidUeventd out of the exported tuple here
# rather than silently dropping declaration data.


FILESYSTEM_OBSERVATION_CODECS = (
    ParsedAndroidInitSourceCodec(),
    ParsedAndroidFstabCodec(),
    ParsedAndroidPropertyFileCodec(),
    ParsedAndroidVintfSourceCodec(),
)

# ---------------------------------------------------------------------------
# Ueventd
# ---------------------------------------------------------------------------

import base64

from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
    ParsedAndroidSelinuxSource,
)
from treeforge.android.parsing.selinux import (
    AndroidSelinuxCilAtom,
    AndroidSelinuxCilForm,
    AndroidSelinuxCilList,
    AndroidSelinuxContextDeclaration,
    AndroidSelinuxMacPermissionsAttribute,
    AndroidSelinuxMacPermissionsElement,
    AndroidSelinuxSeappDeclaration,
    AndroidSelinuxSeappField,
    AndroidSelinuxSourceKind,
    AndroidSelinuxTextLine,
    AndroidSelinuxUnparsedLine,
    ParsedAndroidSelinuxFile,
)
from treeforge.android.parsing.ueventd import (
    AndroidUeventdDeviceRule,
    AndroidUeventdFirmwareDirectories,
    AndroidUeventdImport,
    AndroidUeventdSocketRcvbufSize,
    AndroidUeventdSubsystem,
    AndroidUeventdSubsystemOption,
    AndroidUeventdSysfsRule,
    AndroidUeventdUnparsedLine,
)


def _ueventd_declaration_to_dict(
    value: object,
) -> dict[str, Any]:
    if isinstance(
        value,
        AndroidUeventdImport,
    ):
        return {
            "type": "import",
            "path": value.path,
            "source_path": str(
                value.source_path
            ),
            "source_line": value.source_line,
        }

    if isinstance(
        value,
        AndroidUeventdDeviceRule,
    ):
        return {
            "type": "device_rule",
            "path": value.path,
            "mode": value.mode,
            "user": value.user,
            "group": value.group,
            "source_path": str(
                value.source_path
            ),
            "source_line": value.source_line,
        }

    if isinstance(
        value,
        AndroidUeventdSysfsRule,
    ):
        return {
            "type": "sysfs_rule",
            "path": value.path,
            "attribute": value.attribute,
            "mode": value.mode,
            "user": value.user,
            "group": value.group,
            "source_path": str(
                value.source_path
            ),
            "source_line": value.source_line,
        }

    if isinstance(
        value,
        AndroidUeventdSubsystem,
    ):
        return {
            "type": "subsystem",
            "name": value.name,
            "options": [
                {
                    "name": option.name,
                    "value": option.value,
                    "source_path": str(
                        option.source_path
                    ),
                    "source_line": (
                        option.source_line
                    ),
                }
                for option
                in value.options
            ],
            "source_path": str(
                value.source_path
            ),
            "source_line": value.source_line,
        }

    if isinstance(
        value,
        AndroidUeventdFirmwareDirectories,
    ):
        return {
            "type": "firmware_directories",
            "directories": list(
                value.directories
            ),
            "source_path": str(
                value.source_path
            ),
            "source_line": value.source_line,
        }

    if isinstance(
        value,
        AndroidUeventdSocketRcvbufSize,
    ):
        return {
            "type": "socket_rcvbuf_size",
            "size": value.size,
            "source_path": str(
                value.source_path
            ),
            "source_line": value.source_line,
        }

    raise TypeError(
        "unsupported Android ueventd declaration: "
        f"{type(value).__module__}."
        f"{type(value).__qualname__}"
    )


def _ueventd_declaration_from_dict(
    payload: object,
) -> object:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "ueventd declaration payload "
            "must be a dict"
        )

    kind = payload.get(
        "type"
    )

    source_path = Path(
        payload[
            "source_path"
        ]
    )

    source_line = payload[
        "source_line"
    ]

    if kind == "import":
        return AndroidUeventdImport(
            path=payload[
                "path"
            ],
            source_path=source_path,
            source_line=source_line,
        )

    if kind == "device_rule":
        return AndroidUeventdDeviceRule(
            path=payload[
                "path"
            ],
            mode=payload[
                "mode"
            ],
            user=payload[
                "user"
            ],
            group=payload[
                "group"
            ],
            source_path=source_path,
            source_line=source_line,
        )

    if kind == "sysfs_rule":
        return AndroidUeventdSysfsRule(
            path=payload[
                "path"
            ],
            attribute=payload[
                "attribute"
            ],
            mode=payload[
                "mode"
            ],
            user=payload[
                "user"
            ],
            group=payload[
                "group"
            ],
            source_path=source_path,
            source_line=source_line,
        )

    if kind == "subsystem":
        options = payload[
            "options"
        ]

        if not isinstance(
            options,
            list,
        ):
            raise TypeError(
                "ueventd subsystem options "
                "must be a list"
            )

        return AndroidUeventdSubsystem(
            name=payload[
                "name"
            ],
            options=tuple(
                AndroidUeventdSubsystemOption(
                    name=option[
                        "name"
                    ],
                    value=option[
                        "value"
                    ],
                    source_path=Path(
                        option[
                            "source_path"
                        ]
                    ),
                    source_line=option[
                        "source_line"
                    ],
                )
                for option in options
            ),
            source_path=source_path,
            source_line=source_line,
        )

    if kind == "firmware_directories":
        return AndroidUeventdFirmwareDirectories(
            directories=_strings(
                payload[
                    "directories"
                ],
                field="directories",
            ),
            source_path=source_path,
            source_line=source_line,
        )

    if kind == "socket_rcvbuf_size":
        return AndroidUeventdSocketRcvbufSize(
            size=payload[
                "size"
            ],
            source_path=source_path,
            source_line=source_line,
        )

    raise ValueError(
        "unknown ueventd declaration type: "
        f"{kind}"
    )


def _ueventd_unparsed_to_dict(
    value: AndroidUeventdUnparsedLine,
) -> dict[str, Any]:
    return {
        "raw": value.raw,
        "source_path": str(
            value.source_path
        ),
        "source_line": value.source_line,
    }


def _ueventd_unparsed_from_dict(
    payload: object,
) -> AndroidUeventdUnparsedLine:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "ueventd unparsed payload "
            "must be a dict"
        )

    return AndroidUeventdUnparsedLine(
        raw=payload[
            "raw"
        ],
        source_path=Path(
            payload[
                "source_path"
            ]
        ),
        source_line=payload[
            "source_line"
        ],
    )


class ParsedAndroidUeventdCodec:
    type_tag = "android.parsed.ueventd"
    python_type = ParsedAndroidUeventd

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidUeventd,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidUeventd"
            )

        return {
            "source_path": str(
                value.source_path
            ),
            "raw": value.raw,
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "source": (
                encoder.ref(
                    value.source
                )
                if value.source is not None
                else None
            ),
            "android_path": _pure_path(
                value.android_path
            ),
            "declarations": [
                _ueventd_declaration_to_dict(
                    declaration
                )
                for declaration
                in value.declarations
            ],
            "unparsed_lines": [
                _ueventd_unparsed_to_dict(
                    line
                )
                for line
                in value.unparsed_lines
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidUeventd(
            source=(
                decoder.ref(
                    payload["source"]
                )
                if payload["source"] is not None
                else None
            ),
            source_path=Path(
                payload[
                    "source_path"
                ]
            ),
            raw=payload[
                "raw"
            ],
            filesystem_source=(
                _decode_filesystem_source(
                    decoder,
                    payload[
                        "filesystem_source"
                    ],
                )
            ),
            declarations=tuple(
                _ueventd_declaration_from_dict(
                    declaration
                )
                for declaration
                in payload[
                    "declarations"
                ]
            ),
            unparsed_lines=tuple(
                _ueventd_unparsed_from_dict(
                    line
                )
                for line
                in payload[
                    "unparsed_lines"
                ]
            ),
            android_path=_decode_pure_path(
                payload.get(
                    "android_path"
                )
            ),
        )


# ---------------------------------------------------------------------------
# SELinux
# ---------------------------------------------------------------------------


def _bytes_to_text(
    value: bytes,
) -> str:
    return base64.b64encode(
        value
    ).decode(
        "ascii"
    )


def _bytes_from_text(
    value: object,
) -> bytes:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "encoded bytes must be a string"
        )

    try:
        return base64.b64decode(
            value.encode(
                "ascii"
            ),
            validate=True,
        )
    except Exception as error:
        raise ValueError(
            "invalid base64 payload"
        ) from error


def _cil_expression_to_dict(
    value: object,
) -> dict[str, Any]:
    if isinstance(
        value,
        AndroidSelinuxCilAtom,
    ):
        return {
            "type": "atom",
            "value": value.value,
            "quoted": value.quoted,
            "source_line": value.source_line,
        }

    if isinstance(
        value,
        AndroidSelinuxCilList,
    ):
        return {
            "type": "list",
            "items": [
                _cil_expression_to_dict(
                    item
                )
                for item in value.items
            ],
            "source_line": value.source_line,
            "end_line": value.end_line,
        }

    raise TypeError(
        "unsupported SELinux CIL expression"
    )


def _cil_expression_from_dict(
    payload: object,
) -> object:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "CIL expression payload "
            "must be a dict"
        )

    kind = payload.get(
        "type"
    )

    if kind == "atom":
        return AndroidSelinuxCilAtom(
            value=payload[
                "value"
            ],
            quoted=payload[
                "quoted"
            ],
            source_line=payload[
                "source_line"
            ],
        )

    if kind == "list":
        items = payload[
            "items"
        ]

        if not isinstance(
            items,
            list,
        ):
            raise TypeError(
                "CIL list items must be a list"
            )

        return AndroidSelinuxCilList(
            items=tuple(
                _cil_expression_from_dict(
                    item
                )
                for item in items
            ),
            source_line=payload[
                "source_line"
            ],
            end_line=payload[
                "end_line"
            ],
        )

    raise ValueError(
        "unknown CIL expression type: "
        f"{kind}"
    )


def _mac_permissions_element_to_dict(
    value: AndroidSelinuxMacPermissionsElement,
) -> dict[str, Any]:
    if not isinstance(
        value,
        AndroidSelinuxMacPermissionsElement,
    ):
        raise TypeError(
            "value must be an "
            "AndroidSelinuxMacPermissionsElement"
        )

    return {
        "name": value.name,
        "attributes": [
            {
                "name": attribute.name,
                "value": attribute.value,
            }
            for attribute
            in value.attributes
        ],
        "children": [
            _mac_permissions_element_to_dict(
                child
            )
            for child
            in value.children
        ],
        "text": value.text,
        "source_path": str(
            value.source_path
        ),
        "source_line": value.source_line,
    }


def _mac_permissions_element_from_dict(
    payload: object,
) -> AndroidSelinuxMacPermissionsElement:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "mac_permissions element payload "
            "must be a dict"
        )

    attributes = payload.get(
        "attributes"
    )
    children = payload.get(
        "children"
    )

    if not isinstance(
        attributes,
        list,
    ):
        raise TypeError(
            "mac_permissions attributes payload "
            "must be a list"
        )

    if not isinstance(
        children,
        list,
    ):
        raise TypeError(
            "mac_permissions children payload "
            "must be a list"
        )

    restored_attributes = []

    for attribute in attributes:
        if not isinstance(
            attribute,
            dict,
        ):
            raise TypeError(
                "mac_permissions attribute payload "
                "must be a dict"
            )

        restored_attributes.append(
            AndroidSelinuxMacPermissionsAttribute(
                name=attribute[
                    "name"
                ],
                value=attribute[
                    "value"
                ],
            )
        )

    return AndroidSelinuxMacPermissionsElement(
        name=payload[
            "name"
        ],
        attributes=tuple(
            restored_attributes
        ),
        children=tuple(
            _mac_permissions_element_from_dict(
                child
            )
            for child in children
        ),
        text=payload.get(
            "text",
            "",
        ),
        source_path=Path(
            payload[
                "source_path"
            ]
        ),
        source_line=payload[
            "source_line"
        ],
    )


def _selinux_file_to_dict(
    value: ParsedAndroidSelinuxFile,
) -> dict[str, Any]:
    return {
        "source_path": str(
            value.source_path
        ),
        "kind": value.kind.value,
        "raw_bytes": _bytes_to_text(
            value.raw_bytes
        ),
        "raw": value.raw,
        "context_declarations": [
            {
                "selector": item.selector,
                "context": item.context,
                "selector_fields": list(
                    item.selector_fields
                ),
                "trailing_fields": list(
                    item.trailing_fields
                ),
                "raw": item.raw,
                "source_path": str(
                    item.source_path
                ),
                "source_line": (
                    item.source_line
                ),
            }
            for item
            in value.context_declarations
        ],
        "seapp_declarations": [
            {
                "fields": [
                    {
                        "name": field.name,
                        "value": field.value,
                    }
                    for field
                    in item.fields
                ],
                "raw": item.raw,
                "source_path": str(
                    item.source_path
                ),
                "source_line": (
                    item.source_line
                ),
            }
            for item
            in value.seapp_declarations
        ],
        "mac_permissions_root": (
            _mac_permissions_element_to_dict(
                value.mac_permissions_root
            )
            if value.mac_permissions_root
            is not None
            else None
        ),
        "cil_forms": [
            {
                "name": item.name,
                "expression": (
                    _cil_expression_to_dict(
                        item.expression
                    )
                ),
                "source_line": (
                    item.source_line
                ),
                "end_line": (
                    item.end_line
                ),
            }
            for item
            in value.cil_forms
        ],
        "text_lines": [
            {
                "value": item.value,
                "raw": item.raw,
                "source_path": str(
                    item.source_path
                ),
                "source_line": (
                    item.source_line
                ),
            }
            for item
            in value.text_lines
        ],
        "unparsed_lines": [
            {
                "raw": item.raw,
                "source_path": str(
                    item.source_path
                ),
                "source_line": (
                    item.source_line
                ),
            }
            for item
            in value.unparsed_lines
        ],
    }


def _selinux_file_from_dict(
    payload: object,
) -> ParsedAndroidSelinuxFile:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "SELinux file payload must be a dict"
        )

    context_declarations = payload[
        "context_declarations"
    ]
    seapp_declarations = payload[
        "seapp_declarations"
    ]
    mac_permissions_payload = (
        payload.get(
            "mac_permissions_root"
        )
    )

    cil_forms = payload[
        "cil_forms"
    ]
    text_lines = payload[
        "text_lines"
    ]
    unparsed_lines = payload[
        "unparsed_lines"
    ]

    collections = (
        context_declarations,
        seapp_declarations,
        cil_forms,
        text_lines,
        unparsed_lines,
    )

    if not all(
        isinstance(
            collection,
            list,
        )
        for collection in collections
    ):
        raise TypeError(
            "SELinux collection payloads "
            "must be lists"
        )

    restored_forms = []

    for item in cil_forms:
        expression = (
            _cil_expression_from_dict(
                item[
                    "expression"
                ]
            )
        )

        if not isinstance(
            expression,
            AndroidSelinuxCilList,
        ):
            raise TypeError(
                "SELinux CIL form expression "
                "must restore as "
                "AndroidSelinuxCilList"
            )

        restored_forms.append(
            AndroidSelinuxCilForm(
                name=item[
                    "name"
                ],
                expression=expression,
                source_line=item[
                    "source_line"
                ],
                end_line=item[
                    "end_line"
                ],
            )
        )

    return ParsedAndroidSelinuxFile(
        source_path=Path(
            payload[
                "source_path"
            ]
        ),
        kind=AndroidSelinuxSourceKind(
            payload[
                "kind"
            ]
        ),
        raw_bytes=_bytes_from_text(
            payload[
                "raw_bytes"
            ]
        ),
        raw=payload.get(
            "raw"
        ),
        context_declarations=tuple(
            AndroidSelinuxContextDeclaration(
                selector=item[
                    "selector"
                ],
                context=item[
                    "context"
                ],
                selector_fields=_strings(
                    item[
                        "selector_fields"
                    ],
                    field="selector_fields",
                ),
                trailing_fields=_strings(
                    item[
                        "trailing_fields"
                    ],
                    field="trailing_fields",
                ),
                raw=item[
                    "raw"
                ],
                source_path=Path(
                    item[
                        "source_path"
                    ]
                ),
                source_line=item[
                    "source_line"
                ],
            )
            for item
            in context_declarations
        ),
        seapp_declarations=tuple(
            AndroidSelinuxSeappDeclaration(
                fields=tuple(
                    AndroidSelinuxSeappField(
                        name=field[
                            "name"
                        ],
                        value=field[
                            "value"
                        ],
                    )
                    for field
                    in item[
                        "fields"
                    ]
                ),
                raw=item[
                    "raw"
                ],
                source_path=Path(
                    item[
                        "source_path"
                    ]
                ),
                source_line=item[
                    "source_line"
                ],
            )
            for item
            in seapp_declarations
        ),
        mac_permissions_root=(
            _mac_permissions_element_from_dict(
                mac_permissions_payload
            )
            if mac_permissions_payload
            is not None
            else None
        ),
        cil_forms=tuple(
            restored_forms
        ),
        text_lines=tuple(
            AndroidSelinuxTextLine(
                value=item[
                    "value"
                ],
                raw=item[
                    "raw"
                ],
                source_path=Path(
                    item[
                        "source_path"
                    ]
                ),
                source_line=item[
                    "source_line"
                ],
            )
            for item
            in text_lines
        ),
        unparsed_lines=tuple(
            AndroidSelinuxUnparsedLine(
                raw=item[
                    "raw"
                ],
                source_path=Path(
                    item[
                        "source_path"
                    ]
                ),
                source_line=item[
                    "source_line"
                ],
            )
            for item
            in unparsed_lines
        ),
    )


class ParsedAndroidSelinuxSourceCodec:
    type_tag = "android.parsed.selinux_source"
    python_type = ParsedAndroidSelinuxSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidSelinuxSource,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidSelinuxSource"
            )

        return {
            "source_path": str(
                value.source_path
            ),
            "parsed": _selinux_file_to_dict(
                value.parsed
            ),
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "source": (
                encoder.ref(
                    value.source
                )
                if value.source is not None
                else None
            ),
            "android_path": _pure_path(
                value.android_path
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidSelinuxSource(
            source=(
                decoder.ref(
                    payload["source"]
                )
                if payload["source"] is not None
                else None
            ),
            source_path=Path(
                payload[
                    "source_path"
                ]
            ),
            parsed=_selinux_file_from_dict(
                payload[
                    "parsed"
                ]
            ),
            filesystem_source=(
                _decode_filesystem_source(
                    decoder,
                    payload[
                        "filesystem_source"
                    ],
                )
            ),
            android_path=_decode_pure_path(
                payload.get(
                    "android_path"
                )
            ),
        )


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


class AndroidFilesystemParsingResultCodec:
    type_tag = (
        "android.filesystem_parsing_result"
    )
    python_type = (
        AndroidFilesystemParsingResult
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidFilesystemParsingResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidFilesystemParsingResult"
            )

        return {
            "init_files": [
                encoder.ref(
                    item
                )
                for item
                in value.init_files
            ],
            "fstabs": [
                encoder.ref(
                    item
                )
                for item
                in value.fstabs
            ],
            "ueventd_files": [
                encoder.ref(
                    item
                )
                for item
                in value.ueventd_files
            ],
            "vintf_documents": [
                encoder.ref(
                    item
                )
                for item
                in value.vintf_documents
            ],
            "property_files": [
                encoder.ref(
                    item
                )
                for item
                in value.property_files
            ],
            "selinux_sources": [
                encoder.ref(
                    item
                )
                for item
                in value.selinux_sources
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidFilesystemParsingResult(
            init_files=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "init_files"
                ]
            ),
            fstabs=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "fstabs"
                ]
            ),
            ueventd_files=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "ueventd_files"
                ]
            ),
            vintf_documents=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "vintf_documents"
                ]
            ),
            property_files=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "property_files"
                ]
            ),
            selinux_sources=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "selinux_sources"
                ]
            ),
        )


FILESYSTEM_OBSERVATION_CODECS = (
    ParsedAndroidInitSourceCodec(),
    ParsedAndroidFstabCodec(),
    ParsedAndroidUeventdCodec(),
    ParsedAndroidVintfSourceCodec(),
    ParsedAndroidPropertyFileCodec(),
    ParsedAndroidSelinuxSourceCodec(),
    AndroidFilesystemParsingResultCodec(),
)
