from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import TYPE_CHECKING

from treeforge.core.config import (
    Config,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
)
from treeforge.workspace.workspace import (
    Workspace,
)


if TYPE_CHECKING:
    from treeforge.android.extraction import (
        AndroidExtractionResult,
    )
    from treeforge.android.knowledge import (
        AndroidKnowledgeResolutionResult,
    )
    from treeforge.android.filesystem.inventory import (
        FilesystemMetadataInventory,
    )
    from treeforge.android.partition import (
        PartitionLayout,
    )
    from treeforge.android.partition.inventory import (
        PartitionInventory,
    )
    from treeforge.android.parsing.result import (
        AndroidParsingResult,
    )
    from treeforge.android.universe.model import (
        AndroidDeviceUniverse,
    )
    from treeforge.android.runtime_linking.model import (
        AndroidRuntimeLinking,
    )
    from treeforge.android.version.model import (
        AndroidSemanticVersionSelection,
    )
    from treeforge.android.providers.collection import (
        ProviderCollection,
    )


@dataclass
class Context:
    """
    Shared mutable execution context for the TreeForge pipeline.

    Canonical immutable models are attached as pipeline stages complete.

    ProviderCollection is the canonical provider-level state.

    AndroidExtractionResult is the canonical source transformation state
    established after Discovery/Layout and before downstream inventories.

    Individual provider results, provider inventories, and extraction lineage
    remain reachable through their canonical aggregates rather than being
    duplicated as independent Context fields.
    """

    workspace: Workspace
    config: Config

    input_path: Path | None = None

    requested_android_version: str | None = None

    android_semantic_version: (
        AndroidSemanticVersionSelection
        | None
    ) = None

    provider_collection: (
        ProviderCollection
        | None
    ) = None

    knowledge_resolution: (
        AndroidKnowledgeResolutionResult
        | None
    ) = None

    knowledge_application_policy: (
        KnowledgeApplicationPolicy
    ) = field(
        default_factory=KnowledgeApplicationPolicy
    )

    partition_layout: (
        PartitionLayout
        | None
    ) = None

    android_extraction: (
        AndroidExtractionResult
        | None
    ) = None

    partition_inventory: (
        PartitionInventory
        | None
    ) = None

    filesystem_inventory: (
        FilesystemMetadataInventory
        | None
    ) = None

    android_parsing: (
        AndroidParsingResult
        | None
    ) = None

    android_device_universe: (
        AndroidDeviceUniverse
        | None
    ) = None

    android_runtime_linking: (
        AndroidRuntimeLinking
        | None
    ) = None

    @property
    def resolved_knowledge_profile(
        self,
    ):
        """
        Canonical dependency-ordered Android knowledge profile.

        None means module knowledge has not been resolved, including raw
        generic-only Discovery contexts.
        """

        resolution = (
            self.knowledge_resolution
        )

        if resolution is None:
            return None

        return resolution.profile

    @property
    def partition_layout_knowledge(
        self,
    ):
        profile = (
            self.resolved_knowledge_profile
        )

        return (
            ()
            if profile is None
            else profile.partition_layout_knowledge
        )

    @property
    def extraction_knowledge(
        self,
    ):
        profile = (
            self.resolved_knowledge_profile
        )

        return (
            ()
            if profile is None
            else profile.extraction_knowledge
        )

    @property
    def filesystem_metadata_knowledge(
        self,
    ):
        profile = (
            self.resolved_knowledge_profile
        )

        return (
            ()
            if profile is None
            else profile.filesystem_metadata_knowledge
        )

    @property
    def parsing_knowledge(
        self,
    ):
        profile = (
            self.resolved_knowledge_profile
        )

        return (
            ()
            if profile is None
            else profile.parsing_knowledge
        )

    @property
    def universe_knowledge(
        self,
    ):
        profile = (
            self.resolved_knowledge_profile
        )

        return (
            ()
            if profile is None
            else profile.universe_knowledge
        )
