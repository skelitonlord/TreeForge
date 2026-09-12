from __future__ import annotations

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactKind,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathInstalledJarStatus,
    AndroidUniverseClasspathRequirement,
)


class AndroidReconstructionClasspathBuildProjector:
    """
    Project exact installed Classpath JAR participation.

    Classpath Universe already owns installed-JAR reconciliation. This
    projector consumes those exact conclusions and does not rediscover
    filesystem paths or infer source-tree modules.
    """

    @staticmethod
    def project(
        classpath_requirement: AndroidUniverseClasspathRequirement,
        *,
        existing_build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ] = (),
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        if not isinstance(
            classpath_requirement,
            AndroidUniverseClasspathRequirement,
        ):
            raise TypeError(
                "classpath_requirement must be an "
                "AndroidUniverseClasspathRequirement"
            )

        if (
            not isinstance(
                existing_build_representations,
                tuple,
            )
            or not all(
                isinstance(
                    representation,
                    AndroidReconstructionBuildRepresentation,
                )
                for representation
                in existing_build_representations
            )
        ):
            raise TypeError(
                "existing_build_representations must contain only "
                "AndroidReconstructionBuildRepresentation values"
            )

        represented_artifact_ids: set[str] = set()

        for representation in existing_build_representations:
            if representation.preserved_artifact_id is not None:
                represented_artifact_ids.add(
                    representation.preserved_artifact_id
                )

            if representation.canonical_requirement_id is not None:
                represented_artifact_ids.add(
                    representation.canonical_requirement_id
                )

        projected: list[
            AndroidReconstructionBuildRepresentation
        ] = []

        projected_artifact_ids: set[str] = set()

        for resolution in (
            classpath_requirement.installed_jar_resolutions
        ):
            if (
                resolution.status
                is not
                AndroidUniverseClasspathInstalledJarStatus.RESOLVED
            ):
                continue

            if len(resolution.matched_artifacts) != 1:
                raise ValueError(
                    "resolved Classpath installed-JAR conclusion must "
                    "contain exactly one canonical Artifact requirement"
                )

            artifact_requirement = resolution.matched_artifacts[0]

            jar_kinds = {
                AndroidUniverseArtifactKind.FRAMEWORK_JAR,
                AndroidUniverseArtifactKind.JAVA_LIBRARY,
            }

            if not (
                set(artifact_requirement.kinds)
                & jar_kinds
            ):
                raise ValueError(
                    "resolved Classpath installed JAR must resolve to a "
                    "canonical FRAMEWORK_JAR or JAVA_LIBRARY Artifact "
                    "requirement: "
                    f"{artifact_requirement.requirement_id}, "
                    f"kinds={tuple(kind.value for kind in artifact_requirement.kinds)!r}"
                )

            artifact_requirement_id = (
                artifact_requirement.requirement_id
            )

            if artifact_requirement_id in represented_artifact_ids:
                continue

            if artifact_requirement_id in projected_artifact_ids:
                continue

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:classpath-java:"
                        f"{artifact_requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .JAVA_LIBRARY
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=(
                        "classpath-java:"
                        f"{artifact_requirement_id}"
                    ),
                    canonical_requirement_id=(
                        artifact_requirement_id
                    ),
                    installed_partition=(
                        artifact_requirement.partition_name
                    ),
                    installed_android_path=(
                        artifact_requirement.android_path
                    ),
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Classpath installed-JAR reconciliation "
                        "proves exact Java library build participation and "
                        "installed Artifact identity, but generic "
                        "Reconstruction cannot establish a concrete "
                        "source-tree Java module or Make/Soong mechanism."
                    ),
                )
            )

            projected_artifact_ids.add(
                artifact_requirement_id
            )

        return tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )
