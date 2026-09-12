from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from treeforge.android.knowledge.model import (
    AndroidKnowledgeModule,
)
from treeforge.android.knowledge.universe import (
    AndroidUniverseVintfSelectionKnowledge,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityEvidence,
    AndroidUniverseApplicabilityEvidenceKind,
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.vintf.document import (
    AndroidUniverseVintfDocumentKind,
    AndroidUniverseVintfDocumentSide,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)


class AndroidUniverseVintfSelectionRole(
    StrEnum,
):
    """
    Generic semantic roles for source-tree VINTF inputs.

    These names deliberately avoid DEVICE_* Make variable terminology.
    """

    DEVICE_MANIFEST = "device_manifest"
    DEVICE_COMPATIBILITY_MATRIX = (
        "device_compatibility_matrix"
    )
    FRAMEWORK_COMPATIBILITY_MATRIX = (
        "framework_compatibility_matrix"
    )
    PRODUCT_COMPATIBILITY_MATRIX = (
        "product_compatibility_matrix"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfKnowledgeObservation:
    """
    One exact VINTF source-selection observation from a resolved module.

    The exact AndroidKnowledgeModule is retained so platform/device/version
    provenance is never collapsed into a string-only result.
    """

    selection: AndroidUniverseVintfSelectionKnowledge
    knowledge_module: AndroidKnowledgeModule

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.selection,
            AndroidUniverseVintfSelectionKnowledge,
        ):
            raise TypeError(
                "selection must be an "
                "AndroidUniverseVintfSelectionKnowledge"
            )

        if not isinstance(
            self.knowledge_module,
            AndroidKnowledgeModule,
        ):
            raise TypeError(
                "knowledge_module must be an "
                "AndroidKnowledgeModule"
            )

        universe = self.knowledge_module.universe

        if universe is None:
            raise ValueError(
                "knowledge module must expose Universe knowledge"
            )

        if self.selection not in universe.vintf_selections:
            raise ValueError(
                "selection must belong to the exact "
                "knowledge module"
            )

    @property
    def module_id(
        self,
    ) -> str:
        return self.knowledge_module.module_id


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfSelectionConclusion:
    """
    Canonical source-selection conclusion owned by Universe.

    This is semantic VINTF input selection, not a Build/Make representation.
    """

    source_path: str
    role: AndroidUniverseVintfSelectionRole
    applicability: AndroidUniverseRequirementApplicability

    knowledge_observations: tuple[
        AndroidUniverseVintfKnowledgeObservation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            str,
        ):
            raise TypeError(
                "source_path must be a string"
            )

        if not self.source_path.strip():
            raise ValueError(
                "source_path must not be empty"
            )

        if not isinstance(
            self.role,
            AndroidUniverseVintfSelectionRole,
        ):
            raise TypeError(
                "role must be an "
                "AndroidUniverseVintfSelectionRole"
            )

        if not isinstance(
            self.applicability,
            AndroidUniverseRequirementApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidUniverseRequirementApplicability"
            )

        if not isinstance(
            self.knowledge_observations,
            tuple,
        ):
            raise TypeError(
                "knowledge_observations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfKnowledgeObservation,
            )
            for item in self.knowledge_observations
        ):
            raise TypeError(
                "knowledge_observations must contain only "
                "AndroidUniverseVintfKnowledgeObservation instances"
            )

    @property
    def selection_id(
        self,
    ) -> str:
        return (
            "vintf-selection:"
            f"{self.role.value}:"
            f"{self.source_path}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfApplicability:
    """
    Complete VINTF applicability state known to Universe.

    ``document_applicability`` covers exact factory/Parsing VINTF documents.

    ``selection_conclusions`` covers semantic source-tree selections supplied
    by resolved knowledge modules where final installed factory state cannot
    recover the original source composition by itself.
    """

    document_applicability: tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ] = ()

    selection_conclusions: tuple[
        AndroidUniverseVintfSelectionConclusion,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.document_applicability,
            tuple,
        ):
            raise TypeError(
                "document_applicability must be a tuple"
            )

        if not isinstance(
            self.selection_conclusions,
            tuple,
        ):
            raise TypeError(
                "selection_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            for item in self.document_applicability
        ):
            raise TypeError(
                "document_applicability must contain only "
                "AndroidUniverseRequirementApplicability instances"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfSelectionConclusion,
            )
            for item in self.selection_conclusions
        ):
            raise TypeError(
                "selection_conclusions must contain only "
                "AndroidUniverseVintfSelectionConclusion instances"
            )

        document_ids = tuple(
            item.requirement_id
            for item in self.document_applicability
        )

        if document_ids != tuple(
            sorted(
                document_ids
            )
        ):
            raise ValueError(
                "document_applicability must use canonical order"
            )

        selection_ids = tuple(
            item.selection_id
            for item in self.selection_conclusions
        )

        if selection_ids != tuple(
            sorted(
                selection_ids
            )
        ):
            raise ValueError(
                "selection_conclusions must use canonical order"
            )

    @property
    def active_selections(
        self,
    ) -> tuple[
        AndroidUniverseVintfSelectionConclusion,
        ...,
    ]:
        return tuple(
            item
            for item in self.selection_conclusions
            if (
                item.applicability.status
                is AndroidUniverseApplicabilityStatus.ACTIVE
            )
        )

    @property
    def conditional_selections(
        self,
    ) -> tuple[
        AndroidUniverseVintfSelectionConclusion,
        ...,
    ]:
        return tuple(
            item
            for item in self.selection_conclusions
            if (
                item.applicability.status
                is AndroidUniverseApplicabilityStatus.CONDITIONAL
            )
        )

    @property
    def alternative_selections(
        self,
    ) -> tuple[
        AndroidUniverseVintfSelectionConclusion,
        ...,
    ]:
        return tuple(
            item
            for item in self.selection_conclusions
            if (
                item.applicability.status
                is AndroidUniverseApplicabilityStatus.ALTERNATIVE
            )
        )


