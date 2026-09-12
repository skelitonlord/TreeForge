from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.discovery.unknown_artifact import (
    AndroidUnknownArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUnknownArtifactReport:
    """
    Immutable Discovery report describing semantically unknown artifacts.

    Counts describe the provider artifacts represented by the Discovery result
    used to build this report.

    Unknown entries remain deterministically ordered by canonical source name.
    """

    total_artifact_count: int = 0

    known_artifact_count: int = 0

    unknown_artifact_count: int = 0

    artifacts: tuple[
        AndroidUnknownArtifact,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for (
            field_name,
            value,
        ) in (
            (
                "total_artifact_count",
                self.total_artifact_count,
            ),
            (
                "known_artifact_count",
                self.known_artifact_count,
            ),
            (
                "unknown_artifact_count",
                self.unknown_artifact_count,
            ),
        ):
            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        if not isinstance(
            self.artifacts,
            tuple,
        ):
            raise TypeError(
                "artifacts must be a tuple"
            )

        for artifact in self.artifacts:
            if not isinstance(
                artifact,
                AndroidUnknownArtifact,
            ):
                raise TypeError(
                    "artifacts must contain "
                    "AndroidUnknownArtifact instances"
                )

        if (
            self.total_artifact_count
            != (
                self.known_artifact_count
                + self.unknown_artifact_count
            )
        ):
            raise ValueError(
                "known and unknown artifact counts "
                "must equal total artifact count"
            )

        if (
            self.unknown_artifact_count
            != len(
                self.artifacts
            )
        ):
            raise ValueError(
                "unknown_artifact_count must match "
                "the number of report artifacts"
            )

        canonical = tuple(
            sorted(
                self.artifacts,
                key=lambda artifact: (
                    artifact.source_name,
                    artifact.name,
                    artifact.provider_id,
                ),
            )
        )

        object.__setattr__(
            self,
            "artifacts",
            canonical,
        )

    @property
    def artifacts_with_content_observations(
        self,
    ) -> tuple[
        AndroidUnknownArtifact,
        ...,
    ]:
        """
        Return unknown artifacts with at least one byte-level observation.
        """

        return tuple(
            artifact
            for artifact in self.artifacts
            if artifact.has_content_observations
        )


    @property
    def artifacts_without_content_observations(
        self,
    ) -> tuple[
        AndroidUnknownArtifact,
        ...,
    ]:
        """
        Return unknown artifacts with no recognized content observation.
        """

        return tuple(
            artifact
            for artifact in self.artifacts
            if not artifact.has_content_observations
        )

    @property
    def has_unknown_artifacts(
        self,
    ) -> bool:
        return bool(
            self.artifacts
        )

    @property
    def structurally_known_unknowns(
        self,
    ) -> tuple[
        AndroidUnknownArtifact,
        ...,
    ]:
        """
        Return semantically unknown artifacts whose structure is understood.
        """

        return tuple(
            artifact
            for artifact in self.artifacts
            if artifact.has_known_structure
        )

    @property
    def structurally_unknown_unknowns(
        self,
    ) -> tuple[
        AndroidUnknownArtifact,
        ...,
    ]:
        """
        Return artifacts unknown both structurally and semantically.
        """

        return tuple(
            artifact
            for artifact in self.artifacts
            if not artifact.has_known_structure
        )