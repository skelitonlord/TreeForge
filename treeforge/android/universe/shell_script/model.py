from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.parsing.shell_script import (
    AndroidShellClasspathEntry,
    AndroidShellExecObservation,
    AndroidShellScriptParsingResult,
    ParsedAndroidShellScript,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseJavaArchiveAssociation,
)


class AndroidUniverseShellClasspathResolutionStatus(
    StrEnum
):
    RESOLVED = "resolved"
    DYNAMIC = "dynamic"
    UNMATCHED = "unmatched"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseShellClasspathResolution:
    entry: AndroidShellClasspathEntry

    status: (
        AndroidUniverseShellClasspathResolutionStatus
    )

    matched_archives: tuple[
        AndroidUniverseJavaArchiveAssociation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.entry,
            AndroidShellClasspathEntry,
        ):
            raise TypeError(
                "entry must be an AndroidShellClasspathEntry"
            )

        if not isinstance(
            self.status,
            AndroidUniverseShellClasspathResolutionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseShellClasspathResolutionStatus"
            )

        if (
            not isinstance(
                self.matched_archives,
                tuple,
            )
            or not all(
                isinstance(
                    archive,
                    AndroidUniverseJavaArchiveAssociation,
                )
                for archive
                in self.matched_archives
            )
        ):
            raise TypeError(
                "matched_archives contains invalid values"
            )

        if (
            self.status
            is AndroidUniverseShellClasspathResolutionStatus
            .RESOLVED
            and len(
                self.matched_archives
            ) != 1
        ):
            raise ValueError(
                "resolved shell CLASSPATH entry requires one archive"
            )

        if (
            self.status
            is AndroidUniverseShellClasspathResolutionStatus
            .AMBIGUOUS
            and len(
                self.matched_archives
            ) < 2
        ):
            raise ValueError(
                "ambiguous shell CLASSPATH entry requires multiple archives"
            )

        if (
            self.status
            in {
                AndroidUniverseShellClasspathResolutionStatus
                .DYNAMIC,
                AndroidUniverseShellClasspathResolutionStatus
                .UNMATCHED,
            }
            and self.matched_archives
        ):
            raise ValueError(
                "non-matched shell CLASSPATH entry cannot carry archives"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseShellScriptAssociation:
    """
    Canonical relationship between one parsed shell script and its exact
    filesystem Artifact requirement.
    """

    source: ParsedAndroidShellScript
    artifact: AndroidUniverseArtifactRequirement

    classpath_resolutions: tuple[
        AndroidUniverseShellClasspathResolution,
        ...,
    ] = ()

    app_process_execs: tuple[
        AndroidShellExecObservation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidShellScript,
        ):
            raise TypeError(
                "source must be a ParsedAndroidShellScript"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an AndroidUniverseArtifactRequirement"
            )

        if len(
            self.classpath_resolutions
        ) != len(
            self.source.classpath_entries
        ):
            raise ValueError(
                "shell reconciliation must preserve every "
                "CLASSPATH entry exactly once"
            )

        if not all(
            resolution.entry is entry
            for resolution, entry
            in zip(
                self.classpath_resolutions,
                self.source.classpath_entries,
                strict=True,
            )
        ):
            raise ValueError(
                "shell CLASSPATH reconciliation must preserve exact "
                "Parsing entry identity and order"
            )

        exec_ids = {
            id(
                value
            )
            for value
            in self.source.exec_observations
        }

        if any(
            id(
                value
            )
            not in exec_ids
            for value
            in self.app_process_execs
        ):
            raise ValueError(
                "app_process exec evidence must preserve exact "
                "Parsing exec identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseShellScriptReconciliation:
    source: AndroidShellScriptParsingResult

    associations: tuple[
        AndroidUniverseShellScriptAssociation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidShellScriptParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidShellScriptParsingResult"
            )

        if len(
            self.associations
        ) != len(
            self.source.scripts
        ):
            raise ValueError(
                "shell reconciliation must conserve every Parsing script"
            )

        if not all(
            association.source is script
            for association, script
            in zip(
                self.associations,
                self.source.scripts,
                strict=True,
            )
        ):
            raise ValueError(
                "shell reconciliation must preserve exact Parsing "
                "script identity and order"
            )
