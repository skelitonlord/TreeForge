from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Protocol

from treeforge.android.filesystem.metadata.model import (
    ExtendedAttribute,
    FilesystemEntryType,
    FilesystemMetadata,
    FilesystemMetadataEntry,
    normalize_metadata_path,
)


class FilesystemMetadataBuilderError(RuntimeError):
    """
    Raised when normalized filesystem metadata cannot be built.
    """


class MetadataStatLike(Protocol):
    """
    Stat information required by FilesystemMetadataBuilder.

    The protocol keeps the builder independent from debugfs-specific models.
    """

    inode: int
    inode_type: object
    mode: int
    uid: int
    gid: int
    size: int
    links: int


class MetadataWalkNodeLike(Protocol):
    """
    Filesystem node information required by the metadata builder.
    """

    path: PurePosixPath
    stat: MetadataStatLike


class MetadataXattrsLike(Protocol):
    """
    Extended attributes returned for one filesystem path.
    """

    path: PurePosixPath
    values: Mapping[str, bytes]


class MetadataXattrCollector(Protocol):
    """
    Interface used to collect xattrs for one node.
    """

    def collect(
        self,
        path: str | PurePosixPath,
    ) -> MetadataXattrsLike:
        """
        Collect xattrs for a filesystem path.
        """


MetadataEntryProgressCallback = Callable[
    [str, int],
    None,
]


