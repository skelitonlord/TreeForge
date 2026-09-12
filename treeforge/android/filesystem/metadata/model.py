from __future__ import annotations

import base64
import binascii
import json
import posixpath
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


METADATA_SCHEMA_VERSION = 1


class FilesystemEntryType(StrEnum):
    """
    Types of entries that may exist inside an Android filesystem.
    """

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    CHARACTER_DEVICE = "character_device"
    BLOCK_DEVICE = "block_device"
    FIFO = "fifo"
    SOCKET = "socket"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ExtendedAttribute:
    """
    A binary extended attribute attached to a filesystem entry.
    """

    name: str
    value: bytes

    def __post_init__(
        self,
    ) -> None:
        if not self.name:
            raise ValueError(
                "Extended attribute name cannot be empty.",
            )

        if not isinstance(
            self.value,
            bytes,
        ):
            raise TypeError(
                "Extended attribute value must be bytes.",
            )

    def to_dict(
        self,
    ) -> dict[str, str]:
        """
        Serialize this extended attribute using Base64.
        """

        encoded = base64.b64encode(
            self.value,
        ).decode("ascii")

        return {
            "encoding": "base64",
            "value": encoded,
        }

    @classmethod
    def from_dict(
        cls,
        name: str,
        data: dict[str, Any],
    ) -> ExtendedAttribute:
        """
        Deserialize an extended attribute from sidecar data.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Extended attribute data must be a dictionary.",
            )

        encoding = data.get("encoding")

        if encoding != "base64":
            raise ValueError(
                f"Unsupported extended attribute encoding: {encoding}",
            )

        encoded_value = data.get("value")

        if not isinstance(
            encoded_value,
            str,
        ):
            raise TypeError(
                "Extended attribute value must be a Base64 string.",
            )

        try:
            value = base64.b64decode(
                encoded_value,
                validate=True,
            )
        except (
            binascii.Error,
            ValueError,
        ) as error:
            raise ValueError(
                f"Invalid Base64 value for extended attribute: {name}",
            ) from error

        return cls(
            name=name,
            value=value,
        )


@dataclass(frozen=True)
class FilesystemMetadataEntry:
    """
    Authoritative metadata for one filesystem-native path.

    ``path`` is expressed in the namespace of the authoritative filesystem
    metadata source. It is not an Android logical/view path and it is not a
    host materialization path.
    """

    path: str
    entry_type: FilesystemEntryType
    mode: int
    uid: int
    gid: int
    size: int
    inode: int
    link_count: int
    symlink_target: str | None = None
    device_major: int | None = None
    device_minor: int | None = None
    xattrs: dict[str, ExtendedAttribute] = field(
        default_factory=dict,
    )

    def __post_init__(
        self,
    ) -> None:
        normalized_path = normalize_metadata_path(
            self.path,
        )

        object.__setattr__(
            self,
            "path",
            normalized_path,
        )

        if not isinstance(
            self.entry_type,
            FilesystemEntryType,
        ):
            object.__setattr__(
                self,
                "entry_type",
                FilesystemEntryType(
                    self.entry_type,
                ),
            )

        for field_name in (
            "mode",
            "uid",
            "gid",
            "size",
            "inode",
            "link_count",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an integer.",
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative.",
                )

        if (
            self.device_major is None
        ) != (
            self.device_minor is None
        ):
            raise ValueError(
                "device_major and device_minor must be provided together.",
            )

        normalized_xattrs: dict[str, ExtendedAttribute] = {}

        for name, attribute in self.xattrs.items():
            if not isinstance(
                attribute,
                ExtendedAttribute,
            ):
                raise TypeError(
                    "xattrs values must be ExtendedAttribute instances.",
                )

            if name != attribute.name:
                raise ValueError(
                    "Extended attribute dictionary key must match "
                    "the attribute name.",
                )

            normalized_xattrs[name] = attribute

        object.__setattr__(
            self,
            "xattrs",
            normalized_xattrs,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize this metadata entry.
        """

        return {
            "entry_type": self.entry_type.value,
            "mode": self.mode,
            "uid": self.uid,
            "gid": self.gid,
            "size": self.size,
            "inode": self.inode,
            "link_count": self.link_count,
            "symlink_target": self.symlink_target,
            "device_major": self.device_major,
            "device_minor": self.device_minor,
            "xattrs": {
                name: attribute.to_dict()
                for name, attribute in sorted(
                    self.xattrs.items(),
                )
            },
        }

    @classmethod
    def from_dict(
        cls,
        path: str,
        data: dict[str, Any],
    ) -> FilesystemMetadataEntry:
        """
        Deserialize one metadata entry.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Filesystem metadata entry must be a dictionary.",
            )

        xattrs_data = data.get(
            "xattrs",
            {},
        )

        if not isinstance(
            xattrs_data,
            dict,
        ):
            raise TypeError(
                "Filesystem metadata entry xattrs must be a dictionary.",
            )

        xattrs = {
            name: ExtendedAttribute.from_dict(
                name,
                attribute_data,
            )
            for name, attribute_data in xattrs_data.items()
        }

        try:
            entry_type = FilesystemEntryType(
                data["entry_type"],
            )

            return cls(
                path=path,
                entry_type=entry_type,
                mode=data["mode"],
                uid=data["uid"],
                gid=data["gid"],
                size=data["size"],
                inode=data["inode"],
                link_count=data["link_count"],
                symlink_target=data.get(
                    "symlink_target",
                ),
                device_major=data.get(
                    "device_major",
                ),
                device_minor=data.get(
                    "device_minor",
                ),
                xattrs=xattrs,
            )
        except KeyError as error:
            raise ValueError(
                f"Missing metadata entry field: {error.args[0]}",
            ) from error


@dataclass(frozen=True)
class FilesystemMetadata:
    """
    Authoritative normalized metadata for one filesystem source.

    Metadata remains independent from the materialized host filesystem so
    original ownership, modes, xattrs, special entry types, and other intrinsic
    filesystem facts are not replaced by host-side observations.

    Entry paths are filesystem-native paths in the metadata source namespace.
    They are not Android logical/view paths.
    """

    filesystem_type: str
    source: Path
    entries: dict[str, FilesystemMetadataEntry]
    schema_version: int = METADATA_SCHEMA_VERSION

    def __post_init__(
        self,
    ) -> None:
        if self.schema_version != METADATA_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported filesystem metadata schema version: "
                f"{self.schema_version}",
            )

        if not self.filesystem_type.strip():
            raise ValueError(
                "filesystem_type cannot be empty.",
            )

        object.__setattr__(
            self,
            "filesystem_type",
            self.filesystem_type.strip().lower(),
        )

        object.__setattr__(
            self,
            "source",
            Path(self.source),
        )

        normalized_entries: dict[
            str,
            FilesystemMetadataEntry,
        ] = {}

        for supplied_path, entry in self.entries.items():
            if not isinstance(
                entry,
                FilesystemMetadataEntry,
            ):
                raise TypeError(
                    "entries values must be "
                    "FilesystemMetadataEntry instances.",
                )

            normalized_path = normalize_metadata_path(
                supplied_path,
            )

            if normalized_path != entry.path:
                raise ValueError(
                    "Metadata entry dictionary key does not match "
                    f"entry path: {supplied_path}",
                )

            if normalized_path in normalized_entries:
                raise ValueError(
                    "Duplicate normalized metadata path: "
                    f"{normalized_path}",
                )

            normalized_entries[normalized_path] = entry

        object.__setattr__(
            self,
            "entries",
            normalized_entries,
        )

    def get(
        self,
        path: str,
    ) -> FilesystemMetadataEntry | None:
        """
        Return metadata for a filesystem-native path.
        """

        return self.entries.get(
            normalize_metadata_path(path),
        )

    def require(
        self,
        path: str,
    ) -> FilesystemMetadataEntry:
        """
        Return metadata for a path or raise KeyError.
        """

        normalized = normalize_metadata_path(
            path,
        )

        try:
            return self.entries[normalized]
        except KeyError as error:
            raise KeyError(
                f"No metadata entry exists for path: {normalized}",
            ) from error

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize the complete metadata sidecar.
        """

        return {
            "schema_version": self.schema_version,
            "filesystem_type": self.filesystem_type,
            "source": str(self.source),
            "entries": {
                path: entry.to_dict()
                for path, entry in sorted(
                    self.entries.items(),
                )
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> FilesystemMetadata:
        """
        Deserialize complete filesystem metadata.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "Filesystem metadata must be a dictionary.",
            )

        schema_version = data.get(
            "schema_version",
        )

        if schema_version != METADATA_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported filesystem metadata schema version: "
                f"{schema_version}",
            )

        entries_data = data.get(
            "entries",
        )

        if not isinstance(
            entries_data,
            dict,
        ):
            raise TypeError(
                "Filesystem metadata entries must be a dictionary.",
            )

        entries: dict[str, FilesystemMetadataEntry] = {}

        for path, entry_data in entries_data.items():
            normalized_path = normalize_metadata_path(
                path,
            )

            if normalized_path in entries:
                raise ValueError(
                    "Duplicate normalized metadata path: "
                    f"{normalized_path}",
                )

            entries[normalized_path] = (
                FilesystemMetadataEntry.from_dict(
                    normalized_path,
                    entry_data,
                )
            )

        try:
            filesystem_type = data["filesystem_type"]
            source = data["source"]
        except KeyError as error:
            raise ValueError(
                f"Missing filesystem metadata field: {error.args[0]}",
            ) from error

        if not isinstance(
            filesystem_type,
            str,
        ):
            raise TypeError(
                "filesystem_type must be a string.",
            )

        if not isinstance(
            source,
            str,
        ):
            raise TypeError(
                "source must be a string.",
            )

        return cls(
            schema_version=schema_version,
            filesystem_type=filesystem_type,
            source=Path(source),
            entries=entries,
        )

    def to_json(
        self,
        *,
        indent: int | None = 2,
    ) -> str:
        """
        Serialize metadata to JSON.
        """

        return json.dumps(
            self.to_dict(),
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_json(
        cls,
        value: str,
    ) -> FilesystemMetadata:
        """
        Deserialize metadata from JSON.
        """

        try:
            data = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Invalid filesystem metadata JSON.",
            ) from error

        return cls.from_dict(
            data,
        )

    def write(
        self,
        path: Path,
    ) -> None:
        """
        Atomically write this metadata sidecar.

        A temporary file is replaced only after serialization succeeds.
        """

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = path.with_name(
            f".{path.name}.tmp",
        )

        try:
            temporary_path.write_text(
                self.to_json() + "\n",
                encoding="utf-8",
            )

            temporary_path.replace(
                path,
            )
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @classmethod
    def read(
        cls,
        path: Path,
    ) -> FilesystemMetadata:
        """
        Read a metadata sidecar from disk.
        """

        path = Path(path)

        return cls.from_json(
            path.read_text(
                encoding="utf-8",
            ),
        )


def normalize_metadata_path(
    path: str,
) -> str:
    """
    Normalize a path using Android filesystem semantics.

    Metadata paths are always absolute Android paths. They are never host
    filesystem paths.
    """

    if not isinstance(
        path,
        str,
    ):
        raise TypeError(
            "Metadata path must be a string.",
        )

    normalized = posixpath.normpath(
        "/" + path.lstrip("/"),
    )

    if normalized == "/":
        return normalized

    if normalized.startswith("/../"):
        raise ValueError(
            "Metadata path escapes filesystem root.",
        )

    return normalized