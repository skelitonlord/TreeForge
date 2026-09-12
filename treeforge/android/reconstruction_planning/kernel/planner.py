from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.kernel import (
    AndroidUniverseKernelRequirement,
)


class AndroidReconstructionKernelPlanner:
    """Classify canonical Universe Kernel obligations."""

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

        if obligation.requirement_kind != "kernel":
            raise ValueError(
                "AndroidReconstructionKernelPlanner requires "
                "a kernel obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseKernelRequirement,
        ):
            raise TypeError(
                "kernel obligation requirement must be an "
                "AndroidUniverseKernelRequirement"
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "kernel obligation source_identity must preserve "
                "the canonical Universe kernel requirement identity"
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
                "Canonical Universe kernel-image semantics are preserved "
                "as device evidence. The recovered Linux banner, kernel "
                "release, embedded configuration requirements, unparsed "
                "configuration evidence, Extraction lineage, and Parsing "
                "identity describe the shipped kernel but do not establish "
                "kernel source-tree ownership, a build target, defconfig "
                "ownership, BoardConfig directives, or kernel-generation "
                "semantics. Reconstruction therefore preserves the exact "
                "Universe requirement without inventing source policy."
            ),
        )
