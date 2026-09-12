from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
)
from treeforge.android.filesystem.backends.manager import (
    FilesystemBackendResult,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadataEntry,
    normalize_metadata_path,
)


@dataclass(
    frozen=True,
    slots=True,
)
class FilesystemMetadataInventoryEntry:
    """
    Filesystem metadata collected for one exact canonical Extraction artifact.

    Partition identity remains available when this filesystem is
    partition-backed, but it is not the filesystem's fundamental identity.
    """

    result: FilesystemBackendResult

    def __post_init__(
        self,
    ) -> None:
        """
        Validate the inventory entry.
        """

        if not isinstance(
            self.result,
            FilesystemBackendResult,
        ):
            raise TypeError(
                "result must be a "
                "FilesystemBackendResult"
            )

    @property
    def partition_name(
        self,
    ) -> str | None:
        """
        Return the canonical partition name when partition-backed.
        """

        partition = self.result.partition

        if partition is None:
            return None

        return partition.name

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        """
        Return the exact canonical Extraction artifact.
        """

        return self.result.artifact

    @property
    def source_path(
        self,
    ) -> Path:
        """
        Return the physical source path of the canonical filesystem artifact.
        """

        return self.result.artifact.path


    def materialized_path(
        self,
        metadata_entry: FilesystemMetadataEntry,
    ) -> Path:
        """
        Project one exact canonical metadata entry into materialized storage.

        ``metadata_entry.path`` is filesystem-native. The canonical Extraction
        artifact represents that filesystem root in materialized host storage.

        This method performs a namespace projection only. The resulting host
        path is not required to exist because authoritative metadata may
        describe entries that cannot or should not be materialized as host
        nodes, such as some CPIO special-file records.
        """

        if not isinstance(
            metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "metadata_entry must be a FilesystemMetadataEntry"
            )

        canonical_entry = (
            self.result
            .metadata
            .entries
            .get(
                metadata_entry.path
            )
        )

        if canonical_entry is not metadata_entry:
            raise ValueError(
                "metadata_entry must be the exact canonical entry "
                "owned by this filesystem metadata result"
            )

        root = self.artifact.path

        if not root.is_dir():
            raise ValueError(
                "canonical filesystem artifact must be a directory "
                "to project filesystem-native paths"
            )

        native_path = normalize_metadata_path(
            metadata_entry.path
        )

        parts = tuple(
            part
            for part in native_path.split("/")
            if part
        )

        if ".." in parts:
            raise ValueError(
                "filesystem-native path cannot contain parent traversal"
            )

        materialized = root.joinpath(
            *parts
        )

        try:
            relative = materialized.relative_to(
                root
            )
        except ValueError as error:
            raise ValueError(
                "filesystem-native path escapes canonical "
                "materialized filesystem root"
            ) from error

        if ".." in relative.parts:
            raise ValueError(
                "filesystem-native path escapes canonical "
                "materialized filesystem root"
            )

        return materialized

    def filesystem_path_for_materialized_path(
        self,
        materialized_path: Path,
    ) -> str:
        """
        Return the filesystem-native path for one materialized host path.

        The supplied path must be inside this entry's exact canonical
        Extraction artifact. No Android logical namespace interpretation is
        performed here.
        """

        if not isinstance(
            materialized_path,
            Path,
        ):
            raise TypeError(
                "materialized_path must be a pathlib.Path"
            )

        root = self.artifact.path

        if not root.is_dir():
            raise ValueError(
                "canonical filesystem artifact must be a directory "
                "to resolve materialized paths"
            )

        try:
            relative = materialized_path.relative_to(
                root
            )
        except ValueError as error:
            raise ValueError(
                "materialized_path is outside the canonical "
                "filesystem artifact"
            ) from error

        if ".." in relative.parts:
            raise ValueError(
                "materialized_path escapes the canonical filesystem artifact"
            )

        if not relative.parts:
            return "/"

        return normalize_metadata_path(
            "/"
            + relative.as_posix()
        )

    def metadata_entry_for_materialized_path(
        self,
        materialized_path: Path,
    ) -> FilesystemMetadataEntry | None:
        """
        Return canonical metadata for one materialized host path.

        This is the inverse of ``materialized_path`` for entries represented in
        both namespaces. Missing metadata returns ``None`` rather than implying
        host-observed metadata.
        """

        filesystem_path = (
            self.filesystem_path_for_materialized_path(
                materialized_path
            )
        )

        return self.result.metadata.get(
            filesystem_path
        )


