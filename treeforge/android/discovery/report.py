from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.discovery.snapshot import (
    AndroidDiscoveryArtifactSnapshot,
    AndroidDiscoveryIdentityEvidenceSnapshot,
)
from treeforge.android.discovery.snapshot_diff import (
    AndroidDiscoveryArtifactChange,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryComparisonReport:
    """
    Optional Discovery snapshot-comparison section.

    This model preserves comparison facts only. It does not interpret why
    artifacts or identities changed.
    """

    device_before: str | None = None
    device_after: str | None = None

    android_version_before: str | None = None
    android_version_after: str | None = None

    added: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    removed: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    changed: tuple[
        AndroidDiscoveryArtifactChange,
        ...,
    ] = ()

    unchanged_count: int = 0

    newly_unknown: tuple[
        AndroidDiscoveryArtifactChange,
        ...,
    ] = ()

    newly_understood: tuple[
        AndroidDiscoveryArtifactChange,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for field_name, values, expected_type in (
            (
                "added",
                self.added,
                AndroidDiscoveryArtifactSnapshot,
            ),
            (
                "removed",
                self.removed,
                AndroidDiscoveryArtifactSnapshot,
            ),
            (
                "changed",
                self.changed,
                AndroidDiscoveryArtifactChange,
            ),
            (
                "newly_unknown",
                self.newly_unknown,
                AndroidDiscoveryArtifactChange,
            ),
            (
                "newly_understood",
                self.newly_understood,
                AndroidDiscoveryArtifactChange,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            for value in values:
                if not isinstance(
                    value,
                    expected_type,
                ):
                    raise TypeError(
                        f"{field_name} contains an invalid value"
                    )

        if not isinstance(
            self.unchanged_count,
            int,
        ):
            raise TypeError(
                "unchanged_count must be an int"
            )

        if self.unchanged_count < 0:
            raise ValueError(
                "unchanged_count must not be negative"
            )

    @property
    def added_count(
        self,
    ) -> int:
        return len(
            self.added
        )

    @property
    def removed_count(
        self,
    ) -> int:
        return len(
            self.removed
        )

    @property
    def changed_count(
        self,
    ) -> int:
        return len(
            self.changed
        )

    @property
    def newly_unknown_count(
        self,
    ) -> int:
        return len(
            self.newly_unknown
        )

    @property
    def newly_understood_count(
        self,
    ) -> int:
        return len(
            self.newly_understood
        )

    @property
    def device_changed(
        self,
    ) -> bool:
        return (
            self.device_before
            != self.device_after
        )

    @property
    def android_version_changed(
        self,
    ) -> bool:
        return (
            self.android_version_before
            != self.android_version_after
        )

    @property
    def has_changes(
        self,
    ) -> bool:
        return bool(
            self.device_changed
            or self.android_version_changed
            or self.added
            or self.removed
            or self.changed
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryReport:
    """
    Canonical immutable Discovery report.

    This is the highest reporting model for the Discovery milestone.

    Every field must originate from facts already established by Discovery.

    The report does not resolve knowledge modules, infer unsupported Android
    versions, apply device/platform policy, or perform downstream analysis.
    """

    device_id: str | None = None

    android_version: str | None = None

    identity_evidence: tuple[
        AndroidDiscoveryIdentityEvidenceSnapshot,
        ...,
    ] = ()

    total_artifact_count: int = 0

    known_artifact_count: int = 0

    unknown_artifact_count: int = 0

    content_observed_artifact_count: int = 0

    structurally_known_unknown_count: int = 0

    structurally_unknown_unknown_count: int = 0

    unknown_artifacts: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    comparison: (
        AndroidDiscoveryComparisonReport
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
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
            (
                "content_observed_artifact_count",
                self.content_observed_artifact_count,
            ),
            (
                "structurally_known_unknown_count",
                self.structurally_known_unknown_count,
            ),
            (
                "structurally_unknown_unknown_count",
                self.structurally_unknown_unknown_count,
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

        if (
            self.known_artifact_count
            + self.unknown_artifact_count
            != self.total_artifact_count
        ):
            raise ValueError(
                "known and unknown artifact counts "
                "must equal total artifact count"
            )

        if (
            self.structurally_known_unknown_count
            + self.structurally_unknown_unknown_count
            != self.unknown_artifact_count
        ):
            raise ValueError(
                "structural unknown counts must equal "
                "unknown_artifact_count"
            )

        if (
            len(
                self.unknown_artifacts
            )
            != self.unknown_artifact_count
        ):
            raise ValueError(
                "unknown_artifacts must match "
                "unknown_artifact_count"
            )

        if (
            self.content_observed_artifact_count
            > self.total_artifact_count
        ):
            raise ValueError(
                "content_observed_artifact_count cannot "
                "exceed total_artifact_count"
            )

        if not isinstance(
            self.identity_evidence,
            tuple,
        ):
            raise TypeError(
                "identity_evidence must be a tuple"
            )

        for evidence in (
            self.identity_evidence
        ):
            if not isinstance(
                evidence,
                AndroidDiscoveryIdentityEvidenceSnapshot,
            ):
                raise TypeError(
                    "identity_evidence contains an invalid value"
                )

        if not isinstance(
            self.unknown_artifacts,
            tuple,
        ):
            raise TypeError(
                "unknown_artifacts must be a tuple"
            )

        for artifact in (
            self.unknown_artifacts
        ):
            if not isinstance(
                artifact,
                AndroidDiscoveryArtifactSnapshot,
            ):
                raise TypeError(
                    "unknown_artifacts contains an invalid value"
                )

            if not artifact.is_semantically_unknown:
                raise ValueError(
                    "unknown_artifacts must contain only "
                    "semantically unknown artifacts"
                )

        if (
            self.comparison is not None
            and not isinstance(
                self.comparison,
                AndroidDiscoveryComparisonReport,
            )
        ):
            raise TypeError(
                "comparison must be an "
                "AndroidDiscoveryComparisonReport or None"
            )

        object.__setattr__(
            self,
            "identity_evidence",
            tuple(
                sorted(
                    self.identity_evidence,
                    key=lambda evidence: (
                        evidence.kind,
                        evidence.value,
                        evidence.source,
                        evidence.detail,
                    ),
                )
            ),
        )

        object.__setattr__(
            self,
            "unknown_artifacts",
            tuple(
                sorted(
                    self.unknown_artifacts,
                    key=lambda artifact: (
                        artifact.source_name
                    ),
                )
            ),
        )

    @property
    def has_identity(
        self,
    ) -> bool:
        return bool(
            self.device_id is not None
            or self.android_version is not None
        )

    @property
    def has_unknown_artifacts(
        self,
    ) -> bool:
        return bool(
            self.unknown_artifacts
        )

    @property
    def has_comparison(
        self,
    ) -> bool:
        return (
            self.comparison is not None
        )