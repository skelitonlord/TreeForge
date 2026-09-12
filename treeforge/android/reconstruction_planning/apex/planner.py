from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)


class AndroidReconstructionApexPlanner:
    """Classify canonical Universe APEX obligations."""

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

        if obligation.requirement_kind != "apex":
            raise ValueError(
                "AndroidReconstructionApexPlanner requires "
                "an apex obligation"
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.PRESERVED
            ),
            preserved_artifact_id=(
                obligation.source_identity
            ),
            obligation=obligation,
            reason=(
                "Canonical Universe APEX identity and artifact evidence "
                "are already preserved from the factory image; Universe "
                "does not establish Device Tree package ownership or "
                "build-module semantics requiring reconstruction."
            ),
        )
