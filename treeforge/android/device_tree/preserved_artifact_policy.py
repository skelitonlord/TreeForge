from __future__ import annotations

from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactKind,
    AndroidUniverseArtifactRequirement,
)


_NON_SOURCE_TREE_RUNTIME_KINDS = frozenset(
    {
        AndroidUniverseArtifactKind.ART_RUNTIME_ARTIFACT,
        AndroidUniverseArtifactKind.OTA_CERTIFICATE_ARCHIVE,
    }
)


def canonical_artifact_requires_source_materialization(
    requirement: AndroidUniverseArtifactRequirement,
) -> bool:
    """
    Return whether an exact canonical artifact should become an
    independent Device Tree source payload.

    DIRECT_PARTITION proves observed runtime placement. It does not by itself
    prove that the artifact is an independent Android build input.

    Canonical runtime/compiler outputs remain preserved evidence and are not
    projected back into the generated proprietary source tree.
    """

    if not isinstance(
        requirement,
        AndroidUniverseArtifactRequirement,
    ):
        raise TypeError(
            "requirement must be an AndroidUniverseArtifactRequirement"
        )

    return not any(
        kind in _NON_SOURCE_TREE_RUNTIME_KINDS
        for kind in requirement.kinds
    )


# Compatibility for the preserved-artifact projection path. Both preserved
# and requirement-backed projections consume the same canonical artifact-role
# decision.
preserved_artifact_requires_source_materialization = (
    canonical_artifact_requires_source_materialization
)