class AndroidUniverseVintfApplicabilityReconciler:
    """
    Reconcile exact installed VINTF documents and knowledge selections.

    Every VINTF document physically present in a parser-ready Android VINTF
    install location is positive source-structure evidence that the document
    exists in the observed image.

    Knowledge selections describe source composition that cannot be recovered
    from the final merged/installed image alone.

    Conditional knowledge is preserved as CONDITIONAL unless a future generic
    selector input resolves it. It is never guessed active.
    """

    _ROLE_VALUES = frozenset(
        item.value
        for item in AndroidUniverseVintfSelectionRole
    )

    def reconcile(
        self,
        *,
        requirements: tuple[
            AndroidUniverseVintfDocumentRequirement,
            ...,
        ],
        knowledge_modules: tuple[
            AndroidKnowledgeModule,
            ...,
        ] = (),
    ) -> AndroidUniverseVintfApplicability:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfDocumentRequirement,
            )
            for item in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseVintfDocumentRequirement instances"
            )

        if not isinstance(
            knowledge_modules,
            tuple,
        ):
            raise TypeError(
                "knowledge_modules must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidKnowledgeModule,
            )
            for item in knowledge_modules
        ):
            raise TypeError(
                "knowledge_modules must contain only "
                "AndroidKnowledgeModule instances"
            )

        document_applicability = tuple(
            sorted(
                (
                    self._document_applicability(
                        requirement
                    )
                    for requirement
                    in requirements
                ),
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )

        observations = (
            self._knowledge_observations(
                knowledge_modules
            )
        )

        selection_conclusions = (
            self._selection_conclusions(
                observations
            )
        )

        return AndroidUniverseVintfApplicability(
            document_applicability=(
                document_applicability
            ),
            selection_conclusions=(
                selection_conclusions
            ),
        )

    def _document_applicability(
        self,
        requirement: AndroidUniverseVintfDocumentRequirement,
    ) -> AndroidUniverseRequirementApplicability:
        android_path = requirement.android_path

        evidence = ()

        if android_path is not None:
            normalized = (
                "/"
                + android_path.as_posix().lstrip("/")
            )

            evidence = (
                AndroidUniverseApplicabilityEvidence(
                    kind=(
                        AndroidUniverseApplicabilityEvidenceKind
                        .SOURCE_STRUCTURE
                    ),
                    raw_value=normalized,
                    source_path=requirement.source_path,
                    android_path=PurePosixPath(
                        normalized
                    ),
                ),
            )

        status = (
            AndroidUniverseApplicabilityStatus.ACTIVE
            if evidence
            else AndroidUniverseApplicabilityStatus.UNRESOLVED
        )

        return AndroidUniverseRequirementApplicability(
            requirement_id=requirement.requirement_id,
            status=status,
            evidence=evidence,
        )

    def _knowledge_observations(
        self,
        knowledge_modules: tuple[
            AndroidKnowledgeModule,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseVintfKnowledgeObservation,
        ...,
    ]:
        observations = []

        for module in knowledge_modules:
            universe = module.universe

            if universe is None:
                continue

            for selection in universe.vintf_selections:
                if selection.role not in self._ROLE_VALUES:
                    raise ValueError(
                        "Unsupported VINTF selection role: "
                        f"{selection.role!r}"
                    )

                observations.append(
                    AndroidUniverseVintfKnowledgeObservation(
                        selection=selection,
                        knowledge_module=module,
                    )
                )

        return tuple(
            sorted(
                observations,
                key=lambda item: (
                    item.selection.role,
                    item.selection.source_path,
                    item.module_id,
                    item.selection.selector_key or "",
                    item.selection.selector_value or "",
                ),
            )
        )

    def _selection_conclusions(
        self,
        observations: tuple[
            AndroidUniverseVintfKnowledgeObservation,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseVintfSelectionConclusion,
        ...,
    ]:
        grouped = {}

        for observation in observations:
            selection = observation.selection

            key = (
                selection.role,
                selection.source_path,
            )

            grouped.setdefault(
                key,
                [],
            ).append(
                observation
            )

        conclusions = []

        for (
            role_value,
            source_path,
        ), group in sorted(
            grouped.items()
        ):
            canonical_group = tuple(
                sorted(
                    group,
                    key=lambda item: (
                        item.module_id,
                        item.selection.selector_key or "",
                        item.selection.selector_value or "",
                        item.selection.alternative_group or "",
                    ),
                )
            )

            selectors = tuple(
                item.selection
                for item in canonical_group
                if (
                    item.selection.selector_key
                    is not None
                )
            )

            if selectors:
                status = (
                    AndroidUniverseApplicabilityStatus
                    .CONDITIONAL
                )

                selector_keys = {
                    item.selector_key
                    for item in selectors
                }

                selector_values = {
                    item.selector_value
                    for item in selectors
                }

                alternative_groups = {
                    item.alternative_group
                    for item in selectors
                    if (
                        item.alternative_group
                        is not None
                    )
                }

                selector_key = (
                    next(
                        iter(
                            selector_keys
                        )
                    )
                    if len(selector_keys) == 1
                    else None
                )

                selector_value = (
                    next(
                        iter(
                            selector_values
                        )
                    )
                    if len(selector_values) == 1
                    else None
                )

                alternative_group = (
                    next(
                        iter(
                            alternative_groups
                        )
                    )
                    if len(alternative_groups) == 1
                    else None
                )
            else:
                status = (
                    AndroidUniverseApplicabilityStatus
                    .ACTIVE
                )
                selector_key = None
                selector_value = None
                alternative_group = None

            applicability = (
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        "vintf-selection:"
                        f"{role_value}:"
                        f"{source_path}"
                    ),
                    status=status,
                    evidence=(),
                    alternative_group=(
                        alternative_group
                    ),
                    selector_key=selector_key,
                    selector_value=selector_value,
                )
            )

            conclusions.append(
                AndroidUniverseVintfSelectionConclusion(
                    source_path=source_path,
                    role=(
                        AndroidUniverseVintfSelectionRole(
                            role_value
                        )
                    ),
                    applicability=applicability,
                    knowledge_observations=(
                        canonical_group
                    ),
                )
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.selection_id
                ),
            )
        )