class FilesystemMetadataBuilder:
    """
    Convert filesystem walker output into normalized FilesystemMetadata.

    This builder does not know how filesystem nodes were discovered. It can
    therefore consume nodes from debugfs today and other filesystem backends
    later.
    """

    _ENTRY_TYPE_MAP: dict[str, FilesystemEntryType] = {
        "file": FilesystemEntryType.FILE,
        "regular": FilesystemEntryType.FILE,
        "regular_file": FilesystemEntryType.FILE,
        "directory": FilesystemEntryType.DIRECTORY,
        "dir": FilesystemEntryType.DIRECTORY,
        "symlink": FilesystemEntryType.SYMLINK,
        "symbolic_link": FilesystemEntryType.SYMLINK,
        "character_device": FilesystemEntryType.CHARACTER_DEVICE,
        "character_special": FilesystemEntryType.CHARACTER_DEVICE,
        "char_device": FilesystemEntryType.CHARACTER_DEVICE,
        "block_device": FilesystemEntryType.BLOCK_DEVICE,
        "block_special": FilesystemEntryType.BLOCK_DEVICE,
        "fifo": FilesystemEntryType.FIFO,
        "named_pipe": FilesystemEntryType.FIFO,
        "socket": FilesystemEntryType.SOCKET,
        "unknown": FilesystemEntryType.UNKNOWN,
    }

    @staticmethod
    def _resolve_user_id(
        stat: object,
    ) -> int:
        """
        Return the canonical user ID from a filesystem stat model.

        Filesystem stat models must expose the canonical ``user_id``
        attribute.
        """

        user_id = getattr(
            stat,
            "user_id",
            None,
        )

        if (
            isinstance(
                user_id,
                bool,
            )
            or not isinstance(
                user_id,
                int,
            )
        ):
            raise TypeError(
                "filesystem stat must provide an integer "
                "user_id"
            )

        if user_id < 0:
            raise ValueError(
                "filesystem stat user ID cannot be negative"
            )

        return user_id

    @staticmethod
    def _resolve_group_id(
        stat: object,
    ) -> int:
        """
        Return the canonical group ID from a filesystem stat model.

        Filesystem stat models must expose the canonical ``group_id``
        attribute.
        """

        group_id = getattr(
            stat,
            "group_id",
            None,
        )

        if (
            isinstance(
                group_id,
                bool,
            )
            or not isinstance(
                group_id,
                int,
            )
        ):
            raise TypeError(
                "filesystem stat must provide an integer "
                "group_id"
            )

        if group_id < 0:
            raise ValueError(
                "filesystem stat group ID cannot be negative"
            )

        return group_id

    def __init__(
        self,
        xattr_collector: MetadataXattrCollector | None = None,
        *,
        progress_callback: (
            MetadataEntryProgressCallback
            | None
        ) = None,
    ) -> None:
        self._xattr_collector = xattr_collector
        self._progress_callback = progress_callback

    def build(
        self,
        *,
        source: Path,
        filesystem_type: str,
        nodes: Iterable[MetadataWalkNodeLike],
    ) -> FilesystemMetadata:
        """
        Build normalized metadata from filesystem walker nodes.

        Args:
            source:
                Source filesystem image.

            filesystem_type:
                Filesystem format, such as ``ext4``.

            nodes:
                Walker nodes in any traversal order.

        Returns:
            Complete normalized filesystem metadata.

        Raises:
            TypeError:
                If an argument has an invalid type.

            ValueError:
                If filesystem_type is empty.

            FilesystemMetadataBuilderError:
                If a node is malformed, duplicated, or cannot be converted.
        """

        normalized_source = self._normalize_source(source)
        normalized_filesystem_type = self._normalize_filesystem_type(
            filesystem_type
        )

        if not isinstance(nodes, Iterable):
            raise TypeError(
                "nodes must be an iterable of filesystem walk nodes."
            )

        entries: dict[str, FilesystemMetadataEntry] = {}

        processed = 0

        for node in nodes:
            entry = self._build_entry(node)

            if entry.path in entries:
                raise FilesystemMetadataBuilderError(
                    "Duplicate filesystem metadata path: "
                    f"{entry.path}"
                )

            entries[entry.path] = entry
            processed += 1

            if self._progress_callback is not None:
                self._progress_callback(
                    entry.path,
                    processed,
                )

        return FilesystemMetadata(
            filesystem_type=normalized_filesystem_type,
            source=normalized_source,
            entries=entries,
        )

    def _build_entry(
        self,
        node: MetadataWalkNodeLike,
    ) -> FilesystemMetadataEntry:
        try:
            path = normalize_metadata_path(
                str(node.path)
            )
            stat = node.stat
        except Exception as error:
            raise FilesystemMetadataBuilderError(
                "Filesystem walker produced an invalid node."
            ) from error

        try:
            entry_type = self._convert_entry_type(
                stat.inode_type
            )

            xattrs = self._collect_xattrs(
                path
            )

            return FilesystemMetadataEntry(
                path=path,
                entry_type=entry_type,
                mode=stat.mode,
                uid=self._resolve_user_id(
                    stat,
                ),
                gid=self._resolve_group_id(
                    stat,
                ),
                size=stat.size,
                inode=stat.inode,
                link_count=stat.links,
                symlink_target=(
                    stat.symlink_target
                ),
                device_major=None,
                device_minor=None,
                xattrs=xattrs,
            )
        except FilesystemMetadataBuilderError:
            raise
        except Exception as error:
            raise FilesystemMetadataBuilderError(
                f"Unable to build filesystem metadata for {path}"
            ) from error

    def _collect_xattrs(
        self,
        path: str,
    ) -> dict[str, ExtendedAttribute]:
        if self._xattr_collector is None:
            return {}

        try:
            collected = self._xattr_collector.collect(
                path
            )
        except Exception as error:
            raise FilesystemMetadataBuilderError(
                f"Unable to collect extended attributes for {path}"
            ) from error

        collected_path = normalize_metadata_path(
            str(collected.path)
        )

        if collected_path != path:
            raise FilesystemMetadataBuilderError(
                "Extended attributes were returned for the wrong path: "
                f"expected {path}, received {collected_path}"
            )

        attributes: dict[str, ExtendedAttribute] = {}

        for name, value in collected.values.items():
            if not isinstance(name, str):
                raise FilesystemMetadataBuilderError(
                    f"Extended attribute name for {path} must be a string."
                )

            if not isinstance(value, bytes):
                raise FilesystemMetadataBuilderError(
                    f"Extended attribute {name!r} for {path} "
                    "must contain bytes."
                )

            if name in attributes:
                raise FilesystemMetadataBuilderError(
                    f"Duplicate extended attribute {name!r} for {path}"
                )

            attributes[name] = ExtendedAttribute(
                name=name,
                value=value,
            )

        return attributes

    @classmethod
    def _convert_entry_type(
        cls,
        inode_type: object,
    ) -> FilesystemEntryType:
        if isinstance(
            inode_type,
            FilesystemEntryType,
        ):
            return inode_type

        raw_value = getattr(
            inode_type,
            "value",
            inode_type,
        )

        if not isinstance(raw_value, str):
            raise FilesystemMetadataBuilderError(
                "Filesystem inode type must be a string or enum value."
            )

        normalized = (
            raw_value.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        return cls._ENTRY_TYPE_MAP.get(
            normalized,
            FilesystemEntryType.UNKNOWN,
        )

    @staticmethod
    def _normalize_source(
        source: Path,
    ) -> Path:
        if not isinstance(source, Path):
            raise TypeError(
                "source must be a pathlib.Path."
            )

        return source

    @staticmethod
    def _normalize_filesystem_type(
        filesystem_type: str,
    ) -> str:
        if not isinstance(filesystem_type, str):
            raise TypeError(
                "filesystem_type must be a string."
            )

        normalized = filesystem_type.strip().lower()

        if not normalized:
            raise ValueError(
                "filesystem_type cannot be empty."
            )

        return normalized