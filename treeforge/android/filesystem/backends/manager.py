from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from treeforge.android.filesystem.backends.erofs import (
    ErofsFilesystemBackend,
)
from treeforge.android.filesystem.backends.ext4 import (
    Ext4FilesystemBackend,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadata,
)
from treeforge.android.filesystem.metadata.builder import (
    MetadataEntryProgressCallback,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)


class FilesystemBackendManagerError(
    RuntimeError,
):
    """
    Base error for filesystem backend selection and execution.
    """


class UnsupportedFilesystemError(
    FilesystemBackendManagerError,
):
    """
    Raised when no registered backend supports the detected format.
    """


class FilesystemSourceType(
    StrEnum,
):
    """
    High-level filesystem-source types recognized by the metadata layer.

    Android sparse images may still be detected defensively, but they must have
    been normalized by Extraction before reaching filesystem metadata.
    """

    HOST_DIRECTORY = "host_directory"
    RAW_EXT4 = "raw_ext4"
    SPARSE_EXT4 = "sparse_ext4"
    EROFS = "erofs"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class FilesystemBackendResult:
    """
    Canonical filesystem-metadata result for one exact Extraction artifact.

    ``artifact`` preserves the exact canonical ExtractedArtifact that identifies
    the physical filesystem source.

    ``partition`` preserves canonical InventoryPartition context when the
    filesystem is partition-backed. Non-partition filesystems such as ramdisk
    and APEX payload filesystems legitimately have no InventoryPartition.

    ``source_type`` records the physical source representation observed by the
    metadata layer, while ``metadata`` contains the collected filesystem facts.
    """

    artifact: ExtractedArtifact
    source_type: FilesystemSourceType
    metadata: FilesystemMetadata
    partition: InventoryPartition | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.source_type,
            FilesystemSourceType,
        ):
            raise TypeError(
                "source_type must be a FilesystemSourceType"
            )

        if not isinstance(
            self.metadata,
            FilesystemMetadata,
        ):
            raise TypeError(
                "metadata must be FilesystemMetadata"
            )

        if (
            self.partition is not None
            and not isinstance(
                self.partition,
                InventoryPartition,
            )
        ):
            raise TypeError(
                "partition must be an InventoryPartition or None"
            )

        if self.partition is not None:
            ancestor = self.artifact

            while (
                ancestor is not None
                and ancestor
                is not self.partition.artifact
            ):
                ancestor = ancestor.parent

            if ancestor is None:
                raise ValueError(
                    "partition-backed filesystem metadata artifact must "
                    "descend from the exact canonical partition artifact"
                )


class ImageDetectorLike(
    Protocol,
):
    def detect(
        self,
        source: Path,
    ) -> object:
        ...


class MetadataBackendLike(
    Protocol,
):
    def collect_metadata(
        self,
        source: Path,
        *,
        root: str = "/",
        include_root: bool = True,
        max_depth: int | None = None,
    ) -> FilesystemMetadata:
        ...


BackendFactory = Callable[
    ...,
    MetadataBackendLike,
]


