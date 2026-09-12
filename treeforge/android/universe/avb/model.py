from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.avb import (
    AndroidParsedAvbAnyDescriptor,
    AndroidParsedVbmeta,
)
from treeforge.android.parsing.result import (
    ParsedAvbRegion,
    ParsedAvbVbmeta,
)


@dataclass(frozen=True, slots=True)
class AndroidUniverseVbmetaRequirement:
    """
    Canonical device-level requirement derived from one parsed VBMeta source.

    The complete Parsing-stage ParsedAvbVbmeta identity is retained exactly.
    A VBMeta source may be either:

    - standalone and backed by an InventoryPartition, or
    - embedded inside another canonical artifact.

    Universe does not invent a partition identity for embedded VBMeta.

    Literal AVB metadata remains Parsing-owned. Cross-source AVB
    reconciliation, trust-chain conclusions, applicability, and downstream
    reconstruction policy remain separate Universe work.
    """

    source: ParsedAvbVbmeta

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAvbVbmeta,
        ):
            raise TypeError(
                "source must be a ParsedAvbVbmeta"
            )

    @property
    def metadata(self) -> AndroidParsedVbmeta:
        return self.source.metadata

    @property
    def descriptors(
        self,
    ) -> tuple[AndroidParsedAvbAnyDescriptor, ...]:
        return self.metadata.descriptors

    @property
    def artifact(self):
        return self.source.artifact

    @property
    def container_artifact(self):
        return self.source.container_artifact

    @property
    def partition(self):
        return self.source.partition

    @property
    def partition_name(self) -> str | None:
        partition = self.partition

        if partition is None:
            return None

        name = partition.name

        if not isinstance(name, str) or not name:
            raise ValueError(
                "partition-backed VBMeta source must expose a "
                "non-empty partition name"
            )

        return name

    @property
    def is_partition_backed(self) -> bool:
        return self.partition is not None

    @property
    def is_embedded(self) -> bool:
        return not self.is_partition_backed

    @property
    def requirement_id(self) -> str:
        """
        Return the canonical identity of this exact VBMeta requirement.

        Standalone VBMeta is partition-backed, so the canonical partition
        name is its downstream requirement identity.

        Embedded VBMeta deliberately has no standalone partition identity.
        Parsing instead preserves the exact AVB_REGION_EXTRACTION artifact.
        Extraction guarantees canonical artifact paths are unique, so the
        exact artifact path is retained as the embedded source identity.

        No partition identity is invented for embedded VBMeta.
        """

        partition_name = self.partition_name

        if partition_name is not None:
            return partition_name

        artifact = self.artifact

        if artifact is self.container_artifact:
            raise ValueError(
                "non-partition-backed standalone VBMeta is invalid"
            )

        if artifact.parent is not self.container_artifact:
            raise ValueError(
                "embedded VBMeta must preserve its exact "
                "container-artifact identity"
            )

        path = artifact.path.as_posix()

        if not path:
            raise ValueError(
                "embedded VBMeta artifact must expose a "
                "non-empty canonical path"
            )

        return (
            "embedded-vbmeta:"
            f"{path}"
        )


@dataclass(frozen=True, slots=True)
class AndroidUniverseAvbRegion:
    """
    Exact Parsing -> Universe conservation record for one canonical AVB region.

    Universe deliberately preserves Parsing's already-established region
    disposition rather than rediscovering or reinterpreting Extraction facts.

    ``source`` is preserved by exact identity.

    For a ``parsed`` region, ``vbmeta_requirement`` is the exact Universe
    requirement created from ``source.vbmeta``.

    ``fact_derived`` and ``preserved`` regions do not carry a VBMeta
    requirement because Parsing has already established their disposition.
    """

    source: ParsedAvbRegion
    vbmeta_requirement: AndroidUniverseVbmetaRequirement | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAvbRegion,
        ):
            raise TypeError(
                "source must be a ParsedAvbRegion"
            )

        if (
            self.vbmeta_requirement is not None
            and not isinstance(
                self.vbmeta_requirement,
                AndroidUniverseVbmetaRequirement,
            )
        ):
            raise TypeError(
                "vbmeta_requirement must be an "
                "AndroidUniverseVbmetaRequirement or None"
            )

        if self.source.disposition == "parsed":
            if self.vbmeta_requirement is None:
                raise ValueError(
                    "parsed AVB region must retain its exact "
                    "Universe VBMeta requirement"
                )

            if (
                self.vbmeta_requirement.source
                is not self.source.vbmeta
            ):
                raise ValueError(
                    "parsed AVB region must preserve exact "
                    "ParsedAvbVbmeta identity through its "
                    "Universe requirement"
                )

        elif self.vbmeta_requirement is not None:
            raise ValueError(
                "only parsed AVB regions may carry a "
                "Universe VBMeta requirement"
            )

    @property
    def artifact(self):
        return self.source.artifact

    @property
    def disposition(self) -> str:
        return self.source.disposition
