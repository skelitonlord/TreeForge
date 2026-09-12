from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.extraction.model import (
    ExtractedArtifact,
)


class AndroidUniverseRuntimeContextKind(
    StrEnum,
):
    """
    Canonical structural kind of one Android runtime context.

    Runtime identity is derived from canonical Extraction provenance rather
    than device names, partition names, guest OS names, or filesystem paths.
    """

    ROOT = "root"
    NESTED_PARTITION_SET = "nested_partition_set"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimeContext:
    """
    One canonical Android runtime namespace boundary.

    ``ROOT`` represents the Android runtime rooted directly in the supplied
    provider/factory-image partition population.

    ``NESTED_PARTITION_SET`` represents a distinct Android runtime whose
    logical partitions originate from an exact nested logical-partition
    container discovered beneath another materialized filesystem.

    ``partition_container`` retains that exact canonical Extraction artifact
    as provenance and runtime identity.

    Human guest/runtime labels are deliberately not runtime identity.
    """

    kind: AndroidUniverseRuntimeContextKind

    partition_container: (
        ExtractedArtifact
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidUniverseRuntimeContextKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseRuntimeContextKind"
            )

        if (
            self.partition_container
            is not None
            and not isinstance(
                self.partition_container,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "partition_container must be an "
                "ExtractedArtifact or None"
            )

        if (
            self.kind
            is AndroidUniverseRuntimeContextKind.ROOT
        ):
            if self.partition_container is not None:
                raise ValueError(
                    "ROOT runtime context cannot have a "
                    "nested partition container"
                )

            return

        if (
            self.kind
            is AndroidUniverseRuntimeContextKind
            .NESTED_PARTITION_SET
        ):
            if self.partition_container is None:
                raise ValueError(
                    "NESTED_PARTITION_SET runtime context "
                    "requires its canonical partition container"
                )

            return

        raise ValueError(
            "unsupported Android runtime context kind"
        )

    @property
    def is_root(
        self,
    ) -> bool:
        return (
            self.kind
            is AndroidUniverseRuntimeContextKind.ROOT
        )

    @property
    def is_nested(
        self,
    ) -> bool:
        return (
            self.kind
            is AndroidUniverseRuntimeContextKind
            .NESTED_PARTITION_SET
        )
