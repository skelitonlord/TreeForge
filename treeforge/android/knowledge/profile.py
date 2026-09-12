from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.knowledge.model import (
    AndroidKnowledgeCapability,
    AndroidKnowledgeModule,
)
from treeforge.android.knowledge.stages import (
    AndroidExtractionKnowledge,
    AndroidFilesystemMetadataKnowledge,
    AndroidParsingKnowledge,
    AndroidPartitionLayoutKnowledge,
)
from treeforge.android.knowledge.universe import (
    AndroidUniverseKnowledge,
)
from treeforge.android.knowledge.selection import (
    AndroidKnowledgeRootSelection,
)
from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedAndroidKnowledgeProfile:
    """
    Immutable resolved knowledge graph for one TreeForge run.

    modules are ordered dependency-first.

    root_selections preserve which top-level identities were selected and how
    they were obtained.

    discovery_semantic_rules are flattened in module order and are ready for
    composition with generic Android semantic rules.
    """

    root_selections: tuple[
        AndroidKnowledgeRootSelection,
        ...,
    ]

    modules: tuple[
        AndroidKnowledgeModule,
        ...,
    ]

    discovery_semantic_rules: tuple[
        ProviderArtifactSemanticRule,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.root_selections,
            tuple,
        ):
            raise TypeError(
                "root_selections must be a tuple"
            )

        if not isinstance(
            self.modules,
            tuple,
        ):
            raise TypeError(
                "modules must be a tuple"
            )

        if not isinstance(
            self.discovery_semantic_rules,
            tuple,
        ):
            raise TypeError(
                "discovery_semantic_rules must "
                "be a tuple"
            )

        for selection in (
            self.root_selections
        ):
            if not isinstance(
                selection,
                AndroidKnowledgeRootSelection,
            ):
                raise TypeError(
                    "root_selections must contain "
                    "AndroidKnowledgeRootSelection "
                    "instances"
                )

        root_ids = tuple(
            selection.module_id
            for selection
            in self.root_selections
        )

        if (
            len(root_ids)
            != len(
                set(
                    root_ids
                )
            )
        ):
            raise ValueError(
                "root selections must not contain "
                "duplicate module IDs"
            )

        module_ids = tuple(
            module.module_id
            for module in self.modules
        )

        if (
            len(module_ids)
            != len(
                set(
                    module_ids
                )
            )
        ):
            raise ValueError(
                "modules must not contain "
                "duplicate module IDs"
            )

        rule_ids = tuple(
            rule.rule_id
            for rule
            in self.discovery_semantic_rules
        )

        if (
            len(rule_ids)
            != len(
                set(
                    rule_ids
                )
            )
        ):
            raise ValueError(
                "discovery semantic rules must "
                "not contain duplicate rule IDs"
            )

    @property
    def roots(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Compatibility/convenience view of selected root module IDs.
        """

        return tuple(
            selection.module_id
            for selection
            in self.root_selections
        )

    def modules_supporting(
        self,
        capability: AndroidKnowledgeCapability,
    ) -> tuple[
        AndroidKnowledgeModule,
        ...,
    ]:
        """
        Return resolved modules exposing one capability.

        Resolution order is preserved so stage consumers receive the same
        deterministic dependency-first ordering as the canonical profile.
        """

        if not isinstance(
            capability,
            AndroidKnowledgeCapability,
        ):
            raise TypeError(
                "capability must be an "
                "AndroidKnowledgeCapability"
            )

        return tuple(
            module
            for module in self.modules
            if module.supports(
                capability
            )
        )

    @property
    def partition_layout_knowledge(
        self,
    ) -> tuple[
        AndroidPartitionLayoutKnowledge,
        ...,
    ]:
        return tuple(
            module.partition_layout
            for module in self.modules_supporting(
                AndroidKnowledgeCapability
                .PARTITION_LAYOUT
            )
            if module.partition_layout is not None
        )

    @property
    def extraction_knowledge(
        self,
    ) -> tuple[
        AndroidExtractionKnowledge,
        ...,
    ]:
        return tuple(
            module.extraction
            for module in self.modules_supporting(
                AndroidKnowledgeCapability
                .EXTRACTION
            )
            if module.extraction is not None
        )

    @property
    def filesystem_metadata_knowledge(
        self,
    ) -> tuple[
        AndroidFilesystemMetadataKnowledge,
        ...,
    ]:
        return tuple(
            module.filesystem_metadata
            for module in self.modules_supporting(
                AndroidKnowledgeCapability
                .FILESYSTEM_METADATA
            )
            if module.filesystem_metadata is not None
        )

    @property
    def parsing_knowledge(
        self,
    ) -> tuple[
        AndroidParsingKnowledge,
        ...,
    ]:
        return tuple(
            module.parsing
            for module in self.modules_supporting(
                AndroidKnowledgeCapability
                .PARSING
            )
            if module.parsing is not None
        )

    @property
    def universe_knowledge(
        self,
    ) -> tuple[
        AndroidUniverseKnowledge,
        ...,
    ]:
        """
        Return all selected Universe-stage contributions dependency-first.
        """

        return tuple(
            module.universe
            for module in self.modules_supporting(
                AndroidKnowledgeCapability.UNIVERSE
            )
            if module.universe is not None
        )

    @property
    def module_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            module.module_id
            for module in self.modules
        )