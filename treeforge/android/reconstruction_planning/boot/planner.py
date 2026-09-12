from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)


class AndroidReconstructionBootPlanner:
    """Classify canonical Universe Boot obligations."""

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

        if obligation.requirement_kind != "boot":
            raise ValueError(
                "AndroidReconstructionBootPlanner requires "
                "a boot obligation"
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
                "Canonical Universe boot-family semantics are preserved "
                "as device/image evidence. The boot, init_boot, and "
                "vendor_boot requirements describe resulting boot-image "
                "semantics rather than independently materializable "
                "source-tree components; later reconstruction planning "
                "may consume their preserved command-line, bootconfig, "
                "header, and provenance evidence."
            ),
        )
