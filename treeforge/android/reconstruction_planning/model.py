from __future__ import annotations

from treeforge.android.universe.fstab.source_context import (
    AndroidUniverseFstabSourceContext,
)
from treeforge.android.universe.ueventd.source_context import (
    AndroidUniverseUeventdSourceContext,
)
from treeforge.android.reconstruction_ownership.model import (
    AndroidReconstructionOwnershipResult,
)

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

class AndroidReconstructionPlanningRequirementLike(Protocol):
    """Structural contract for a canonical Universe requirement."""

    pass


class AndroidReconstructionPlanningDisposition(StrEnum):
    """
    Canonical disposition of one Reconstruction Planning obligation.

    PLANNED means Reconstruction Planning has established that downstream
    Reconstruction work is required. It does not imply that Planning has
    chosen a source-tree target, destination, representation, or
    materialization strategy.
    """

    PLANNED = "planned"
    PRESERVED = "preserved"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionPlanningObligation:
    """
    Planning representation of one exact Universe requirement.

    ``universe_context`` preserves canonical Universe-owned side products
    associated with the requirement. Reconstruction Planning does not
    reinterpret or recreate this context; it only carries exact Universe
    objects forward for family planners that require reconciliation or
    population-level conclusions.
    """

    obligation_id: str
    requirement: AndroidReconstructionPlanningRequirementLike
    requirement_kind: str
    source_identity: str
    universe_context: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.obligation_id, str):
            raise TypeError("obligation_id must be a string")

        if not self.obligation_id:
            raise ValueError(
                "obligation_id must not be empty"
            )

        if not isinstance(self.requirement_kind, str):
            raise TypeError(
                "requirement_kind must be a string"
            )

        if not self.requirement_kind:
            raise ValueError(
                "requirement_kind must not be empty"
            )

        if not isinstance(self.source_identity, str):
            raise TypeError(
                "source_identity must be a string"
            )

        if not self.source_identity:
            raise ValueError(
                "source_identity must not be empty"
            )

        if not isinstance(
            self.universe_context,
            tuple,
        ):
            raise TypeError(
                "universe_context must be a tuple"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionPlanningOutcome:
    """
    Canonical Planning disposition of one exact Universe obligation.

    A PLANNED outcome establishes that Reconstruction work is required.
    Planning does not need to synthesize a source representation or component
    in order to make that decision.

    PRESERVED retains the exact canonical artifact/evidence identity that
    downstream Reconstruction may consume without Planning reinterpreting it.
    """

    obligation_id: str
    disposition: AndroidReconstructionPlanningDisposition

    obligation: AndroidReconstructionPlanningObligation | None = None

    preserved_artifact_id: str | None = None
    reason: str | None = None
    known_unresolved: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.obligation_id,
            str,
        ):
            raise TypeError(
                "obligation_id must be a string"
            )

        if not self.obligation_id:
            raise ValueError(
                "obligation_id must not be empty"
            )

        if self.obligation is not None:
            if not isinstance(
                self.obligation,
                AndroidReconstructionPlanningObligation,
            ):
                raise TypeError(
                    "obligation must be an "
                    "AndroidReconstructionPlanningObligation or None"
                )

            if (
                self.obligation.obligation_id
                != self.obligation_id
            ):
                raise ValueError(
                    "obligation_id must match outcome obligation_id"
                )

        if not isinstance(
            self.disposition,
            AndroidReconstructionPlanningDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidReconstructionPlanningDisposition"
            )

        if (
            self.preserved_artifact_id is not None
            and (
                not isinstance(
                    self.preserved_artifact_id,
                    str,
                )
                or not self.preserved_artifact_id
            )
        ):
            raise TypeError(
                "preserved_artifact_id must be a "
                "non-empty string or None"
            )

        if (
            self.disposition
            is AndroidReconstructionPlanningDisposition.PRESERVED
            and self.preserved_artifact_id is None
        ):
            raise ValueError(
                "PRESERVED outcome requires preserved_artifact_id"
            )

        if (
            self.disposition
            is not AndroidReconstructionPlanningDisposition.PRESERVED
            and self.preserved_artifact_id is not None
        ):
            raise ValueError(
                "only PRESERVED outcomes may reference "
                "preserved_artifact_id"
            )

        if not isinstance(
            self.known_unresolved,
            bool,
        ):
            raise TypeError(
                "known_unresolved must be a bool"
            )

        if (
            self.known_unresolved
            and self.disposition
            is not AndroidReconstructionPlanningDisposition.UNRESOLVED
        ):
            raise ValueError(
                "known_unresolved may only be set for "
                "UNRESOLVED outcomes"
            )

        if self.disposition in (
            AndroidReconstructionPlanningDisposition.UNRESOLVED,
            AndroidReconstructionPlanningDisposition.CONFLICTING,
        ) and not self.reason:
            raise ValueError(
                f"{self.disposition.value} outcome requires a reason"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionPlanningCoverage:
    """Coverage accounting for canonical Reconstruction Planning obligations."""

    required: int
    planned: int
    preserved: int
    not_applicable: int
    unresolved: int
    conflicting: int

    @property
    def dispositioned(self) -> int:
        return (
            self.planned
            + self.preserved
            + self.not_applicable
            + self.unresolved
            + self.conflicting
        )

    @property
    def complete(self) -> bool:
        return (
            self.required == self.dispositioned
            and self.unresolved == 0
            and self.conflicting == 0
        )

    def __post_init__(self) -> None:
        values = (
            self.required,
            self.planned,
            self.preserved,
            self.not_applicable,
            self.unresolved,
            self.conflicting,
        )

        if not all(
            isinstance(value, int)
            and value >= 0
            for value in values
        ):
            raise ValueError(
                "coverage counts must be non-negative integers"
            )

        if self.dispositioned > self.required:
            raise ValueError(
                "coverage dispositions exceed required count"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionPlanningCompleteness:
    """Canonical completeness assessment for a reconstruction plan."""

    coverage: AndroidReconstructionPlanningCoverage
    blocking_unresolved_count: int
    blocking_conflict_count: int

    @property
    def complete(self) -> bool:
        return (
            self.coverage.complete
            and self.blocking_unresolved_count == 0
            and self.blocking_conflict_count == 0
        )

    def __post_init__(self) -> None:
        if not isinstance(
            self.coverage,
            AndroidReconstructionPlanningCoverage,
        ):
            raise TypeError(
                "coverage must be an "
                "AndroidReconstructionPlanningCoverage"
            )

        for field_name, value in (
            (
                "blocking_unresolved_count",
                self.blocking_unresolved_count,
            ),
            (
                "blocking_conflict_count",
                self.blocking_conflict_count,
            ),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionPlan:
    """Complete canonical Reconstruction Planning result."""

    ownership: AndroidReconstructionOwnershipResult | None

    obligations: tuple[
        AndroidReconstructionPlanningObligation,
        ...
    ]

    init_source_groups: tuple

    outcomes: tuple[
        AndroidReconstructionPlanningOutcome,
        ...
    ]

    # Exact canonical Universe relationship products required by downstream
    # Reconstruction composition. Planning does not reinterpret these values.
    cross_family_relationships: tuple[object, ...]

    cross_family_relationship_applicability: tuple[object, ...]

    # Exact canonical Universe fstab source-level lexical context.
    # Planning does not interpret, classify, or modify these objects.
    fstab_source_contexts: tuple[
        AndroidUniverseFstabSourceContext,
        ...,
    ]

    # Exact canonical Universe UEVENTD source-level lexical context.
    # Planning does not interpret, classify, or modify these objects.
    ueventd_source_contexts: tuple[
        AndroidUniverseUeventdSourceContext,
        ...,
    ]

    completeness: AndroidReconstructionPlanningCompleteness | None = None

    def __post_init__(self) -> None:
        if (
            self.ownership is not None
            and not isinstance(
                self.ownership,
                AndroidReconstructionOwnershipResult,
            )
        ):
            raise TypeError(
                "ownership must be an "
                "AndroidReconstructionOwnershipResult or None"
            )

        for field_name, value, expected_type in (
            (
                "obligations",
                self.obligations,
                AndroidReconstructionPlanningObligation,
            ),
            (
                "outcomes",
                self.outcomes,
                AndroidReconstructionPlanningOutcome,
            ),
        ):
            if not isinstance(value, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(item, expected_type)
                for item in value
            ):
                raise TypeError(
                    f"{field_name} contains an invalid model"
                )

        if not isinstance(
            self.fstab_source_contexts,
            tuple,
        ):
            raise TypeError(
                "fstab_source_contexts must be a tuple"
            )

        if not all(
            isinstance(
                context,
                AndroidUniverseFstabSourceContext,
            )
            for context in self.fstab_source_contexts
        ):
            raise TypeError(
                "fstab_source_contexts must preserve only "
                "AndroidUniverseFstabSourceContext objects"
            )

        fstab_source_context_ids = tuple(
            context.source_identity
            for context in self.fstab_source_contexts
        )

        if len(
            fstab_source_context_ids
        ) != len(
            set(fstab_source_context_ids)
        ):
            raise ValueError(
                "fstab_source_contexts must preserve unique "
                "canonical source identities"
            )

        if not isinstance(
            self.ueventd_source_contexts,
            tuple,
        ):
            raise TypeError(
                "ueventd_source_contexts must be a tuple"
            )

        if not all(
            isinstance(
                context,
                AndroidUniverseUeventdSourceContext,
            )
            for context in self.ueventd_source_contexts
        ):
            raise TypeError(
                "ueventd_source_contexts must preserve only "
                "AndroidUniverseUeventdSourceContext objects"
            )

        ueventd_source_context_ids = tuple(
            context.source_identity
            for context in self.ueventd_source_contexts
        )

        if len(
            ueventd_source_context_ids
        ) != len(
            set(
                ueventd_source_context_ids
            )
        ):
            raise ValueError(
                "ueventd_source_contexts must preserve unique "
                "canonical source identities"
            )

        #
        # Validate the complete filesystem-source context handoff here,
        # before Reconstruction begins.
        #
        # Android-visible paths are not globally unique across canonical
        # filesystem roots. Fstab and UEVENTD therefore use the exact
        # Universe-owned tuple:
        #
        #     (source_name, path_identity)
        #
        # Planning carries those contexts verbatim and must prove every
        # requirement in either family resolves to exactly that identity.
        #
        source_context_by_kind = {
            "fstab": {
                context.source_identity: context
                for context
                in self.fstab_source_contexts
            },
            "ueventd": {
                context.source_identity: context
                for context
                in self.ueventd_source_contexts
            },
        }

        for obligation in self.obligations:
            if obligation.requirement_kind not in (
                "fstab",
                "ueventd",
            ):
                continue

            requirement = (
                obligation.requirement
            )

            source_name = getattr(
                requirement,
                "source_name",
                None,
            )

            source_path = getattr(
                requirement,
                "source_path",
                None,
            )

            android_path = getattr(
                requirement,
                "android_path",
                None,
            )

            if (
                not isinstance(
                    source_name,
                    str,
                )
                or not source_name
            ):
                raise ValueError(
                    "canonical Universe filesystem-source "
                    "requirement must expose source_name: "
                    f"{obligation.obligation_id}"
                )

            if source_path is None:
                raise ValueError(
                    "canonical Universe filesystem-source "
                    "requirement must expose source_path: "
                    f"{obligation.obligation_id}"
                )

            path_identity = (
                android_path.as_posix()
                if android_path is not None
                else source_path.as_posix()
            )

            canonical_source_identity = (
                source_name,
                path_identity,
            )

            source_context = (
                source_context_by_kind[
                    obligation.requirement_kind
                ].get(
                    canonical_source_identity
                )
            )

            if source_context is None:
                raise ValueError(
                    "canonical Universe source context is missing "
                    "at the Planning -> Reconstruction boundary: "
                    f"kind={obligation.requirement_kind}, "
                    f"identity={canonical_source_identity!r}, "
                    f"obligation={obligation.obligation_id}"
                )

            if (
                source_context.source_path
                != source_path
            ):
                raise ValueError(
                    "canonical Universe source context does not "
                    "preserve requirement source_path: "
                    f"{obligation.obligation_id}"
                )

            if (
                source_context.android_path
                != android_path
            ):
                raise ValueError(
                    "canonical Universe source context does not "
                    "preserve requirement android_path: "
                    f"{obligation.obligation_id}"
                )

            if (
                source_context.source_identity
                != canonical_source_identity
            ):
                raise ValueError(
                    "canonical Universe source-context identity "
                    "drifted across Planning: "
                    f"{obligation.obligation_id}"
                )

        if not isinstance(
            self.cross_family_relationships,
            tuple,
        ):
            raise TypeError(
                "cross_family_relationships must be a tuple"
            )

        if not isinstance(
            self.cross_family_relationship_applicability,
            tuple,
        ):
            raise TypeError(
                "cross_family_relationship_applicability "
                "must be a tuple"
            )

        relationship_ids = tuple(
            getattr(
                relationship,
                "relationship_id",
                None,
            )
            for relationship
            in self.cross_family_relationships
        )

        if not all(
            isinstance(
                relationship_id,
                str,
            )
            and relationship_id
            for relationship_id
            in relationship_ids
        ):
            raise ValueError(
                "cross_family_relationships must preserve canonical "
                "relationships with non-empty relationship_id values"
            )

        if len(
            relationship_ids
        ) != len(
            set(
                relationship_ids
            )
        ):
            raise ValueError(
                "cross_family_relationships must contain unique "
                "relationship identities"
            )

        applicability_ids = tuple(
            getattr(
                applicability,
                "requirement_id",
                None,
            )
            for applicability
            in self.cross_family_relationship_applicability
        )

        if not all(
            isinstance(
                applicability_id,
                str,
            )
            and applicability_id
            for applicability_id
            in applicability_ids
        ):
            raise ValueError(
                "cross_family_relationship_applicability must preserve "
                "canonical applicability entries with non-empty "
                "requirement_id values"
            )

        if len(
            applicability_ids
        ) != len(
            set(
                applicability_ids
            )
        ):
            raise ValueError(
                "cross_family_relationship_applicability must contain "
                "unique relationship identities"
            )

        if (
            set(applicability_ids)
            != set(relationship_ids)
        ):
            missing = sorted(
                set(relationship_ids)
                - set(applicability_ids)
            )

            unexpected = sorted(
                set(applicability_ids)
                - set(relationship_ids)
            )

            raise ValueError(
                "cross-family relationship applicability must cover "
                "the canonical relationship population exactly: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        obligation_ids = tuple(
            obligation.obligation_id
            for obligation in self.obligations
        )

        if len(obligation_ids) != len(set(obligation_ids)):
            raise ValueError(
                "obligations must have unique obligation_id values"
            )

        outcome_obligation_ids = tuple(
            outcome.obligation_id
            for outcome in self.outcomes
        )

        if len(
            outcome_obligation_ids
        ) != len(
            set(
                outcome_obligation_ids
            )
        ):
            raise ValueError(
                "outcomes must have unique obligation_id values"
            )

        if self.completeness is not None and not isinstance(
            self.completeness,
            AndroidReconstructionPlanningCompleteness,
        ):
            raise TypeError(
                "completeness must be an "
                "AndroidReconstructionPlanningCompleteness or None"
            )

    @property
    def outcome_by_obligation_id(
        self,
    ) -> dict[str, AndroidReconstructionPlanningOutcome]:
        return {
            outcome.obligation_id: outcome
            for outcome in self.outcomes
        }
