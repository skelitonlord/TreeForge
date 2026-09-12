from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.dtbo.population import (
    AndroidUniverseDtboEntrySignature,
    AndroidUniverseDtboPopulationReconciliation,
    AndroidUniverseDtboVariant,
)
from treeforge.android.universe.dtbo.requirement import (
    AndroidUniverseDtboRequirement,
)


class AndroidReconstructionDtboPlanner:
    """Classify canonical Universe DTBO obligations."""

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

        if obligation.requirement_kind != "dtbo":
            raise ValueError(
                "AndroidReconstructionDtboPlanner requires "
                "a dtbo obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseDtboRequirement,
        ):
            raise TypeError(
                "dtbo obligation requirement must be an "
                "AndroidUniverseDtboRequirement"
            )

        if (
            obligation.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "dtbo obligation source_identity must match "
                "the canonical Universe requirement_id"
            )

        if len(
            obligation.universe_context
        ) != 3:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition.UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "DTBO Reconstruction requires the canonical "
                    "Universe population entry, variant, and complete "
                    "population reconciliation context."
                ),
            )

        (
            entry,
            variant,
            population,
        ) = obligation.universe_context

        if not isinstance(
            entry,
            AndroidUniverseDtboEntrySignature,
        ):
            raise TypeError(
                "DTBO Universe context entry must be an "
                "AndroidUniverseDtboEntrySignature"
            )

        if not isinstance(
            variant,
            AndroidUniverseDtboVariant,
        ):
            raise TypeError(
                "DTBO Universe context variant must be an "
                "AndroidUniverseDtboVariant"
            )

        if not isinstance(
            population,
            AndroidUniverseDtboPopulationReconciliation,
        ):
            raise TypeError(
                "DTBO Universe context population must be an "
                "AndroidUniverseDtboPopulationReconciliation"
            )

        if entry.requirement is not requirement:
            raise ValueError(
                "DTBO population entry must preserve exact "
                "Universe requirement identity"
            )

        if variant.requirement is not requirement:
            raise ValueError(
                "DTBO population variant must preserve exact "
                "Universe requirement identity"
            )

        if not any(
            population_entry is entry
            for population_entry
            in population.entries
        ):
            raise ValueError(
                "DTBO population context does not contain its "
                "canonical entry"
            )

        if not any(
            population_variant is variant
            for population_variant
            in population.variants
        ):
            raise ValueError(
                "DTBO population context does not contain its "
                "canonical variant"
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.PRESERVED
            ),
            preserved_artifact_id=requirement.requirement_id,
            obligation=obligation,
            reason=(
                "Universe provides the canonical DTBO requirement "
                "together with its exact population signature, variant "
                "profile, and complete population reconciliation. "
                "Reconstruction preserves this DTBO evidence without "
                "inventing source-tree ownership, a logical destination, "
                "vendor board-selection policy, or DTS generation "
                "semantics that Universe has not established."
            ),
        )
