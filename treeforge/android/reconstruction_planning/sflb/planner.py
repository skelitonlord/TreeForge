from __future__ import annotations

from treeforge.android.universe.boot_firmware_lineage import (
    AndroidUniverseBootFirmwareLineageStatus,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.sflb import (
    AndroidUniverseSflbRequirement,
)


class AndroidReconstructionSflbPlanner:
    """Classify canonical Universe SFLB obligations."""

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

        if obligation.requirement_kind != "sflb":
            raise ValueError(
                "AndroidReconstructionSflbPlanner requires "
                "an sflb obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseSflbRequirement,
        ):
            raise TypeError(
                "sflb obligation requirement must be an "
                "AndroidUniverseSflbRequirement"
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "sflb obligation source_identity must match "
                "the canonical Universe requirement_id"
            )

        conclusion = (
            requirement.boot_firmware_lineage
        )

        if (
            conclusion.status
            is AndroidUniverseBootFirmwareLineageStatus
            .BOOT_FIRMWARE_DESCENDANT
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    conclusion.reason
                    + " It is therefore outside normal "
                    "Android source reconstruction."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=conclusion.reason,
            known_unresolved=True,
        )
