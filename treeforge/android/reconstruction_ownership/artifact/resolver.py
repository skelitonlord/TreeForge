from __future__ import annotations

from treeforge.android.reconstruction_ownership.model import (
    AndroidReconstructionOwnershipDecision,
    AndroidReconstructionOwnershipDomain,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactRequirement,
)


class AndroidReconstructionArtifactOwnershipResolver:
    """
    Resolve source-tree ownership for exact preserved filesystem artifacts.

    A canonical PRESERVE disposition means downstream Reconstruction must
    retain the exact runtime artifact rather than synthesize equivalent
    source. Its source-tree representation is therefore an exact prebuilt
    artifact, owned by the PROPRIETARY source-tree domain.

    This rule does not use installed partition as a source-tree ownership
    heuristic and does not assert anything about legal provenance.
    """

    @staticmethod
    def resolve(
        requirement: AndroidUniverseArtifactRequirement,
    ) -> AndroidReconstructionOwnershipDecision:
        if not isinstance(
            requirement,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseArtifactRequirement"
            )

        if (
            requirement.disposition
            is not AndroidUniverseArtifactDisposition
            .PRESERVE
        ):
            raise ValueError(
                "Artifact Ownership resolver requires "
                "a canonical PRESERVE requirement"
            )

        return AndroidReconstructionOwnershipDecision(
            requirement_kind="artifact",
            source_identity=(
                requirement.requirement_id
            ),
            domain=(
                AndroidReconstructionOwnershipDomain
                .PROPRIETARY
            ),
            requirement=requirement,
            reason=(
                "Canonical Universe classifies this regular "
                "filesystem artifact for exact preservation. "
                "Its downstream source representation is therefore "
                "an exact prebuilt artifact owned by the proprietary "
                "source-tree domain; installed partition is retained "
                "only as runtime destination evidence."
            ),
            evidence=(
                requirement,
                requirement.inventory_entry,
                requirement.metadata_entry,
            ),
        )
