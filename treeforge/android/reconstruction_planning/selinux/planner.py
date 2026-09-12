from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)


class AndroidReconstructionSelinuxPlanner:
    """
    Classify one canonical Universe SELinux obligation.

    Android Device Universe owns SELinux interpretation, reconciliation,
    policy conclusions, and source applicability.

    Reconstruction Planning consumes only the exact canonical requirement
    applicability conclusion and does not inspect SELinux policy semantics.
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

        if obligation.requirement_kind != "selinux":
            raise ValueError(
                "AndroidReconstructionSelinuxPlanner requires "
                "a selinux obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseSelinuxSourceRequirement,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "SELinux obligation does not contain the canonical "
                    "AndroidUniverseSelinuxSourceRequirement."
                ),
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "SELinux obligation source_identity must preserve "
                "the canonical Universe requirement identity"
            )

        applicability = tuple(
            item
            for item in obligation.universe_context
            if isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            and (
                item.requirement_id
                == requirement.requirement_id
            )
        )

        if len(applicability) != 1:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe SELinux applicability "
                    "conclusion is unavailable or non-unique."
                ),
            )

        conclusion = applicability[0]

        if (
            conclusion.status
            is AndroidUniverseApplicabilityStatus.ACTIVE
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .PLANNED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe SELinux applicability "
                    "classifies this source requirement as active; "
                    "downstream Reconstruction must represent it."
                ),
            )

        if (
            conclusion.status
            is AndroidUniverseApplicabilityStatus.ALTERNATIVE
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe SELinux applicability "
                    "classifies this source requirement as an "
                    "unselected alternative."
                ),
            )

        if (
            conclusion.status
            is AndroidUniverseApplicabilityStatus.UNRESOLVED
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe SELinux applicability "
                    "remains unresolved."
                ),
            )

        if (
            conclusion.status
            is AndroidUniverseApplicabilityStatus.CONDITIONAL
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe SELinux applicability remains "
                    "conditional and is not yet actionable."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "Canonical Universe SELinux applicability uses "
                "an unsupported status."
            ),
        )
