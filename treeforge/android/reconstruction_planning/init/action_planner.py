from __future__ import annotations

from treeforge.android.reconstruction_planning.init.source_grouping import (
    AndroidReconstructionInitSourceDisposition,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)


class AndroidReconstructionInitActionPlanner:
    """
    Plan one canonical Universe INIT Action obligation.

    Action syntax and command semantics remain owned by Android Device
    Universe. Source applicability is consumed from the canonical INIT source
    grouping already established by Reconstruction Planning.

    This planner does not repeat import resolution, infer source-tree
    ownership, choose a destination, or synthesize INIT source content.
    """

    @staticmethod
    def plan(
        obligation: AndroidReconstructionPlanningObligation,
        *,
        source_disposition: (
            AndroidReconstructionInitSourceDisposition
            | None
        ) = None,
    ) -> AndroidReconstructionPlanningOutcome:
        if not isinstance(
            obligation,
            AndroidReconstructionPlanningObligation,
        ):
            raise TypeError(
                "obligation must be an "
                "AndroidReconstructionPlanningObligation"
            )

        if obligation.requirement_kind != "init_action":
            raise ValueError(
                "AndroidReconstructionInitActionPlanner requires "
                "an init_action obligation"
            )

        if (
            source_disposition is not None
            and not isinstance(
                source_disposition,
                AndroidReconstructionInitSourceDisposition,
            )
        ):
            raise TypeError(
                "source_disposition must be an "
                "AndroidReconstructionInitSourceDisposition or None"
            )

        if source_disposition is None:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical INIT source-group disposition "
                    "is unavailable for this action."
                ),
            )

        if source_disposition in (
            AndroidReconstructionInitSourceDisposition.REQUIRED,
            AndroidReconstructionInitSourceDisposition.RUNTIME_SELECTABLE,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .PLANNED
                ),
                obligation=obligation,
                reason=(
                    "The canonical INIT source containing this action "
                    "must participate in reconstruction because Universe "
                    "classifies it as required or as a concrete candidate "
                    "of an unresolved runtime selector."
                ),
            )

        if (
            source_disposition
            is AndroidReconstructionInitSourceDisposition.ALTERNATIVE
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "The canonical INIT source containing this "
                    "action is an unselected source alternative."
                ),
            )

        if (
            source_disposition
            is AndroidReconstructionInitSourceDisposition.UNREFERENCED
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe INIT source applicability "
                    "establishes that the containing source has no "
                    "canonical load path in the observed INIT graph."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "The canonical INIT source containing this action "
                "has unresolved source applicability."
            ),
            known_unresolved=True,
        )
