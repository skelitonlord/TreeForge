from __future__ import annotations

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.universe.avb import (
    AndroidUniverseAvbChainRelationship,
    AndroidUniverseAvbPartitionAuthentication,
    AndroidUniverseAvbTopology,
    AndroidUniverseVbmetaRequirement,
)


class AndroidReconstructionVbmetaPlanner:
    """
    Classify canonical Universe VBMeta obligations.

    Universe owns AVB descriptor interpretation and device-wide topology
    reconciliation. Reconstruction consumes those conclusions without
    reopening VBMeta images or rebuilding the trust graph.

    Canonical AVB evidence is preserved until a later Reconstruction
    capability can prove concrete Android source-tree ownership and AVB
    configuration-generation semantics.
    """

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

        if obligation.requirement_kind != "vbmeta":
            raise ValueError(
                "AndroidReconstructionVbmetaPlanner requires "
                "a vbmeta obligation"
            )

        requirement = obligation.requirement

        if not isinstance(
            requirement,
            AndroidUniverseVbmetaRequirement,
        ):
            raise TypeError(
                "vbmeta obligation requirement must be an "
                "AndroidUniverseVbmetaRequirement"
            )

        canonical_identity = (
            requirement.requirement_id
        )

        if (
            obligation.source_identity
            != canonical_identity
        ):
            raise ValueError(
                "vbmeta obligation source_identity must match "
                "the canonical Universe VBMeta requirement identity"
            )

        if len(
            obligation.universe_context
        ) != 4:
            return AndroidReconstructionPlanningOutcome(
                obligation_id=obligation.obligation_id,
                disposition=(
                    AndroidReconstructionPlanningDisposition
                    .UNRESOLVED
                ),
                obligation=obligation,
                reason=(
                    "VBMeta Reconstruction requires canonical "
                    "Universe AVB authentication relationships, "
                    "incoming and outgoing chain relationships, "
                    "and the complete AVB topology."
                ),
            )

        (
            authentications,
            outgoing_chains,
            incoming_chains,
            topology,
        ) = obligation.universe_context

        if not isinstance(
            authentications,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidUniverseAvbPartitionAuthentication,
            )
            for item in authentications
        ):
            raise TypeError(
                "VBMeta authentication context must contain only "
                "AndroidUniverseAvbPartitionAuthentication entries"
            )

        if not isinstance(
            outgoing_chains,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidUniverseAvbChainRelationship,
            )
            for item in outgoing_chains
        ):
            raise TypeError(
                "VBMeta outgoing-chain context must contain only "
                "AndroidUniverseAvbChainRelationship entries"
            )

        if not isinstance(
            incoming_chains,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidUniverseAvbChainRelationship,
            )
            for item in incoming_chains
        ):
            raise TypeError(
                "VBMeta incoming-chain context must contain only "
                "AndroidUniverseAvbChainRelationship entries"
            )

        if not isinstance(
            topology,
            AndroidUniverseAvbTopology,
        ):
            raise TypeError(
                "VBMeta topology context must be an "
                "AndroidUniverseAvbTopology"
            )

        if not any(
            topology_requirement is requirement
            for topology_requirement
            in topology.requirements
        ):
            raise ValueError(
                "VBMeta topology context must preserve exact "
                "Universe requirement identity"
            )

        if not all(
            authentication.owner is requirement
            for authentication
            in authentications
        ):
            raise ValueError(
                "VBMeta authentication context contains a "
                "relationship owned by another requirement"
            )

        if not all(
            chain.owner is requirement
            for chain in outgoing_chains
        ):
            raise ValueError(
                "VBMeta outgoing-chain context contains a "
                "relationship owned by another requirement"
            )

        if not all(
            chain.target is requirement
            for chain in incoming_chains
        ):
            raise ValueError(
                "VBMeta incoming-chain context contains a "
                "relationship targeting another requirement"
            )

        expected_authentications = tuple(
            authentication
            for authentication
            in topology.authentications
            if authentication.owner is requirement
        )

        expected_outgoing_chains = tuple(
            chain
            for chain in topology.chains
            if chain.owner is requirement
        )

        expected_incoming_chains = tuple(
            chain
            for chain in topology.chains
            if chain.target is requirement
        )

        if (
            authentications
            != expected_authentications
        ):
            raise ValueError(
                "VBMeta authentication context must preserve the "
                "complete canonical topology subset"
            )

        if (
            outgoing_chains
            != expected_outgoing_chains
        ):
            raise ValueError(
                "VBMeta outgoing-chain context must preserve the "
                "complete canonical topology subset"
            )

        if (
            incoming_chains
            != expected_incoming_chains
        ):
            raise ValueError(
                "VBMeta incoming-chain context must preserve the "
                "complete canonical topology subset"
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition
                .PRESERVED
            ),
            preserved_artifact_id=(
                obligation.source_identity
            ),
            obligation=obligation,
            reason=(
                (
                    "Universe provides this canonical partition-backed "
                    "VBMeta requirement "
                )
                if requirement.is_partition_backed
                else (
                    "Universe provides this canonical embedded VBMeta "
                    "requirement and its exact containing-artifact lineage "
                )
            )
            + (
                "together with its exact AVB authentication and "
                "chain relationships and the reconciled device-wide "
                "AVB topology. Reconstruction preserves that evidence "
                "without inventing signing-key policy, BoardConfig AVB "
                "directives, source-tree ownership, logical destinations, "
                "a standalone partition identity for embedded VBMeta, "
                "or AVB generation semantics that Universe has not "
                "established."
            ),
        )
