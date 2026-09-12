from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.providers.artifact import (
    ProviderArtifactClassification,
    ProviderArtifactKind,
    ProviderArtifactKindEvidence,
)
from treeforge.android.providers.content_observation import (
    ProviderContentObservation,
)
from treeforge.android.providers.provenance import (
    ProviderArtifactProvenance,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUnknownArtifact:
    """
    Immutable Discovery report entry for one semantically unknown artifact.

    This model preserves what Discovery knows without trying to interpret the
    artifact beyond that evidence.

    Structural kind, content observations, and semantic classification remain
    independent.

    An artifact may therefore be structurally understood and contain known
    byte-level signatures while still remaining semantically unknown.
    """

    source_name: str

    name: str

    provider_id: str

    source_type: ProviderSourceType

    kind: ProviderArtifactKind

    kind_evidence: ProviderArtifactKindEvidence

    classification: ProviderArtifactClassification

    content_observations: tuple[
        ProviderContentObservation,
        ...,
    ] = ()

    provenance: (
        ProviderArtifactProvenance
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        for (
            field_name,
            value,
        ) in (
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
            self.source_type,
            ProviderSourceType,
        ):
            raise TypeError(
                "source_type must be a "
                "ProviderSourceType"
            )

        if not isinstance(
            self.kind,
            ProviderArtifactKind,
        ):
            raise TypeError(
                "kind must be a "
                "ProviderArtifactKind"
            )

        if not isinstance(
            self.kind_evidence,
            ProviderArtifactKindEvidence,
        ):
            raise TypeError(
                "kind_evidence must be a "
                "ProviderArtifactKindEvidence"
            )

        if not isinstance(
            self.classification,
            ProviderArtifactClassification,
        ):
            raise TypeError(
                "classification must be a "
                "ProviderArtifactClassification"
            )

        if (
            self.classification
            is not ProviderArtifactClassification.UNKNOWN
        ):
            raise ValueError(
                "AndroidUnknownArtifact requires "
                "UNKNOWN semantic classification"
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
                ProviderContentObservation,
            ):
                raise TypeError(
                    "content_observations must contain "
                    "ProviderContentObservation instances"
                )

        canonical_observations = tuple(
            sorted(
                self.content_observations,
                key=lambda observation: (
                    observation.offset,
                    observation.signature.value,
                    observation.confidence.value,
                    observation.matched_bytes,
                ),
            )
        )

        object.__setattr__(
            self,
            "content_observations",
            canonical_observations,
        )

        if (
            self.provenance is not None
            and not isinstance(
                self.provenance,
                ProviderArtifactProvenance,
            )
        ):
            raise TypeError(
                "provenance must be a "
                "ProviderArtifactProvenance or None"
            )

    @property
    def has_known_structure(
        self,
    ) -> bool:
        """
        Return whether Discovery understands the artifact's structural kind.
        """

        return (
            self.kind
            is not ProviderArtifactKind.UNKNOWN
        )

    @property
    def has_content_observations(
        self,
    ) -> bool:
        """
        Return whether Discovery collected byte-level observations.
        """

        return bool(
            self.content_observations
        )

    @property
    def exact_content_observations(
        self,
    ) -> tuple[
        ProviderContentObservation,
        ...,
    ]:
        """
        Return exact signature observations only.
        """

        return tuple(
            observation
            for observation
            in self.content_observations
            if observation.is_exact
        )

    @property
    def heuristic_content_observations(
        self,
    ) -> tuple[
        ProviderContentObservation,
        ...,
    ]:
        """
        Return heuristic content observations only.
        """

        return tuple(
            observation
            for observation
            in self.content_observations
            if observation.is_heuristic
        )