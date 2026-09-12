from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.knowledge import (
    AndroidKnowledgeResolutionResult,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)
from treeforge.android.partition.layout import (
    PartitionLayout,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsingSnapshot:
    """
    Canonical immutable checkpoint at the Android Parsing boundary.

    The snapshot preserves the canonical Partition Layout handoff,
    the complete canonical Parsing result, and the exact resolved Android
    knowledge handoff that accompanied the run.

    It intentionally does not duplicate derived knowledge projections such
    as ``parsing_knowledge`` or ``universe_knowledge``. Those remain owned by
    the resolved knowledge profile and are projected from
    ``knowledge_resolution`` when required by later stages.

    ``knowledge_resolution`` may be None for a generic-only Parsing run.

    This model defines the canonical checkpoint contract only. Persistence,
    serialization, workspace storage, and restoration are application-layer
    concerns and are deliberately kept outside the Parsing models.
    """

    partition_layout: PartitionLayout

    parsing: AndroidParsingResult

    knowledge_resolution: (
        AndroidKnowledgeResolutionResult
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.partition_layout,
            PartitionLayout,
        ):
            raise TypeError(
                "partition_layout must be a PartitionLayout"
            )

        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if (
            self.knowledge_resolution is not None
            and not isinstance(
                self.knowledge_resolution,
                AndroidKnowledgeResolutionResult,
            )
        ):
            raise TypeError(
                "knowledge_resolution must be an "
                "AndroidKnowledgeResolutionResult or None"
            )

    @property
    def resolved_knowledge_profile(
        self,
    ):
        """
        Return the exact resolved Android knowledge profile, if present.
        """

        if self.knowledge_resolution is None:
            return None

        return self.knowledge_resolution.profile

    @property
    def parsing_knowledge(
        self,
    ):
        """
        Return Parsing-stage knowledge projected from the resolved profile.
        """

        profile = self.resolved_knowledge_profile

        return (
            ()
            if profile is None
            else profile.parsing_knowledge
        )

    @property
    def universe_knowledge(
        self,
    ):
        """
        Return Universe-stage knowledge projected from the resolved profile.
        """

        profile = self.resolved_knowledge_profile

        return (
            ()
            if profile is None
            else profile.universe_knowledge
        )
