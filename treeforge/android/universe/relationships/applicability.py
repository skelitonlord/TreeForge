from __future__ import annotations

from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportResolution,
    android_init_inapplicable_source_paths,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceResolution,
    AndroidUniverseInitServiceResolutionStatus,
    android_init_source_context,
)
from treeforge.android.universe.init.source_applicability import (
    AndroidUniverseInitSourceApplicability,
    AndroidUniverseInitSourceApplicabilityStatus,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityEvidence,
    AndroidUniverseApplicabilityEvidenceKind,
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseCrossFamilyRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
    AndroidUniverseInitServiceControlRelationship,
    AndroidUniverseRelationshipStatus,
)


def _relationship_source_path(
    relationship: AndroidUniverseCrossFamilyRelationship,
):
    """
    Return the canonical INIT source owning one relationship, when any.

    Cross-family relationships that originate from property evidence rather
    than INIT have no INIT-source applicability and are active by default.
    """

    init_action = getattr(
        relationship,
        "init_action",
        None,
    )

    if init_action is not None:
        return (
            init_action.source_path
        )

    init_service = getattr(
        relationship,
        "init_service",
        None,
    )

    if init_service is not None:
        return (
            init_service.source_path
        )

    return None


def _relationship_init_requirement(
    relationship: AndroidUniverseCrossFamilyRelationship,
):
    init_action = getattr(
        relationship,
        "init_action",
        None,
    )

    if init_action is not None:
        return init_action

    return getattr(
        relationship,
        "init_service",
        None,
    )


def _runtime_context_key(
    runtime_context,
):
    if runtime_context.is_root:
        return (
            "root",
            None,
        )

    partition_container = (
        runtime_context.partition_container
    )

    if partition_container is None:
        raise ValueError(
            "nested runtime context must preserve partition_container"
        )

    return (
        "nested_partition_set",
        id(
            partition_container
        ),
    )


