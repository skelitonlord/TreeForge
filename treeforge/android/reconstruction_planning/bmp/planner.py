from __future__ import annotations

from treeforge.android.universe.bmp import (
    AndroidUniverseBmpRequirement,
)
from treeforge.android.universe.boot_firmware_lineage import (
    AndroidUniverseBootFirmwareLineageStatus,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)


class AndroidReconstructionBmpPlanner:
    """Classify canonical Universe BMP obligations."""

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

        if obligation.requirement_kind != "bmp":
            raise ValueError(
                "AndroidReconstructionBmpPlanner requires "
                "a bmp obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseBmpRequirement,
        ):
            raise TypeError(
                "bmp obligation requirement must be an "
                "AndroidUniverseBmpRequirement"
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "bmp obligation source_identity must match "
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
                    + " It does not participate in normal "
                    "Android Device Tree source reconstruction."
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
