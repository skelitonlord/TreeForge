from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)


class AndroidReconstructionElfPlanner:
    """Plan ELF-family obligations from canonical Universe facts."""

    @staticmethod
    def plan(
        obligation: AndroidReconstructionPlanningObligation,
    ) -> AndroidReconstructionPlanningOutcome:
        if obligation.requirement_kind != "elf":
            raise ValueError(
                "ELF planner received non-ELF obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseElfRequirement,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition.UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "ELF obligation does not contain the canonical "
                    "AndroidUniverseElfRequirement."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.PRESERVED
            ),
            preserved_artifact_id=requirement.requirement_id,
            obligation=obligation,
            reason=(
                "Universe provides a canonical ELF source requirement; "
                "the exact ELF source is preserved while ELF-specific "
                "reconstruction semantics remain attached to the "
                "canonical requirement."
            ),
        )
