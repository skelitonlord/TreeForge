from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryContentObservationSnapshot:
    """
    Stable snapshot representation of one Discovery content observation.

    Primitive values are retained so the snapshot can later be serialized
    without depending on provider implementation classes.
    """

    signature: str

    confidence: str

    offset: int

    matched_bytes_hex: str = ""

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "signature",
                self.signature,
            ),
            (
                "confidence",
                self.confidence,
            ),
            (
                "matched_bytes_hex",
                self.matched_bytes_hex,
            ),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

        if not self.signature.strip():
            raise ValueError(
                "signature must not be empty"
            )

        if not self.confidence.strip():
            raise ValueError(
                "confidence must not be empty"
            )

        if not isinstance(
            self.offset,
            int,
        ):
            raise TypeError(
                "offset must be an int"
            )

        if self.offset < 0:
            raise ValueError(
                "offset must not be negative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryArtifactSnapshot:
    """
    Stable Discovery snapshot for one provider artifact.

    Exact provider source identity is preserved.

    Host filesystem paths and ZIP timestamps are intentionally excluded from
    this baseline because they are not reliable indicators that source content
    changed between runs.
    """

    source_name: str

    name: str

    provider_id: str

    source_type: str

    kind: str

    kind_evidence: str

    classification: str

    content_observations: tuple[
        AndroidDiscoveryContentObservationSnapshot,
        ...,
    ] = ()

    container_depth: int = 0

    size_bytes: int | None = None

    compressed_size_bytes: int | None = None

    crc32: int | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "source_name",
                self.source_name,
            ),
            (
                "name",
                self.name,
            ),
            (
                "provider_id",
                self.provider_id,
            ),
            (
                "source_type",
                self.source_type,
            ),
            (
                "kind",
                self.kind,
            ),
            (
                "kind_evidence",
                self.kind_evidence,
            ),
            (
                "classification",
                self.classification,
            ),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.content_observations,
            tuple,
        ):
            raise TypeError(
                "content_observations must be a tuple"
            )

        for observation in (
            self.content_observations
        ):
            if not isinstance(
                observation,
                AndroidDiscoveryContentObservationSnapshot,
            ):
                raise TypeError(
                    "content_observations must contain "
                    "AndroidDiscoveryContentObservationSnapshot "
                    "instances"
                )

        canonical_observations = tuple(
            sorted(
                self.content_observations,
                key=lambda observation: (
                    observation.offset,
                    observation.signature,
                    observation.confidence,
                    observation.matched_bytes_hex,
                ),
            )
        )

        object.__setattr__(
            self,
            "content_observations",
            canonical_observations,
        )

        if not isinstance(
            self.container_depth,
            int,
        ):
            raise TypeError(
                "container_depth must be an int"
            )

        if self.container_depth < 0:
            raise ValueError(
                "container_depth must not be negative"
            )

        for field_name, value in (
            (
                "size_bytes",
                self.size_bytes,
            ),
            (
                "compressed_size_bytes",
                self.compressed_size_bytes,
            ),
            (
                "crc32",
                self.crc32,
            ),
        ):
            if value is None:
                continue

            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an int or None"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

    @property
    def is_semantically_unknown(
        self,
    ) -> bool:
        return (
            self.classification
            == "unknown"
        )

    @property
    def has_content_observations(
        self,
    ) -> bool:
        return bool(
            self.content_observations
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryIdentityEvidenceSnapshot:
    """
    Stable snapshot of one identity-inference evidence record.
    """

    kind: str

    value: str

    source: str

    detail: str

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "kind",
                self.kind,
            ),
            (
                "value",
                self.value,
            ),
            (
                "source",
                self.source,
            ),
            (
                "detail",
                self.detail,
            ),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoverySnapshot:
    """
    Immutable canonical baseline for one completed Discovery view.

    This snapshot contains only facts established inside Discovery.

    It does not contain knowledge resolution, Android-version policy, build
    configuration, kernel analysis, SEPolicy analysis, or reconstruction
    results.

    android_version remains None until Discovery itself obtains direct evidence
    sufficient to establish it.
    """

    device_id: str | None = None

    board_platform: str | None = None

    android_version: str | None = None

    identity_evidence: tuple[
        AndroidDiscoveryIdentityEvidenceSnapshot,
        ...,
    ] = ()

    artifacts: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        self._validate_optional_string(
            self.device_id,
            field_name="device_id",
        )

        self._validate_optional_string(
            self.board_platform,
            field_name="board_platform",
        )

        self._validate_optional_string(
            self.android_version,
            field_name="android_version",
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
                    "identity_evidence must contain "
                    "AndroidDiscoveryIdentityEvidenceSnapshot "
                    "instances"
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
                AndroidDiscoveryArtifactSnapshot,
            ):
                raise TypeError(
                    "artifacts must contain "
                    "AndroidDiscoveryArtifactSnapshot instances"
                )

        canonical_evidence = tuple(
            sorted(
                self.identity_evidence,
                key=lambda evidence: (
                    evidence.kind,
                    evidence.value,
                    evidence.source,
                    evidence.detail,
                ),
            )
        )

        canonical_artifacts = tuple(
            sorted(
                self.artifacts,
                key=lambda artifact: (
                    artifact.source_name,
                    artifact.name,
                    artifact.provider_id,
                ),
            )
        )

        source_names = tuple(
            artifact.source_name
            for artifact in canonical_artifacts
        )

        if len(
            source_names
        ) != len(
            set(
                source_names
            )
        ):
            raise ValueError(
                "snapshot artifacts must not contain "
                "duplicate source names"
            )

        object.__setattr__(
            self,
            "identity_evidence",
            canonical_evidence,
        )

        object.__setattr__(
            self,
            "artifacts",
            canonical_artifacts,
        )

    @property
    def artifact_count(
        self,
    ) -> int:
        return len(
            self.artifacts
        )

    @property
    def known_artifact_count(
        self,
    ) -> int:
        return sum(
            not artifact.is_semantically_unknown
            for artifact in self.artifacts
        )

    @property
    def unknown_artifact_count(
        self,
    ) -> int:
        return sum(
            artifact.is_semantically_unknown
            for artifact in self.artifacts
        )

    @property
    def artifacts_with_content_observations(
        self,
    ) -> tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ]:
        return tuple(
            artifact
            for artifact in self.artifacts
            if artifact.has_content_observations
        )

    @property
    def unknown_artifacts(
        self,
    ) -> tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ]:
        return tuple(
            artifact
            for artifact in self.artifacts
            if artifact.is_semantically_unknown
        )

    @staticmethod
    def _validate_optional_string(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string or None"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )