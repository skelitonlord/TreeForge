from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactRequirement,
)
from treeforge.android.reconstruction_ownership.model import (
    AndroidReconstructionOwnershipDecision,
    AndroidReconstructionOwnershipDomain,
)


class AndroidReconstructionArtifactPlanner:
    """Plan Artifact-family obligations from canonical Universe facts."""

    @staticmethod
    def plan(
        obligation: AndroidReconstructionPlanningObligation,
        *,
        ownership: (
            AndroidReconstructionOwnershipDecision
            | None
        ) = None,
    ) -> AndroidReconstructionPlanningOutcome:
        if obligation.requirement_kind != "artifact":
            raise ValueError(
                "Artifact planner received non-artifact obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseArtifactRequirement,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition.UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "Artifact obligation does not contain the "
                    "canonical AndroidUniverseArtifactRequirement."
                ),
                known_unresolved=True,
            )

        disposition = requirement.disposition

        if disposition is AndroidUniverseArtifactDisposition.PRESERVE:
            if ownership is None:
                return AndroidReconstructionPlanningOutcome(
                    obligation_id=obligation.obligation_id,
                    disposition=(
                        AndroidReconstructionPlanningDisposition
                        .UNRESOLVED
                    ),
                    obligation=obligation,
                    reason=(
                        "Canonical preserved artifact requires a "
                        "first-class Reconstruction Ownership decision "
                        "before Planning may preserve it."
                    ),
                )

            if not isinstance(
                ownership,
                AndroidReconstructionOwnershipDecision,
            ):
                raise TypeError(
                    "artifact ownership must be an "
                    "AndroidReconstructionOwnershipDecision or None"
                )

            if ownership.requirement_kind != "artifact":
                raise ValueError(
                    "artifact ownership decision must describe "
                    "an artifact requirement"
                )

            if (
                ownership.source_identity
                != requirement.requirement_id
            ):
                raise ValueError(
                    "artifact ownership decision must preserve "
                    "the exact Universe requirement identity"
                )

            if ownership.requirement is not requirement:
                raise ValueError(
                    "artifact ownership decision must retain "
                    "the exact Universe requirement object"
                )

            if (
                ownership.domain
                is AndroidReconstructionOwnershipDomain
                .UNRESOLVED
            ):
                return AndroidReconstructionPlanningOutcome(
                    obligation_id=obligation.obligation_id,
                    disposition=(
                        AndroidReconstructionPlanningDisposition
                        .UNRESOLVED
                    ),
                    obligation=obligation,
                    reason=(
                        "Reconstruction Ownership could not establish "
                        "a source-tree ownership domain for this "
                        "canonical preserved artifact."
                    ),
                )

            if (
                ownership.domain
                is not AndroidReconstructionOwnershipDomain
                .PROPRIETARY
            ):
                return AndroidReconstructionPlanningOutcome(
                    obligation_id=obligation.obligation_id,
                    disposition=(
                        AndroidReconstructionPlanningDisposition
                        .CONFLICTING
                    ),
                    obligation=obligation,
                    reason=(
                        "Canonical preserved artifact has a "
                        "non-prebuilt Ownership domain that conflicts "
                        "with exact artifact preservation."
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
                    "Universe classified this artifact as a canonical "
                    "preservation obligation."
                ),
            )

        if disposition in (
            AndroidUniverseArtifactDisposition.SEMANTIC_SOURCE,
            AndroidUniverseArtifactDisposition.INVENTORY_ONLY,
            AndroidUniverseArtifactDisposition.IGNORE,
        ):
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .NOT_APPLICABLE
                ),
                obligation=obligation,
                reason=(
                    "Universe classified this artifact as "
                    f"{disposition.value}; reconstruction handling "
                    "remains outside generic artifact preservation."
                ),
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "Universe artifact disposition is "
                f"{disposition.value}; no generic Reconstruction "
                "Planning rule exists yet."
            ),
            known_unresolved=True,
        )
