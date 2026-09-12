from __future__ import annotations

from treeforge.android.reconstruction_planning.init.source_grouping import (
    AndroidReconstructionInitSourceDisposition,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportResolution,
    AndroidUniverseInitImportResolutionStatus,
)


class AndroidReconstructionInitImportPlanner:
    """
    Classify one canonical Universe INIT Import obligation.

    Import expansion and target resolution remain owned by Android Device
    Universe. Reconstruction Planning consumes that exact conclusion without
    repeating or extending Universe interpretation.
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

        if obligation.requirement_kind != "init_import":
            raise ValueError(
                "AndroidReconstructionInitImportPlanner requires "
                "an init_import obligation"
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
                    "import is an unselected source alternative."
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
                    "The canonical INIT source containing this "
                    "import has unresolved source applicability."
                ),
                known_unresolved=True,
            )

        resolutions = tuple(
            item
            for item in obligation.universe_context
            if isinstance(
                item,
                AndroidUniverseInitImportResolution,
            )
        )

        matching_resolutions = tuple(
            resolution
            for resolution in resolutions
            if (
                resolution.requirement.requirement_id
                == obligation.source_identity
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
                    "Canonical Universe INIT Import resolution "
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
                    "Multiple canonical Universe INIT Import "
                    "resolutions describe this obligation."
                ),
            )

        resolution = matching_resolutions[0]

        if (
            resolution.status
            is AndroidUniverseInitImportResolutionStatus.RESOLVED
        ):
            reason = (
                "The containing INIT source participates in "
                "reconstruction and the literal canonical import "
                "declaration is reconstructable; Universe also "
                "resolves its target to exactly one parsed INIT "
                "source."
            )

        elif (
            resolution.status
            is AndroidUniverseInitImportResolutionStatus
            .RESOLVED_EXTERNAL_TARGET
        ):
            reason = (
                "The containing INIT source participates in "
                "reconstruction and the literal canonical import "
                "declaration is reconstructable; Universe resolves "
                "its target to the canonical external Android path "
                f"{resolution.external_target_path}."
            )

        elif (
            resolution.status
            is AndroidUniverseInitImportResolutionStatus.UNRESOLVED
        ):
            reason = (
                "The containing INIT source participates in "
                "reconstruction and the literal canonical import "
                "declaration is reconstructable exactly. Universe "
                "retains the unresolved runtime target relationship "
                "separately; Planning does not need to choose that "
                "target to preserve the declaration."
            )

        elif (
            resolution.status
            is AndroidUniverseInitImportResolutionStatus.AMBIGUOUS
        ):
            reason = (
                "The containing INIT source participates in "
                "reconstruction and the literal canonical import "
                "declaration is reconstructable exactly. Universe "
                "retains the ambiguous runtime target relationship "
                "separately; Planning does not need to choose among "
                "targets to preserve the declaration."
            )

        else:
            raise ValueError(
                "unsupported canonical Universe INIT Import "
                f"resolution status: {resolution.status!r}"
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.PLANNED
            ),
            obligation=obligation,
            reason=reason,
        )
