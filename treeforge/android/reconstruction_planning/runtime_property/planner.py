from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.runtime_property import (
    AndroidUniverseRuntimePropertyRelevance,
    AndroidUniverseRuntimePropertyRelevanceStatus,
    AndroidUniverseRuntimePropertyRequirement,
)


class AndroidReconstructionRuntimePropertyPlanner:
    """
    Plan one canonical Universe runtime-property requirement.

    Planning consumes the Universe-owned reconstruction-relevance conclusion
    directly. It does not reinterpret producer, consumer, declaration,
    property-context, or cross-family evidence.
    """

    @staticmethod
    def plan(
        obligation: AndroidReconstructionPlanningObligation,
        *,
        relevance: AndroidUniverseRuntimePropertyRelevance,
    ) -> AndroidReconstructionPlanningOutcome:
        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseRuntimePropertyRequirement,
        ):
            raise TypeError(
                "runtime_property obligation must contain an "
                "AndroidUniverseRuntimePropertyRequirement"
            )

        if obligation.source_identity != requirement.property_key:
            raise ValueError(
                "runtime_property obligation source identity must match "
                "property_key"
            )

        if not isinstance(
            relevance,
            AndroidUniverseRuntimePropertyRelevance,
        ):
            raise TypeError(
                "runtime_property relevance must be an "
                "AndroidUniverseRuntimePropertyRelevance"
            )

        if relevance.requirement is not requirement:
            raise ValueError(
                "runtime_property relevance must retain the exact canonical "
                "runtime-property requirement identity"
            )

        if (
            relevance.status
            is AndroidUniverseRuntimePropertyRelevanceStatus
            .RECONSTRUCTION_REQUIRED
        ):
            disposition = (
                AndroidReconstructionPlanningDisposition.PLANNED
            )
            reason = (
                relevance.reason
                or "Canonical Universe requires runtime-property "
                "reconstruction."
            )

        elif (
            relevance.status
            is AndroidUniverseRuntimePropertyRelevanceStatus
            .COVERED_BY_OTHER_FAMILY
        ):
            disposition = (
                AndroidReconstructionPlanningDisposition.NOT_APPLICABLE
            )
            reason = (
                relevance.reason
                or "Canonical Universe assigns this reconstruction concern "
                "to another requirement family."
            )

        elif (
            relevance.status
            is AndroidUniverseRuntimePropertyRelevanceStatus
            .RUNTIME_INPUT
        ):
            disposition = (
                AndroidReconstructionPlanningDisposition.NOT_APPLICABLE
            )
            reason = (
                relevance.reason
                or "Canonical Universe establishes this property as a "
                "runtime-provided input to reconstructed consumer logic "
                "rather than an independently reconstructed property source."
            )

        elif (
            relevance.status
            is AndroidUniverseRuntimePropertyRelevanceStatus
            .NOT_APPLICABLE
        ):
            disposition = (
                AndroidReconstructionPlanningDisposition.NOT_APPLICABLE
            )
            reason = (
                relevance.reason
                or "Canonical Universe establishes that this "
                "runtime-property requirement is not applicable."
            )

        elif (
            relevance.status
            is AndroidUniverseRuntimePropertyRelevanceStatus.UNRESOLVED
        ):
            disposition = (
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            )
            reason = (
                relevance.reason
                or "Canonical Universe could not establish runtime-property "
                "reconstruction relevance."
            )

        else:
            raise ValueError(
                "unsupported canonical runtime-property relevance status: "
                f"{relevance.status!r}"
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=disposition,
            obligation=obligation,
            reason=reason,
            known_unresolved=(
                relevance.status
                is AndroidUniverseRuntimePropertyRelevanceStatus.UNRESOLVED
            ),
        )
