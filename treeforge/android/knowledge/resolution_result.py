from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.discovery.identity import (
    AndroidIdentityInferenceResult,
)
from treeforge.android.knowledge.profile import (
    ResolvedAndroidKnowledgeProfile,
)
from treeforge.android.knowledge.selection import (
    AndroidKnowledgeRootSelection,
    AndroidKnowledgeSelection,
    AndroidKnowledgeSelectionSource,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidKnowledgeResolutionResult:
    """
    Immutable handoff between Discovery identity inference and resolved Android
    knowledge.

    This model preserves:

    - the caller's explicit selection;
    - Discovery's evidence-backed inferred identity;
    - the final canonical root selections after precedence is applied;
    - the resolved knowledge profile.

    Precedence is determined before this model is constructed:

        explicit
            >
        inferred
            >
        absent

    Discovery evidence is preserved even when an explicit selection overrides
    the inferred value.

    This model performs no Discovery, inference, dependency resolution, or
    semantic enrichment itself.
    """

    explicit_selection: AndroidKnowledgeSelection

    inferred_identity: AndroidIdentityInferenceResult

    root_selections: tuple[
        AndroidKnowledgeRootSelection,
        ...,
    ]

    profile: ResolvedAndroidKnowledgeProfile

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.explicit_selection,
            AndroidKnowledgeSelection,
        ):
            raise TypeError(
                "explicit_selection must be an "
                "AndroidKnowledgeSelection"
            )

        if not isinstance(
            self.inferred_identity,
            AndroidIdentityInferenceResult,
        ):
            raise TypeError(
                "inferred_identity must be an "
                "AndroidIdentityInferenceResult"
            )

        if not isinstance(
            self.root_selections,
            tuple,
        ):
            raise TypeError(
                "root_selections must be a tuple"
            )

        for root in self.root_selections:
            if not isinstance(
                root,
                AndroidKnowledgeRootSelection,
            ):
                raise TypeError(
                    "root_selections must contain "
                    "AndroidKnowledgeRootSelection instances"
                )

        if not isinstance(
            self.profile,
            ResolvedAndroidKnowledgeProfile,
        ):
            raise TypeError(
                "profile must be a "
                "ResolvedAndroidKnowledgeProfile"
            )

        root_ids = tuple(
            root.module_id
            for root in self.root_selections
        )

        if (
            root_ids
            != self.profile.roots
        ):
            raise ValueError(
                "profile roots must match "
                "root_selections"
            )

    @property
    def explicit_roots(
        self,
    ) -> tuple[
        AndroidKnowledgeRootSelection,
        ...,
    ]:
        return tuple(
            root
            for root in self.root_selections
            if (
                root.source
                is AndroidKnowledgeSelectionSource.EXPLICIT
            )
        )

    @property
    def inferred_roots(
        self,
    ) -> tuple[
        AndroidKnowledgeRootSelection,
        ...,
    ]:
        return tuple(
            root
            for root in self.root_selections
            if (
                root.source
                is AndroidKnowledgeSelectionSource.INFERRED
            )
        )

    @property
    def has_explicit_roots(
        self,
    ) -> bool:
        return bool(
            self.explicit_roots
        )

    @property
    def has_inferred_roots(
        self,
    ) -> bool:
        return bool(
            self.inferred_roots
        )

    @property
    def module_ids(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.profile.module_ids