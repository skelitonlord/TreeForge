from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath

from treeforge.android.universe.apex import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementInventory,
    apex_names_by_container_identity,
    artifact_android_namespace_paths,
    artifact_projects_to_android_runtime_namespace,
    normalize_android_namespace_path,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathInstalledJarResolution,
    AndroidUniverseClasspathInstalledJarStatus,
    AndroidUniverseEffectiveClasspath,
)


class AndroidUniverseClasspathInstalledJarReconciler:
    """
    Resolve effective Classpath entries against canonical installed artifacts.

    Artifact enumeration remains owned by the Universe Artifact family.
    Runtime namespace projection remains owned by Artifact namespace semantics.

    This reconciler performs no filesystem traversal, host-path lookup,
    symlink expansion, APEX-name inference, or JAR parsing.
    """

    def reconcile(
        self,
        *,
        effective_classpaths: tuple[
            AndroidUniverseEffectiveClasspath,
            ...,
        ],
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseClasspathInstalledJarResolution,
        ...,
    ]:
        if not isinstance(
            effective_classpaths,
            tuple,
        ):
            raise TypeError(
                "effective_classpaths must be a tuple"
            )

        if not all(
            isinstance(
                effective,
                AndroidUniverseEffectiveClasspath,
            )
            for effective
            in effective_classpaths
        ):
            raise TypeError(
                "effective_classpaths must contain only "
                "AndroidUniverseEffectiveClasspath instances"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        apex_names = (
            apex_names_by_container_identity(
                apex_requirements
            )
        )

        artifacts_by_runtime_path = defaultdict(
            dict
        )

        for artifact in (
            artifact_requirements.requirements
        ):
            if not (
                artifact_projects_to_android_runtime_namespace(
                    requirement=artifact,
                    apex_names_by_container_id=apex_names,
                )
            ):
                continue

            for projected_path in (
                artifact_android_namespace_paths(
                    requirement=artifact,
                    apex_names_by_container_id=apex_names,
                )
            ):
                artifacts_by_runtime_path[
                    projected_path
                ][
                    artifact.identity_key
                ] = artifact

        results = []

        for effective in effective_classpaths:
            for entry in effective.entries:
                declared_path = PurePosixPath(
                    entry.requirement.declared_path
                )

                if not declared_path.is_absolute():
                    declared_path = (
                        PurePosixPath("/")
                        / declared_path
                    )

                declared_path = (
                    normalize_android_namespace_path(
                        declared_path
                    )
                )

                matches = tuple(
                    sorted(
                        artifacts_by_runtime_path.get(
                            declared_path,
                            {},
                        ).values(),
                        key=lambda artifact: (
                            artifact.key
                        ),
                    )
                )

                if not matches:
                    status = (
                        AndroidUniverseClasspathInstalledJarStatus
                        .ABSENT
                    )

                elif len(
                    matches
                ) == 1:
                    status = (
                        AndroidUniverseClasspathInstalledJarStatus
                        .RESOLVED
                    )

                else:
                    status = (
                        AndroidUniverseClasspathInstalledJarStatus
                        .AMBIGUOUS
                    )

                results.append(
                    AndroidUniverseClasspathInstalledJarResolution(
                        entry=entry,
                        status=status,
                        matched_artifacts=matches,
                    )
                )

        return tuple(
            results
        )
