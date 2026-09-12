from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.ueventd.reconciliation import (
    AndroidUniverseUeventdRequirementConclusion,
    AndroidUniverseUeventdRequirementStatus,
)
from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdRequirement,
)


class AndroidReconstructionUeventdPlanner:
    """
    Classify one canonical Universe UEVENTD obligation.

    Android Device Universe owns UEVENTD interpretation, import resolution,
    source reachability, and cross-source semantic reconciliation.

    Reconstruction Planning consumes only the exact canonical requirement
    conclusion and decides whether downstream Reconstruction work is required.
    """

    @staticmethod
    def plan(
        obligation: AndroidReconstructionPlanningObligation,
    ) -> AndroidReconstructionPlanningOutcome:
        if not isinstance(
            obligation,
            AndroidReconstructionPlanningObligation,
        ):
            raise TypeError(
                "obligation must be an "
                "AndroidReconstructionPlanningObligation"
            )

        if obligation.requirement_kind != "ueventd":
            raise ValueError(
                "AndroidReconstructionUeventdPlanner requires "
                "a ueventd obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseUeventdRequirement,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "UEVENTD obligation does not contain a canonical "
                    "AndroidUniverseUeventdRequirement."
                ),
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "UEVENTD obligation source_identity must preserve "
                "the canonical Universe requirement identity"
            )

        conclusions = tuple(
            item
            for item in obligation.universe_context
            if isinstance(
                item,
                AndroidUniverseUeventdRequirementConclusion,
            )
            and (
                item.requirement_id
                == requirement.requirement_id
            )
        )

        if len(conclusions) != 1:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe UEVENTD reconciliation "
                    "conclusion is unavailable or non-unique."
                ),
            )

        conclusion = conclusions[0]

        if conclusion.requirement is not requirement:
            raise ValueError(
                "UEVENTD Planning must consume the exact canonical "
                "Universe requirement conclusion"
            )

        if (
            conclusion.status
            is AndroidUniverseUeventdRequirementStatus.ACTIVE
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .PLANNED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe UEVENTD reconciliation "
                    "classifies this requirement as active; "
                    "downstream Reconstruction must represent it."
                ),
            )

        if (
            conclusion.status
            is AndroidUniverseUeventdRequirementStatus.NOT_APPLICABLE
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe UEVENTD reconciliation "
                    "classifies this requirement as not applicable; "
                    "no downstream Reconstruction work is required."
                ),
            )

        if (
            conclusion.status
            is AndroidUniverseUeventdRequirementStatus.CONFLICTING
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .CONFLICTING
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe UEVENTD reconciliation "
                    "classifies this requirement as conflicting: "
                    f"{conclusion.reason}"
                ),
            )

        if (
            conclusion.status
            is AndroidUniverseUeventdRequirementStatus.UNRESOLVED
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe UEVENTD reconciliation "
                    "remains unresolved: "
                    f"{conclusion.reason}"
                ),
                known_unresolved=True,
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "Canonical Universe UEVENTD reconciliation uses "
                "an unsupported status."
            ),
        )