def reconcile_android_relationship_applicability(
    *,
    relationships: tuple[
        AndroidUniverseCrossFamilyRelationship,
        ...,
    ],
    init_import_resolutions: tuple[
        AndroidUniverseInitImportResolution,
        ...,
    ],
    init_service_resolutions: tuple[
        AndroidUniverseInitServiceResolution,
        ...,
    ],
    init_source_applicability: tuple[
        AndroidUniverseInitSourceApplicability,
        ...,
    ],
) -> tuple[
    AndroidUniverseRequirementApplicability,
    ...,
]:
    """
    Classify preserved cross-family relationships independently from their
    resolution status.

    Relationships emitted by a property-selected INIT source alternative stay
    in the canonical Universe but are marked ALTERNATIVE.

    Relationships owned by a preserved INIT service declaration that has been
    superseded by context-local INIT override semantics also remain canonical
    but are marked ALTERNATIVE. Service reconciliation owns the effective
    declaration conclusion; relationship applicability only consumes it.

    Resolution and applicability deliberately remain orthogonal:
    an ALTERNATIVE relationship can still be structurally resolved,
    unresolved, or ambiguous without being treated as an actionable device
    requirement.
    """

    if not isinstance(
        relationships,
        tuple,
    ):
        raise TypeError(
            "relationships must be a tuple"
        )

    if not isinstance(
        init_import_resolutions,
        tuple,
    ):
        raise TypeError(
            "init_import_resolutions must be a tuple"
        )

    if not isinstance(
        init_service_resolutions,
        tuple,
    ):
        raise TypeError(
            "init_service_resolutions must be a tuple"
        )

    if not all(
        isinstance(
            resolution,
            AndroidUniverseInitServiceResolution,
        )
        for resolution
        in init_service_resolutions
    ):
        raise TypeError(
            "init_service_resolutions must contain only "
            "AndroidUniverseInitServiceResolution instances"
        )

    if not isinstance(
        init_source_applicability,
        tuple,
    ):
        raise TypeError(
            "init_source_applicability must be a tuple"
        )

    if not all(
        isinstance(
            item,
            AndroidUniverseInitSourceApplicability,
        )
        for item in init_source_applicability
    ):
        raise TypeError(
            "init_source_applicability must contain only "
            "AndroidUniverseInitSourceApplicability instances"
        )

    source_applicability_by_identity = {
        item.source_identity: item
        for item in init_source_applicability
    }

    if (
        len(source_applicability_by_identity)
        != len(init_source_applicability)
    ):
        raise ValueError(
            "canonical INIT source applicability identities must be unique"
        )

    inapplicable_source_paths = (
        android_init_inapplicable_source_paths(
            init_import_resolutions
        )
    )

    alternative_sources = {}

    for resolution in (
        init_import_resolutions
    ):
        for source in (
            resolution.candidate_sources
        ):
            if (
                source.source_path
                not in inapplicable_source_paths
            ):
                continue

            alternative_sources.setdefault(
                source.source_path,
                [],
            ).append(
                resolution
            )

    service_resolutions_by_context_name = {
        (
            _runtime_context_key(
                resolution.runtime_context
            ),
            resolution.source_context,
            resolution.name,
        ): resolution
        for resolution
        in init_service_resolutions
    }

    conclusions = []

    for relationship in relationships:
        source_path = (
            _relationship_source_path(
                relationship
            )
        )

        init_requirement = (
            _relationship_init_requirement(
                relationship
            )
        )

        source_applicability_conclusion = None
        relationship_runtime_key = None

        if init_requirement is not None:
            source_identity = (
                android_universe_init_source_identity(
                    source_path=(
                        init_requirement.source_path
                    ),
                    android_path=(
                        init_requirement.android_path
                    ),
                    filesystem_source=(
                        init_requirement.filesystem_source
                    ),
                )
            )

            source_applicability_conclusion = (
                source_applicability_by_identity.get(
                    source_identity
                )
            )

            if source_applicability_conclusion is None:
                raise ValueError(
                    "INIT-origin relationship has no canonical "
                    "source-applicability conclusion: "
                    f"{relationship.relationship_id}"
                )

            relationship_runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    init_requirement.filesystem_source
                )
            )

            relationship_runtime_key = (
                _runtime_context_key(
                    relationship_runtime_context
                )
            )

        selectors = tuple(
            alternative_sources.get(
                source_path,
                (),
            )
        )

        superseded_service_resolution = None

        init_service = getattr(
            relationship,
            "init_service",
            None,
        )

        if init_service is not None:
            source_context = (
                android_init_source_context(
                    init_service.source_path
                )
            )

            service_resolution = (
                service_resolutions_by_context_name.get(
                    (
                        relationship_runtime_key,
                        source_context,
                        init_service.name,
                    )
                )
            )

            if (
                service_resolution is not None
                and any(
                    declaration.requirement_id
                    == init_service.requirement_id
                    for declaration
                    in service_resolution.declarations
                )
                and all(
                    effective.requirement_id
                    != init_service.requirement_id
                    for effective
                    in service_resolution.effective_services
                )
            ):
                superseded_service_resolution = (
                    service_resolution
                )

        target_selectors = ()

        if (
            not selectors
            and relationship.status
            is AndroidUniverseRelationshipStatus.UNRESOLVED
            and isinstance(
                relationship,
                (
                    AndroidUniverseInitServiceControlRelationship,
                    AndroidUniverseInitOnRestartServiceControlRelationship,
                ),
            )
        ):
            source_context = (
                android_init_source_context(
                    source_path
                )
                if source_path is not None
                else None
            )

            lookup_target = (
                relationship.expanded_target
                or relationship.target
            )

            target_resolution = (
                service_resolutions_by_context_name.get(
                    (
                        relationship_runtime_key,
                        source_context,
                        lookup_target,
                    )
                )
                if (
                    source_context is not None
                    and relationship_runtime_key is not None
                )
                else None
            )

            if (
                target_resolution is not None
                and target_resolution.status
                is AndroidUniverseInitServiceResolutionStatus.INAPPLICABLE
                and target_resolution.declarations
            ):
                declaration_selector_sets = []

                for declaration in (
                    target_resolution.declarations
                ):
                    declaration_selectors = tuple(
                        alternative_sources.get(
                            declaration.source_path,
                            (),
                        )
                    )

                    if not declaration_selectors:
                        declaration_selector_sets = []
                        break

                    declaration_selector_sets.extend(
                        declaration_selectors
                    )

                if declaration_selector_sets:
                    target_selectors = tuple(
                        sorted(
                            {
                                selector.resolution_id: selector
                                for selector
                                in declaration_selector_sets
                            }.values(),
                            key=lambda selector: (
                                selector.resolution_id
                            ),
                        )
                    )

        applicable_selectors = (
            selectors
            or target_selectors
        )

        if applicable_selectors:
            evidence = []

            selector_pairs = []

            for resolution in applicable_selectors:
                requirement = (
                    resolution.requirement
                )

                evidence.append(
                    AndroidUniverseApplicabilityEvidence(
                        kind=(
                            AndroidUniverseApplicabilityEvidenceKind
                            .PROPERTY
                        ),
                        raw_value=(
                            requirement.declaration.raw
                        ),
                        source_path=(
                            requirement.source_path
                        ),
                        android_path=(
                            requirement.android_path
                        ),
                        line_number=(
                            requirement.declaration.location.line
                        ),
                    )
                )

                selector_pairs.extend(
                    resolution.expansion.resolved_properties
                )

            selector_pairs = tuple(
                sorted(
                    set(
                        selector_pairs
                    )
                )
            )

            if len(
                selector_pairs
            ) == 1:
                (
                    selector_key,
                    selector_value,
                ) = selector_pairs[0]
            else:
                selector_key = None
                selector_value = None

            alternative_group = (
                "init-source-selection:"
                + "|".join(
                    sorted(
                        resolution.requirement.requirement_id
                        for resolution
                        in applicable_selectors
                    )
                )
            )

            applicability = (
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        relationship.relationship_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .ALTERNATIVE
                    ),
                    evidence=tuple(
                        sorted(
                            evidence,
                            key=lambda item: (
                                (
                                    item.source_path.as_posix()
                                    if item.source_path
                                    is not None
                                    else ""
                                ),
                                item.line_number or 0,
                                item.raw_value,
                            ),
                        )
                    ),
                    alternative_group=(
                        alternative_group
                    ),
                    selector_key=(
                        selector_key
                    ),
                    selector_value=(
                        selector_value
                    ),
                )
            )

        elif (
            source_applicability_conclusion is not None
            and source_applicability_conclusion.status
            in {
                AndroidUniverseInitSourceApplicabilityStatus
                .ALTERNATIVE,
                AndroidUniverseInitSourceApplicabilityStatus
                .UNREFERENCED,
            }
        ):
            applicability = (
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        relationship.relationship_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .ALTERNATIVE
                    ),
                    evidence=(
                        AndroidUniverseApplicabilityEvidence(
                            kind=(
                                AndroidUniverseApplicabilityEvidenceKind
                                .SOURCE_STRUCTURE
                            ),
                            raw_value=(
                                "init-source-applicability:"
                                f"{source_applicability_conclusion.status.value}"
                            ),
                            source_path=source_path,
                        ),
                    ),
                    alternative_group=(
                        "init-source-applicability:"
                        + source_applicability_conclusion
                        .source_identity
                    ),
                )
            )

        elif superseded_service_resolution is not None:
            applicability = (
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        relationship.relationship_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .ALTERNATIVE
                    ),
                    evidence=(),
                    alternative_group=(
                        "init-service-resolution:"
                        + superseded_service_resolution
                        .resolution_id
                    ),
                )
            )

        else:
            applicability = (
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        relationship.relationship_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .ACTIVE
                    ),
                )
            )

        conclusions.append(
            applicability
        )

    return tuple(
        sorted(
            conclusions,
            key=lambda item: (
                item.requirement_id
            ),
        )
    )
