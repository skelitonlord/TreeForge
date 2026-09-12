from __future__ import annotations

from treeforge.android.discovery.identity import (
    AndroidIdentityInferenceResult,
)
from treeforge.android.knowledge.profile import (
    ResolvedAndroidKnowledgeProfile,
)
from treeforge.android.knowledge.registry import (
    AndroidKnowledgeRegistry,
)
from treeforge.android.knowledge.resolution_result import (
    AndroidKnowledgeResolutionResult,
)
from treeforge.android.knowledge.resolver import (
    AndroidKnowledgeResolver,
)
from treeforge.android.knowledge.selection import (
    AndroidKnowledgeSelection,
)
from treeforge.android.knowledge.selection_resolver import (
    AndroidKnowledgeSelectionResolver,
)


class AndroidKnowledgeResolutionService:
    """
    Resolve the post-Discovery Android knowledge handoff.

    This service coordinates existing canonical components only:

        explicit selection
            +
        Discovery identity inference
            ↓
        AndroidKnowledgeSelectionResolver
            ↓
        AndroidKnowledgeResolver
            ↓
        AndroidKnowledgeResolutionResult

    It does not perform Discovery or semantic enrichment.
    """

    def __init__(
        self,
        *,
        registry: AndroidKnowledgeRegistry,
        selection_resolver: (
            AndroidKnowledgeSelectionResolver
            | None
        ) = None,
        knowledge_resolver: (
            AndroidKnowledgeResolver
            | None
        ) = None,
    ) -> None:
        if not isinstance(
            registry,
            AndroidKnowledgeRegistry,
        ):
            raise TypeError(
                "registry must be an "
                "AndroidKnowledgeRegistry"
            )

        self.registry = registry

        self.selection_resolver = (
            selection_resolver
            if selection_resolver is not None
            else AndroidKnowledgeSelectionResolver(
                registry=registry
            )
        )

        if not isinstance(
            self.selection_resolver,
            AndroidKnowledgeSelectionResolver,
        ):
            raise TypeError(
                "selection_resolver must be an "
                "AndroidKnowledgeSelectionResolver"
            )

        self.knowledge_resolver = (
            knowledge_resolver
            if knowledge_resolver is not None
            else AndroidKnowledgeResolver(
                registry=registry
            )
        )

        if not isinstance(
            self.knowledge_resolver,
            AndroidKnowledgeResolver,
        ):
            raise TypeError(
                "knowledge_resolver must be an "
                "AndroidKnowledgeResolver"
            )

    def resolve(
        self,
        *,
        explicit: AndroidKnowledgeSelection,
        inferred: AndroidIdentityInferenceResult,
    ) -> AndroidKnowledgeResolutionResult:
        if not isinstance(
            explicit,
            AndroidKnowledgeSelection,
        ):
            raise TypeError(
                "explicit must be an "
                "AndroidKnowledgeSelection"
            )

        if not isinstance(
            inferred,
            AndroidIdentityInferenceResult,
        ):
            raise TypeError(
                "inferred must be an "
                "AndroidIdentityInferenceResult"
            )

        roots = (
            self.selection_resolver.resolve(
                explicit=explicit,
                inferred=inferred,
            )
        )

        profile = (
            self.knowledge_resolver
            .resolve_root_selections(
                root_selections=roots
            )
        )

        if not isinstance(
            profile,
            ResolvedAndroidKnowledgeProfile,
        ):
            raise TypeError(
                "knowledge_resolver must return a "
                "ResolvedAndroidKnowledgeProfile"
            )

        return AndroidKnowledgeResolutionResult(
            explicit_selection=explicit,
            inferred_identity=inferred,
            root_selections=roots,
            profile=profile,
        )