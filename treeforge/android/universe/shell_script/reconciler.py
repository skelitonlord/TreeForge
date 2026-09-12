from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.parsing.shell_script import (
    AndroidShellScriptParsingResult,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseJavaArchiveReconciliation,
)
from treeforge.android.universe.shell_script.model import (
    AndroidUniverseShellClasspathResolution,
    AndroidUniverseShellClasspathResolutionStatus,
    AndroidUniverseShellScriptAssociation,
    AndroidUniverseShellScriptReconciliation,
)


class AndroidUniverseShellScriptReconciler:
    """
    Promote intrinsic Parsing shell observations into canonical Universe
    artifact relationships.

    All physical identity and Android-path reconciliation happens here.
    """

    _APP_PROCESS_NAMES = frozenset({
        "app_process",
        "app_process32",
        "app_process64",
    })

    def reconcile(
        self,
        parsing: AndroidShellScriptParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        java_archive_reconciliation: (
            AndroidUniverseJavaArchiveReconciliation
            | None
        ),
    ) -> AndroidUniverseShellScriptReconciliation:
        if not isinstance(
            parsing,
            AndroidShellScriptParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidShellScriptParsingResult"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        java_archives = (
            ()
            if java_archive_reconciliation is None
            else java_archive_reconciliation.associations
        )

        associations = []

        for script in parsing.scripts:
            filesystem_source = (
                script.source.filesystem_source
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
                            script.source.host_path
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

            if len(
                matches
            ) != 1:
                raise ValueError(
                    "shell script must resolve to exactly one "
                    "canonical Artifact requirement: "
                    f"{script.source.source_name}:"
                    f"{script.source.android_path.as_posix()} "
                    f"matches={len(matches)}"
                )

            classpath_resolutions = []

            for entry in script.classpath_entries:
                if entry.resolved_path is None:
                    classpath_resolutions.append(
                        AndroidUniverseShellClasspathResolution(
                            entry=entry,
                            status=(
                                AndroidUniverseShellClasspathResolutionStatus
                                .DYNAMIC
                            ),
                        )
                    )
                    continue

                archive_matches = tuple(
                    association
                    for association
                    in java_archives
                    if (
                        association
                        .source
                        .source
                        .android_path
                        == entry.resolved_path
                    )
                )

                if len(
                    archive_matches
                ) == 1:
                    status = (
                        AndroidUniverseShellClasspathResolutionStatus
                        .RESOLVED
                    )
                elif not archive_matches:
                    status = (
                        AndroidUniverseShellClasspathResolutionStatus
                        .UNMATCHED
                    )
                else:
                    status = (
                        AndroidUniverseShellClasspathResolutionStatus
                        .AMBIGUOUS
                    )

                classpath_resolutions.append(
                    AndroidUniverseShellClasspathResolution(
                        entry=entry,
                        status=status,
                        matched_archives=(
                            archive_matches
                        ),
                    )
                )

            app_process_execs = []

            for observation in (
                script.exec_observations
            ):
                if not observation.resolved_argv:
                    continue

                executable = (
                    observation.resolved_argv[
                        0
                    ]
                )

                if executable is None:
                    continue

                name = PurePosixPath(
                    executable
                ).name

                if name in self._APP_PROCESS_NAMES:
                    app_process_execs.append(
                        observation
                    )

            associations.append(
                AndroidUniverseShellScriptAssociation(
                    source=script,
                    artifact=matches[
                        0
                    ],
                    classpath_resolutions=tuple(
                        classpath_resolutions
                    ),
                    app_process_execs=tuple(
                        app_process_execs
                    ),
                )
            )

        return AndroidUniverseShellScriptReconciliation(
            source=parsing,
            associations=tuple(
                associations
            ),
        )
