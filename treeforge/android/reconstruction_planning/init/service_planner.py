from __future__ import annotations

from treeforge.android.reconstruction_planning.init.source_grouping import (
    AndroidReconstructionInitSourceDisposition,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceResolution,
    AndroidUniverseInitServiceResolutionStatus,
)


class AndroidReconstructionInitServicePlanner:
    """
    Classify one canonical Universe INIT Service obligation.

    Effective-service reconciliation remains owned by Android Device Universe.
    Reconstruction Planning consumes the exact Universe conclusion and does
    not repeat override, source-selection, or context reconciliation.
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

        if obligation.requirement_kind != "init_service":
            raise ValueError(
                "AndroidReconstructionInitServicePlanner requires "
                "an init_service obligation"
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
                    "service is an unselected source alternative."
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

        requirement = obligation.requirement

        resolutions = tuple(
            item
            for item in obligation.universe_context
            if isinstance(
                item,
                AndroidUniverseInitServiceResolution,
            )
        )

        matching_resolutions = tuple(
            resolution
            for resolution in resolutions
            if any(
                declaration is requirement
                for declaration
                in resolution.declarations
            )
        )

        if not matching_resolutions:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe INIT Service resolution "
                    "is unavailable."
                ),
            )

        if len(matching_resolutions) != 1:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .CONFLICTING
                ),
                obligation=obligation,
                reason=(
                    "Multiple canonical Universe INIT Service "
                    "resolutions describe this declaration."
                ),
            )

        resolution = matching_resolutions[0]

        is_effective = any(
            effective is requirement
            for effective
            in resolution.effective_services
        )

        if not is_effective:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe INIT Service reconciliation "
                    "does not retain this declaration as an "
                    "effective service."
                ),
            )

        if (
            source_disposition is None
            or source_disposition
            is AndroidReconstructionInitSourceDisposition.UNRESOLVED
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "This declaration remains effective, but its "
                    "canonical INIT source has unresolved source "
                    "applicability."
                ),
            )

        if (
            resolution.status
            is AndroidUniverseInitServiceResolutionStatus.RESOLVED
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .PLANNED
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe INIT Service reconciliation "
                    "selects this declaration as the unique effective "
                    "service in a required INIT source."
                ),
            )

        if (
            resolution.status
            is AndroidUniverseInitServiceResolutionStatus.AMBIGUOUS
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .CONFLICTING
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe INIT Service reconciliation "
                    "retains multiple effective declarations for "
                    "this service in the same source context."
                ),
            )

        if (
            resolution.status
            is AndroidUniverseInitServiceResolutionStatus.INAPPLICABLE
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Canonical Universe INIT Service reconciliation "
                    "classifies this service as inapplicable."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "Canonical Universe INIT Service resolution has "
                "an unsupported status."
            ),
        )
