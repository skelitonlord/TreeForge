from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class KnowledgeApplicationStage(
    StrEnum,
):
    """
    Pipeline boundary at which optional Android Knowledge may be applied.

    Knowledge application is disabled by default.

    Resolution/profile availability is intentionally separate from application:
    TreeForge may know which profile applies without allowing that profile to
    alter the canonical evidence flowing through a stage.
    """

    DISCOVERY = "discovery"
    PARTITION_LAYOUT = "partition_layout"
    EXTRACTION = "extraction"
    FILESYSTEM_METADATA = "filesystem_metadata"
    PARSING = "parsing"
    UNIVERSE = "universe"
    RUNTIME_LINKING = "runtime_linking"
    RECONSTRUCTION_OWNERSHIP = "reconstruction_ownership"
    RECONSTRUCTION_PLANNING = "reconstruction_planning"
    RECONSTRUCTION = "reconstruction"
    DEVICE_TREE = "device_tree"


@dataclass(
    frozen=True,
    slots=True,
)
class KnowledgeApplicationPolicy:
    """
    Immutable policy controlling optional Knowledge application.

    Empty ``enabled_stages`` is the canonical default: no pipeline stage is
    permitted to apply Knowledge-derived evidence unless explicitly enabled.

    This policy does not control Knowledge resolution, profile identity,
    provenance, serialization, or reporting.
    """

    enabled_stages: frozenset[
        KnowledgeApplicationStage
    ] = frozenset()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.enabled_stages,
            frozenset,
        ):
            raise TypeError(
                "enabled_stages must be a frozenset"
            )

        for stage in self.enabled_stages:
            if not isinstance(
                stage,
                KnowledgeApplicationStage,
            ):
                raise TypeError(
                    "enabled_stages must contain "
                    "KnowledgeApplicationStage instances"
                )

    def enabled_for(
        self,
        stage: KnowledgeApplicationStage,
    ) -> bool:
        if not isinstance(
            stage,
            KnowledgeApplicationStage,
        ):
            raise TypeError(
                "stage must be a KnowledgeApplicationStage"
            )

        return stage in self.enabled_stages

    @classmethod
    def all_disabled(
        cls,
    ) -> "KnowledgeApplicationPolicy":
        return cls()

    @classmethod
    def all_enabled(
        cls,
    ) -> "KnowledgeApplicationPolicy":
        return cls(
            enabled_stages=frozenset(
                KnowledgeApplicationStage
            )
        )
