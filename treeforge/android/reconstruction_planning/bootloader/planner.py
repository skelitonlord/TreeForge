from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.bootloader import (
    AndroidUniverseBootloaderRequirement,
    AndroidUniverseBootloaderRequirementFamily,
)


class AndroidReconstructionBootloaderPlanner:
    """Classify canonical Universe Bootloader obligations."""

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

        if obligation.requirement_kind != "bootloader":
            raise ValueError(
                "AndroidReconstructionBootloaderPlanner requires "
                "a bootloader obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseBootloaderRequirement,
        ):
            raise TypeError(
                "bootloader obligation requirement must be an "
                "AndroidUniverseBootloaderRequirement"
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "bootloader obligation source_identity must match "
                "the canonical Universe requirement_id"
            )

        family = requirement.family

        non_android_source_families = {
            AndroidUniverseBootloaderRequirementFamily
            .FIRMWARE_PAYLOAD,
            AndroidUniverseBootloaderRequirementFamily
            .PARTITION_TABLE,
            AndroidUniverseBootloaderRequirementFamily
            .UFS_DESCRIPTOR,
            AndroidUniverseBootloaderRequirementFamily
            .FIRMWARE_PACKAGE,
            AndroidUniverseBootloaderRequirementFamily
            .FIRMWARE_PACKAGE_DESCRIPTOR,
        }

        if family in non_android_source_families:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "This canonical Bootloader "
                    f"{family.value} requirement is specific to "
                    "bootloader firmware. "
                    "It is specific to bootloader firmware evidence "
                    "and does not require a normal Android Device Tree "
                    "source component, tree target, logical destination, "
                    "or materialization strategy."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "No Reconstruction Planning classification exists "
                "for Bootloader requirement family "
                f"{family.value}. The family is not automatically "
                "treated as bootloader-specific."
            ),
        )