class FilesystemBackendManager:
    """
    Detect an already-normalized filesystem source and route it to a backend.

    Supported filesystem-image paths:

    - raw ext4;
    - EROFS.

    Sparse image conversion is not owned here. Sparse sources reaching this
    manager indicate that the Extraction pipeline did not complete correctly.
    """

    def __init__(
        self,
        *,
        detector: ImageDetectorLike,
        ext4_backend_factory: (
            BackendFactory
            | None
        ) = None,
        erofs_backend_factory: (
            BackendFactory
            | None
        ) = None,
    ) -> None:
        self._detector = detector

        self._ext4_backend_factory = (
            ext4_backend_factory
            if ext4_backend_factory is not None
            else Ext4FilesystemBackend
        )

        self._erofs_backend_factory = (
            erofs_backend_factory
            if erofs_backend_factory is not None
            else ErofsFilesystemBackend
        )

    def collect_metadata(
        self,
        artifact: ExtractedArtifact,
        *,
        metadata_source: ExtractedArtifact | None = None,
        partition: InventoryPartition | None = None,
        root: str = "/",
        include_root: bool = True,
        max_depth: int | None = None,
        progress_callback: (
            MetadataEntryProgressCallback
            | None
        ) = None,
    ) -> FilesystemBackendResult:
        """
        Collect intrinsic metadata for one canonical filesystem artifact.

        ``artifact`` is the exact canonical filesystem identity consumed by
        downstream stages.

        ``metadata_source`` is the authoritative filesystem image used to
        obtain intrinsic metadata. When omitted, ``artifact`` itself is used.

        The two identities are intentionally distinct for materialized
        filesystems: Parsing consumes the directory artifact while metadata
        remains sourced from the original filesystem image.
        """

        normalized_artifact = (
            self._validate_artifact(
                artifact
            )
        )

        normalized_metadata_source = (
            normalized_artifact
            if metadata_source is None
            else self._validate_artifact(
                metadata_source
            )
        )

        normalized_partition = (
            self._validate_partition(
                partition
            )
        )

        if (
            normalized_metadata_source
            is not normalized_artifact
        ):
            ancestor = (
                normalized_artifact.parent
            )

            while (
                ancestor is not None
                and ancestor
                is not normalized_metadata_source
            ):
                ancestor = ancestor.parent

            if ancestor is None:
                raise ValueError(
                    "metadata_source must be an exact ancestor "
                    "of the canonical filesystem artifact"
                )

        if normalized_partition is not None:
            ancestor = normalized_artifact

            while (
                ancestor is not None
                and ancestor
                is not normalized_partition.artifact
            ):
                ancestor = ancestor.parent

            if ancestor is None:
                raise ValueError(
                    "partition must be an exact ancestor "
                    "of the canonical filesystem artifact"
                )

        canonical_source = (
            self._validate_source(
                normalized_artifact.path
            )
        )

        metadata_source_path = (
            self._validate_source(
                normalized_metadata_source.path
            )
        )

        canonical_source_type = (
            self.detect_source_type(
                canonical_source
            )
        )

        metadata_source_type = (
            self.detect_source_type(
                metadata_source_path
            )
        )

        if (
            metadata_source_type
            is FilesystemSourceType.HOST_DIRECTORY
        ):
            raise UnsupportedFilesystemError(
                "Host directories do not provide authoritative "
                "image metadata evidence."
            )

        if (
            metadata_source_type
            is FilesystemSourceType.SPARSE_EXT4
        ):
            raise UnsupportedFilesystemError(
                "Sparse filesystem image reached "
                "FilesystemBackendManager after Extraction: "
                f"{metadata_source_path}"
            )

        if (
            metadata_source_type
            is FilesystemSourceType.RAW_EXT4
        ):
            metadata = (
                self._collect_ext4(
                    metadata_source_path,
                    root=root,
                    include_root=include_root,
                    max_depth=max_depth,
                    progress_callback=progress_callback,
                )
            )

            return FilesystemBackendResult(
                artifact=normalized_artifact,
                source_type=canonical_source_type,
                metadata=metadata,
                partition=normalized_partition,
            )

        if (
            metadata_source_type
            is FilesystemSourceType.EROFS
        ):
            metadata = (
                self._collect_erofs(
                    metadata_source_path,
                    root=root,
                    include_root=include_root,
                    max_depth=max_depth,
                )
            )

            return FilesystemBackendResult(
                artifact=normalized_artifact,
                source_type=canonical_source_type,
                metadata=metadata,
                partition=normalized_partition,
            )

        raise UnsupportedFilesystemError(
            self._unsupported_message(
                metadata_source_path,
                metadata_source_type,
            )
        )

    def detect_source_type(
        self,
        source: Path,
    ) -> FilesystemSourceType:
        normalized_source = (
            self._validate_source(
                source
            )
        )

        if normalized_source.is_dir():
            return (
                FilesystemSourceType
                .HOST_DIRECTORY
            )

        try:
            detected = (
                self._detector.detect(
                    normalized_source
                )
            )

        except Exception as error:
            raise FilesystemBackendManagerError(
                "Unable to detect filesystem format: "
                f"{normalized_source}"
            ) from error

        return (
            self._normalize_detected_type(
                detected
            )
        )

    def _collect_ext4(
        self,
        source: Path,
        *,
        root: str,
        include_root: bool,
        max_depth: int | None,
        progress_callback: (
            MetadataEntryProgressCallback
            | None
        ),
    ) -> FilesystemMetadata:
        try:
            backend = (
                self._ext4_backend_factory(
                    progress_callback=progress_callback,
                )
            )

        except Exception as error:
            raise FilesystemBackendManagerError(
                "Unable to create ext4 filesystem backend."
            ) from error

        try:
            return backend.collect_metadata(
                source,
                root=root,
                include_root=include_root,
                max_depth=max_depth,
            )

        except Exception as error:
            raise FilesystemBackendManagerError(
                "Unable to collect ext4 metadata from "
                f"{source}"
            ) from error

    def _collect_erofs(
        self,
        source: Path,
        *,
        root: str,
        include_root: bool,
        max_depth: int | None,
    ) -> FilesystemMetadata:
        try:
            backend = (
                self._erofs_backend_factory()
            )

        except Exception as error:
            raise FilesystemBackendManagerError(
                "Unable to create EROFS filesystem backend."
            ) from error

        try:
            return backend.collect_metadata(
                source,
                root=root,
                include_root=include_root,
                max_depth=max_depth,
            )

        except Exception as error:
            raise FilesystemBackendManagerError(
                "Unable to collect EROFS metadata from "
                f"{source}"
            ) from error

    @staticmethod
    def _filesystem_type_for_source(
        source_type: FilesystemSourceType,
    ) -> str | None:
        if (
            source_type
            is FilesystemSourceType.RAW_EXT4
        ):
            return "ext4"

        if (
            source_type
            is FilesystemSourceType.EROFS
        ):
            return "erofs"

        return None

    @classmethod
    def _normalize_detected_type(
        cls,
        detected: object,
    ) -> FilesystemSourceType:
        if isinstance(
            detected,
            FilesystemSourceType,
        ):
            return detected

        raw_value = getattr(
            detected,
            "value",
            detected,
        )

        if not isinstance(
            raw_value,
            str,
        ):
            return (
                FilesystemSourceType.UNKNOWN
            )

        normalized = (
            raw_value.strip()
            .lower()
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

        aliases = {
            "ext4": (
                FilesystemSourceType
                .RAW_EXT4
            ),
            "raw_ext4": (
                FilesystemSourceType
                .RAW_EXT4
            ),
            "ext": (
                FilesystemSourceType
                .RAW_EXT4
            ),
            "android_sparse": (
                FilesystemSourceType
                .SPARSE_EXT4
            ),
            "android_sparse_image": (
                FilesystemSourceType
                .SPARSE_EXT4
            ),
            "sparse": (
                FilesystemSourceType
                .SPARSE_EXT4
            ),
            "sparse_ext4": (
                FilesystemSourceType
                .SPARSE_EXT4
            ),
            "erofs": (
                FilesystemSourceType
                .EROFS
            ),
            "unknown": (
                FilesystemSourceType
                .UNKNOWN
            ),
        }

        return aliases.get(
            normalized,
            FilesystemSourceType.UNKNOWN,
        )

    @staticmethod
    def _validate_artifact(
        artifact: ExtractedArtifact,
    ) -> ExtractedArtifact:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        return artifact

    @staticmethod
    def _validate_partition(
        partition: InventoryPartition | None,
    ) -> InventoryPartition | None:
        if partition is None:
            return None

        if not isinstance(
            partition,
            InventoryPartition,
        ):
            raise TypeError(
                "partition must be an InventoryPartition or None"
            )

        return partition

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> Path:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path."
            )

        if not source.exists():
            raise FileNotFoundError(
                "Filesystem source does not exist: "
                f"{source}"
            )

        return source

    @staticmethod
    def _unsupported_message(
        source: Path,
        source_type: FilesystemSourceType,
    ) -> str:
        if (
            source_type
            is FilesystemSourceType.SPARSE_EXT4
        ):
            return (
                "Sparse filesystem image reached "
                "FilesystemBackendManager after Extraction: "
                f"{source}"
            )

        return (
            "Unsupported filesystem source: "
            f"{source}"
        )