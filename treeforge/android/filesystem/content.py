from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol

from treeforge.android.filesystem.backends.manager import (
    FilesystemSourceType,
)
from treeforge.android.filesystem.debugfs.runner import (
    DebugfsRunner,
)
from treeforge.android.filesystem.filesystem import (
    Filesystem,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventoryEntry,
)


class FilesystemContentReadError(
    RuntimeError,
):
    """
    Raised when content cannot be read from a canonical filesystem source.
    """


class UnsupportedFilesystemContentError(
    FilesystemContentReadError,
):
    """
    Raised when TreeForge does not yet support content reads for the source
    representation associated with a canonical filesystem inventory entry.
    """


class DebugfsContentReaderLike(
    Protocol,
):
    def read_bytes(
        self,
        image,
        path: str,
    ) -> bytes:
        ...


class FilesystemContentReader:
    """
    Read targeted file content from one canonical filesystem inventory entry.

    This component performs no Discovery, Extraction, filesystem traversal,
    metadata collection, or Android semantic interpretation.

    The supplied FilesystemMetadataInventoryEntry remains the authoritative
    identity of the filesystem being read, including its exact canonical
    InventoryPartition and Extraction artifact lineage.
    """

    def __init__(
        self,
        *,
        debugfs_runner: (
            DebugfsContentReaderLike
            | None
        ) = None,
    ) -> None:
        self.debugfs_runner = (
            debugfs_runner
            if debugfs_runner is not None
            else DebugfsRunner()
        )

    def read_bytes(
        self,
        filesystem: FilesystemMetadataInventoryEntry,
        path: str,
    ) -> bytes:
        filesystem = self._validate_filesystem(
            filesystem
        )

        filesystem_path = self._normalize_filesystem_path(
            path
        )

        result = filesystem.result
        source_type = result.source_type
        source = result.artifact.path

        try:
            if (
                source_type
                is FilesystemSourceType.HOST_DIRECTORY
            ):
                return Filesystem(
                    root=source,
                ).read_bytes(
                    filesystem_path
                )

            if (
                source_type
                is FilesystemSourceType.RAW_EXT4
            ):
                return self.debugfs_runner.read_bytes(
                    source,
                    filesystem_path,
                )

            if (
                source_type
                is FilesystemSourceType.SPARSE_EXT4
            ):
                raise UnsupportedFilesystemContentError(
                    "Sparse filesystem reached content access "
                    "after Extraction: "
                    f"{source}"
                )

            if (
                source_type
                is FilesystemSourceType.EROFS
            ):
                raise UnsupportedFilesystemContentError(
                    "EROFS targeted content access is not yet "
                    "implemented: "
                    f"{source}"
                )

            raise UnsupportedFilesystemContentError(
                "Unsupported filesystem content source: "
                f"{source_type}"
            )

        except UnsupportedFilesystemContentError:
            raise

        except Exception as error:
            raise FilesystemContentReadError(
                "Unable to read "
                f"{filesystem_path} from canonical filesystem "
                f"{filesystem.partition_name or filesystem.source_path}"
            ) from error

    def read_text(
        self,
        filesystem: FilesystemMetadataInventoryEntry,
        path: str,
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
    ) -> str:
        if not isinstance(
            encoding,
            str,
        ):
            raise TypeError(
                "encoding must be a string"
            )

        if not encoding:
            raise ValueError(
                "encoding cannot be empty"
            )

        if not isinstance(
            errors,
            str,
        ):
            raise TypeError(
                "errors must be a string"
            )

        if not errors:
            raise ValueError(
                "errors cannot be empty"
            )

        return self.read_bytes(
            filesystem,
            path,
        ).decode(
            encoding=encoding,
            errors=errors,
        )

    @staticmethod
    def _validate_filesystem(
        filesystem: FilesystemMetadataInventoryEntry,
    ) -> FilesystemMetadataInventoryEntry:
        if not isinstance(
            filesystem,
            FilesystemMetadataInventoryEntry,
        ):
            raise TypeError(
                "filesystem must be a "
                "FilesystemMetadataInventoryEntry"
            )

        return filesystem

    @staticmethod
    def _normalize_filesystem_path(
        path: str,
    ) -> str:
        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "path must be a string"
            )

        stripped = path.strip()

        if not stripped:
            raise ValueError(
                "path cannot be empty"
            )

        if (
            "\\x00" in stripped
            or "\\n" in stripped
            or "\\r" in stripped
        ):
            raise ValueError(
                "path contains invalid characters"
            )

        normalized = PurePosixPath(
            stripped
        )

        if not normalized.is_absolute():
            normalized = (
                PurePosixPath("/")
                / normalized
            )

        if ".." in normalized.parts:
            raise ValueError(
                "path cannot contain parent traversal"
            )

        return str(
            normalized
        )
