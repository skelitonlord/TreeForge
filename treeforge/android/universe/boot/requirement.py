from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.result import (
    ParsedBootImage,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)
from treeforge.android.universe.boot.semantics import (
    AndroidUniverseBootSemantics,
    AndroidUniverseVendorBootSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootRequirement:
    """
    Canonical Universe requirement for one Parsing-owned boot-family image.

    Parsing owns the exact container identity, header-family identity,
    InventoryPartition, semantic header metadata, component artifacts, and
    optional bootconfig Parsing result.

    Universe preserves that exact source and adds semantic interpretation
    without constraining boot-family identity to a fixed list of partition
    names.
    """

    source: ParsedBootImage

    semantics: (
        AndroidUniverseBootSemantics
        | AndroidUniverseVendorBootSemantics
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedBootImage,
        ):
            raise TypeError(
                "source must be a ParsedBootImage"
            )

        if (
            self.source.container_format
            == "android_boot"
        ):
            if not isinstance(
                self.semantics,
                AndroidUniverseBootSemantics,
            ):
                raise TypeError(
                    "android_boot source requires "
                    "AndroidUniverseBootSemantics"
                )

        elif (
            self.source.container_format
            == "android_vendor_boot"
        ):
            if not isinstance(
                self.semantics,
                AndroidUniverseVendorBootSemantics,
            ):
                raise TypeError(
                    "android_vendor_boot source requires "
                    "AndroidUniverseVendorBootSemantics"
                )

        else:
            raise ValueError(
                "unsupported canonical boot container format: "
                f"{self.source.container_format}"
            )

    @property
    def container_format(
        self,
    ) -> str:
        return self.source.container_format

    @property
    def container_kind(
        self,
    ) -> str:
        return self.source.container_kind

    @property
    def partition(
        self,
    ) -> InventoryPartition:
        return self.source.partition

    @property
    def source_path(
        self,
    ) -> Path:
        return self.partition.artifact.path

    @property
    def component_artifacts(
        self,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        return self.source.component_artifacts

    def component_artifact(
        self,
        semantic_name: str,
    ) -> ExtractedArtifact | None:
        if not isinstance(
            semantic_name,
            str,
        ):
            raise TypeError(
                "semantic_name must be a string"
            )

        semantic_name = (
            semantic_name.strip()
        )

        if not semantic_name:
            raise ValueError(
                "semantic_name cannot be empty"
            )

        matches = tuple(
            artifact
            for artifact
            in self.component_artifacts
            if (
                artifact.semantic_name
                == semantic_name
            )
        )

        if len(matches) > 1:
            raise ValueError(
                "canonical boot-family requirement contains "
                "ambiguous component identity: "
                f"{semantic_name}"
            )

        return (
            matches[0]
            if matches
            else None
        )

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "boot-family:"
            f"{self.container_format}:"
            f"{self.container_kind}:"
            f"{self.partition.name}:"
            f"{self.source_path.as_posix()}"
        )


AndroidUniverseBootFamilyRequirement = (
    AndroidUniverseBootRequirement
)
