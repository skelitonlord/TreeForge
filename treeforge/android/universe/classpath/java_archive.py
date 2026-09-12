from __future__ import annotations

from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveParsingResult,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathInstalledJarResolution,
    AndroidUniverseJavaArchiveAssociation,
    AndroidUniverseJavaArchiveReconciliation,
)


class AndroidUniverseJavaArchiveReconciler:
    """
    Reconcile intrinsic Java-archive Parsing evidence with canonical
    filesystem Artifact requirements and existing Classpath resolution.

    No path is rediscovered and classpath participation is never inferred
    from the fact that a file is a JAR.
    """

    def reconcile(
        self,
        parsing: AndroidJavaArchiveParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        installed_jar_resolutions: tuple[
            AndroidUniverseClasspathInstalledJarResolution,
            ...,
        ],
    ) -> AndroidUniverseJavaArchiveReconciliation:
        if not isinstance(
            parsing,
            AndroidJavaArchiveParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidJavaArchiveParsingResult"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        associations = []

        for archive in parsing.archives:
            filesystem_source = (
                archive.source.filesystem_source
            )

            matches = []

            for candidate in (
                artifact_requirements.requirements
            ):
                if (
                    candidate.inventory_entry.artifact
                    is not filesystem_source.artifact
                ):
                    continue

                try:
                    metadata_path = (
                        candidate.inventory_entry
                        .filesystem_path_for_materialized_path(
                            archive.source.host_path
                        )
                    )
                except ValueError:
                    continue

                if (
                    candidate.metadata_entry.path
                    == metadata_path
                ):
                    matches.append(
                        candidate
                    )

            if len(matches) != 1:
                raise ValueError(
                    "Java archive must resolve to exactly one "
                    "canonical Artifact requirement: "
                    f"{archive.source.source_name}:"
                    f"{archive.source.android_path.as_posix()} "
                    f"matches={len(matches)}"
                )

            artifact = matches[0]

            classpath_resolutions = tuple(
                resolution
                for resolution
                in installed_jar_resolutions
                if any(
                    candidate is artifact
                    for candidate
                    in resolution.matched_artifacts
                )
            )

            associations.append(
                AndroidUniverseJavaArchiveAssociation(
                    source=archive,
                    artifact=artifact,
                    classpath_resolutions=(
                        classpath_resolutions
                    ),
                )
            )

        return AndroidUniverseJavaArchiveReconciliation(
            source=parsing,
            associations=tuple(
                associations
            ),
        )
