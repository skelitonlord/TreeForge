from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.fstab import (
    AndroidUniverseFstabRequirement,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)


class AndroidReconstructionFstabPlanner:
    """
    Classify one canonical Universe Fstab obligation.

    Android Device Universe owns Fstab interpretation and applicability
    reconciliation. Reconstruction Planning consumes the exact canonical
    requirement and its exact applicability conclusion without repeating
    either analysis.

    ACTIVE requirements require downstream Reconstruction work.
    ALTERNATIVE requirements are not selected for this device configuration.
    UNRESOLVED applicability remains unresolved rather than being guessed.
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

        if obligation.requirement_kind != "fstab":
            raise ValueError(
                "AndroidReconstructionFstabPlanner requires "
                "a fstab obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseFstabRequirement,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Fstab obligation does not contain the canonical "
                    "AndroidUniverseFstabRequirement."
                ),
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "Fstab obligation source_identity must preserve "
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
                    "Canonical Universe Fstab applicability conclusion "
                    "is unavailable or non-unique."
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
                    "Canonical Universe Fstab applicability classifies "
                    "this requirement as active; downstream "
                    "Reconstruction must represent it."
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
                    "Canonical Universe Fstab applicability classifies "
                    "this requirement as an unselected alternative."
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
                    "Canonical Universe Fstab applicability remains "
                    "unresolved."
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
                "Canonical Universe Fstab applicability uses a status "
                "that Reconstruction Planning does not yet classify: "
                f"{conclusion.status.value}."
            ),
        )