@dataclass(
    frozen=True,
    slots=True,
)
class FilesystemMetadataInventory:
    """
    Immutable collection of canonical filesystem metadata results.

    Entries are identified by exact canonical Extraction artifact identity.
    Partition identity remains an optional projection for partition-backed
    filesystems.
    """

    entries: tuple[
        FilesystemMetadataInventoryEntry,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        """
        Validate the inventory and reject duplicate filesystem artifacts.
        """

        seen_artifacts: set[int] = set()
        seen_paths: set[Path] = set()

        for entry in self.entries:
            if not isinstance(
                entry,
                FilesystemMetadataInventoryEntry,
            ):
                raise TypeError(
                    "entries must contain only "
                    "FilesystemMetadataInventoryEntry "
                    "objects"
                )

            artifact = entry.result.artifact
            artifact_id = id(
                artifact
            )

            if artifact_id in seen_artifacts:
                raise ValueError(
                    "Duplicate filesystem metadata "
                    "Extraction artifact identity: "
                    f"{artifact.path}"
                )

            if artifact.path in seen_paths:
                raise ValueError(
                    "Duplicate filesystem metadata "
                    "artifact path: "
                    f"{artifact.path}"
                )

            seen_artifacts.add(
                artifact_id
            )
            seen_paths.add(
                artifact.path
            )

    def __len__(
        self,
    ) -> int:
        """
        Return the number of collected filesystems.
        """

        return len(
            self.entries
        )

    def __iter__(
        self,
    ):
        """
        Iterate over filesystem inventory entries.
        """

        return iter(
            self.entries
        )

    def __bool__(
        self,
    ) -> bool:
        """
        Return whether the inventory contains any entries.
        """

        return bool(
            self.entries
        )

    @property
    def partition_names(
        self,
    ) -> tuple[str, ...]:
        """
        Return canonical partition names in inventory order.
        """

        return tuple(
            entry.partition_name
            for entry in self.entries
            if entry.partition_name is not None
        )

    @property
    def results(
        self,
    ) -> tuple[
        FilesystemBackendResult,
        ...,
    ]:
        """
        Return backend results in inventory order.
        """

        return tuple(
            entry.result
            for entry in self.entries
        )

    @property
    def filesystem_types(
        self,
    ) -> tuple[str, ...]:
        """
        Return collected filesystem type names in inventory order.
        """

        return tuple(
            entry.result.metadata.filesystem_type
            for entry in self.entries
        )

    def contains(
        self,
        partition_name: str,
    ) -> bool:
        """
        Return whether metadata exists for a partition.
        """

        return any(
            entry.partition_name
            == partition_name
            for entry in self.entries
        )

    def entry(
        self,
        partition_name: str,
    ) -> FilesystemMetadataInventoryEntry:
        """
        Return the complete inventory entry for a partition.

        Raises KeyError when the partition is not present.
        """

        for entry in self.entries:
            if (
                entry.partition_name
                == partition_name
            ):
                return entry

        raise KeyError(
            partition_name
        )

    def result(
        self,
        partition_name: str,
    ) -> FilesystemBackendResult:
        """
        Return the backend result for a partition.

        Raises KeyError when the partition is not present.
        """

        return self.entry(
            partition_name
        ).result

    def entry_for_artifact(
        self,
        artifact: ExtractedArtifact,
    ) -> FilesystemMetadataInventoryEntry:
        """
        Return metadata for one exact canonical Extraction artifact.

        Exact object identity is authoritative.
        """

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        for entry in self.entries:
            if entry.result.artifact is artifact:
                return entry

        raise KeyError(
            artifact.path
        )

    def contains_artifact(
        self,
        artifact: ExtractedArtifact,
    ) -> bool:
        """
        Return whether metadata exists for one exact Extraction artifact.
        """

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        return any(
            entry.result.artifact is artifact
            for entry in self.entries
        )

