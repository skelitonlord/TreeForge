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


class AndroidReconstructionVintfPlanner:
    """
    Classify one canonical Universe VINTF obligation.

    Android Device Universe owns VINTF interpretation and applicability.
    Reconstruction Planning consumes the exact canonical requirement and its
    exact applicability conclusion without repeating either analysis.

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

        if obligation.requirement_kind != "vintf":
            raise ValueError(
                "AndroidReconstructionVintfPlanner requires "
                "a vintf obligation"
            )

        requirement = obligation.requirement

        requirement_id = getattr(
            requirement,
            "requirement_id",
            None,
        )

        if (
            not isinstance(requirement_id, str)
            or not requirement_id
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition.UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "VINTF obligation does not contain a canonical "
                    "Universe requirement identity."
                ),
            )

        if obligation.source_identity != requirement_id:
            raise ValueError(
                "VINTF obligation source_identity must preserve "
                "the canonical Universe requirement identity"
            )

        applicability = tuple(
            item
            for item in obligation.universe_context
            if isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            and item.requirement_id == requirement_id
        )

        if len(applicability) != 1:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition.UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe VINTF applicability conclusion "
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
                    AndroidReconstructionPlanningDisposition.PLANNED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe VINTF applicability classifies "
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
                    AndroidReconstructionPlanningDisposition.NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe VINTF applicability classifies "
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
                    AndroidReconstructionPlanningDisposition.UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe VINTF applicability remains "
                    "unresolved."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "Canonical Universe VINTF applicability uses a status "
                "that Reconstruction Planning does not yet classify: "
                f"{conclusion.status.value}."
            ),
        )
