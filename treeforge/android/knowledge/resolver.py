from __future__ import annotations

from treeforge.android.knowledge.profile import (
    ResolvedAndroidKnowledgeProfile,
)
from treeforge.android.knowledge.registry import (
    AndroidKnowledgeRegistry,
)
from treeforge.android.knowledge.selection import (
    AndroidKnowledgeRootSelection,
    AndroidKnowledgeSelection,
    AndroidKnowledgeSelectionSource,
)


class AndroidKnowledgeResolutionError(
    RuntimeError,
):
    """
    Raised when an installed knowledge dependency graph cannot be resolved.
    """


class AndroidKnowledgeResolver:
    """
    Resolve selected knowledge roots and their transitive dependencies.

    Resolution is deterministic and dependency-first.

    Explicit selection is supported now.

    Discovery identity inference may supply missing selections before they are
    resolved.

    Explicit selections must always take precedence over inferred selections.
    """

    def __init__(
        self,
        *,
        registry: AndroidKnowledgeRegistry,
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

    def resolve_selection(
        self,
        selection: AndroidKnowledgeSelection,
    ) -> ResolvedAndroidKnowledgeProfile:
        """
        Resolve an explicit device / Android-version selection.

        Missing fields remain unresolved in this v1 implementation.

        Discovery identity inference may supply those missing fields before this
        selection is resolved.
        """

        if not isinstance(
            selection,
            AndroidKnowledgeSelection,
        ):
            raise TypeError(
                "selection must be an "
                "AndroidKnowledgeSelection"
            )

        return self.resolve_root_selections(
            root_selections=(
                selection.explicit_roots()
            )
        )

    def resolve(
        self,
        *,
        roots: tuple[
            str,
            ...,
        ],
    ) -> ResolvedAndroidKnowledgeProfile:
        """
        Compatibility API for callers that already have canonical root IDs.

        Roots supplied here are treated as explicit selections.
        """

        if not isinstance(
            roots,
            tuple,
        ):
            raise TypeError(
                "roots must be a tuple"
            )

        root_selections = tuple(
            AndroidKnowledgeRootSelection(
                module_id=root,
                source=(
                    AndroidKnowledgeSelectionSource
                    .EXPLICIT
                ),
            )
            for root in roots
        )

        return self.resolve_root_selections(
            root_selections=root_selections
        )

    def resolve_root_selections(
        self,
        *,
        root_selections: tuple[
            AndroidKnowledgeRootSelection,
            ...,
        ],
    ) -> ResolvedAndroidKnowledgeProfile:
        """
        Resolve canonical selected roots.

        This is the common resolution path for explicit selection today and
        inferred/merged selections later.
        """

        if not isinstance(
            root_selections,
            tuple,
        ):
            raise TypeError(
                "root_selections must be a tuple"
            )

        for selection in (
            root_selections
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
            in root_selections
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

        if not root_selections:
            return (
                ResolvedAndroidKnowledgeProfile(
                    root_selections=(),
                    modules=(),
                    discovery_semantic_rules=(),
                )
            )

        resolved = []
        resolved_ids = set()
        visiting = []

        for root_id in root_ids:
            self._visit(
                root_id,
                resolved=resolved,
                resolved_ids=resolved_ids,
                visiting=visiting,
            )

        rules = tuple(
            rule
            for module in resolved
            for rule
            in module.discovery_semantic_rules
        )

        return (
            ResolvedAndroidKnowledgeProfile(
                root_selections=(
                    root_selections
                ),
                modules=tuple(
                    resolved
                ),
                discovery_semantic_rules=rules,
            )
        )

    def _visit(
        self,
        module_id: str,
        *,
        resolved,
        resolved_ids,
        visiting,
    ) -> None:
        if module_id in resolved_ids:
            return

        if module_id in visiting:
            cycle_start = (
                visiting.index(
                    module_id
                )
            )

            cycle = (
                visiting[
                    cycle_start:
                ]
                + [
                    module_id
                ]
            )

            raise (
                AndroidKnowledgeResolutionError(
                    "knowledge dependency cycle: "
                    + " -> ".join(
                        cycle
                    )
                )
            )

        try:
            module = (
                self.registry.require(
                    module_id
                )
            )
        except KeyError as error:
            raise (
                AndroidKnowledgeResolutionError(
                    "missing knowledge dependency: "
                    f"{module_id}"
                )
            ) from error

        visiting.append(
            module_id
        )

        for dependency in (
            module.dependencies
        ):
            self._visit(
                dependency,
                resolved=resolved,
                resolved_ids=resolved_ids,
                visiting=visiting,
            )

        visiting.pop()

        if module_id in resolved_ids:
            return

        resolved.append(
            module
        )

        resolved_ids.add(
            module_id
        )