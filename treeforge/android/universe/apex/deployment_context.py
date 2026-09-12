from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionOperation,
)


class AndroidUniverseApexDeploymentPartition(
    StrEnum,
):
    """
    Literal Android partition placement relevant to linkerconfig APEX
    semantics.

    This preserves deployment placement before AOSP's higher-level
    system/product/vendor classification is applied. In particular,
    PRODUCT remains distinct because its effective linkerconfig role
    depends on Treble state.
    """

    SYSTEM = "system"
    SYSTEM_EXT = "system_ext"
    PRODUCT = "product"
    VENDOR = "vendor"
    ODM = "odm"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApexDeploymentContext:
    """
    Canonical deployment-placement conclusion for one APEX.

    ``filesystem_artifact`` is the nearest enclosing materialized
    filesystem. ``relative_path`` preserves the exact location of the
    APEX source within that filesystem.
    """

    partition: AndroidUniverseApexDeploymentPartition
    filesystem_artifact: ExtractedArtifact
    relative_path: PurePosixPath

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.partition,
            AndroidUniverseApexDeploymentPartition,
        ):
            raise TypeError(
                "partition must be an "
                "AndroidUniverseApexDeploymentPartition"
            )

        if not isinstance(
            self.filesystem_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "filesystem_artifact must be an ExtractedArtifact"
            )

        if (
            self.filesystem_artifact.operation
            is not ExtractionOperation.FILESYSTEM_EXTRACTION
        ):
            raise ValueError(
                "filesystem_artifact must be a filesystem extraction"
            )

        if not isinstance(
            self.relative_path,
            PurePosixPath,
        ):
            raise TypeError(
                "relative_path must be a PurePosixPath"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )


class AndroidUniverseApexDeploymentContextResolver:
    """
    Derive APEX deployment placement from canonical Extraction ancestry.

    Physical guest/logical-partition names are not treated as Android
    deployment roles. Android-visible placement within the nearest
    enclosing filesystem takes precedence.
    """

    _PARTITIONS = {
        "system": (
            AndroidUniverseApexDeploymentPartition.SYSTEM
        ),
        "system_ext": (
            AndroidUniverseApexDeploymentPartition.SYSTEM_EXT
        ),
        "product": (
            AndroidUniverseApexDeploymentPartition.PRODUCT
        ),
        "vendor": (
            AndroidUniverseApexDeploymentPartition.VENDOR
        ),
        "odm": (
            AndroidUniverseApexDeploymentPartition.ODM
        ),
    }

    @classmethod
    def resolve_artifact(
        cls,
        artifact: ExtractedArtifact,
    ) -> AndroidUniverseApexDeploymentContext:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        current = artifact
        source_within_filesystem = None
        filesystem_artifact = None

        while current is not None:
            parent = current.parent

            if (
                parent is not None
                and parent.operation
                is ExtractionOperation.FILESYSTEM_EXTRACTION
            ):
                source_within_filesystem = current
                filesystem_artifact = parent
                break

            current = parent

        if (
            source_within_filesystem is None
            or filesystem_artifact is None
        ):
            raise ValueError(
                "APEX artifact does not descend from a canonical "
                "filesystem extraction"
            )

        try:
            relative = (
                source_within_filesystem.path
                .relative_to(
                    filesystem_artifact.path
                )
            )
        except ValueError as error:
            raise ValueError(
                "APEX filesystem descendant path is outside its "
                "canonical filesystem artifact"
            ) from error

        relative_path = PurePosixPath(
            relative.as_posix()
        )

        partition = cls._partition_from_relative_path(
            relative_path
        )

        if (
            partition
            is AndroidUniverseApexDeploymentPartition.UNKNOWN
        ):
            partition = cls._partition_from_filesystem(
                filesystem_artifact,
                relative_path,
            )

        return AndroidUniverseApexDeploymentContext(
            partition=partition,
            filesystem_artifact=filesystem_artifact,
            relative_path=relative_path,
        )

    @classmethod
    def _partition_from_relative_path(
        cls,
        relative_path: PurePosixPath,
    ) -> AndroidUniverseApexDeploymentPartition:
        parts = relative_path.parts

        if len(
            parts
        ) < 2:
            return (
                AndroidUniverseApexDeploymentPartition.UNKNOWN
            )

        candidate = cls._PARTITIONS.get(
            parts[0]
        )

        if (
            candidate is not None
            and parts[1] == "apex"
        ):
            return candidate

        return (
            AndroidUniverseApexDeploymentPartition.UNKNOWN
        )

    @classmethod
    def _partition_from_filesystem(
        cls,
        filesystem_artifact: ExtractedArtifact,
        relative_path: PurePosixPath,
    ) -> AndroidUniverseApexDeploymentPartition:
        parts = relative_path.parts

        if (
            not parts
            or parts[0] != "apex"
        ):
            return (
                AndroidUniverseApexDeploymentPartition.UNKNOWN
            )

        semantic_name = (
            filesystem_artifact.semantic_name
        )

        if semantic_name is None:
            return (
                AndroidUniverseApexDeploymentPartition.UNKNOWN
            )

        return cls._PARTITIONS.get(
            semantic_name,
            AndroidUniverseApexDeploymentPartition.UNKNOWN,
        )
