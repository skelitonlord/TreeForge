from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
    ProviderArtifactKind,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderArtifactInventory:
    """
    Canonical exhaustive inventory of artifacts discovered by one provider.

    Discovery is broader than interpretation.

    Every provider artifact remains represented even when TreeForge does not
    yet understand its semantic meaning. Unknown artifacts therefore remain
    first-class entries rather than being filtered out during discovery.

    Canonical identity is based on the exact provider source name.

    The inventory owns ordering and lookup only. It does not resolve conflicts
    between providers, inspect artifact contents, materialize sources, or
    decide how artifacts participate in Android builds.
    """

    artifacts: tuple[
        ProviderArtifact,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        """
        Validate and canonicalize the inventory.
        """

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
                ProviderArtifact,
            ):
                raise TypeError(
                    "artifacts must contain only "
                    "ProviderArtifact objects"
                )

        source_names = tuple(
            artifact.source_name
            for artifact
            in self.artifacts
        )

        if (
            len(source_names)
            != len(
                set(
                    source_names
                )
            )
        ):
            raise ValueError(
                "artifacts must not contain "
                "duplicate source names"
            )

        canonical = tuple(
            sorted(
                self.artifacts,
                key=lambda artifact: (
                    artifact.source_name,
                    artifact.name,
                    artifact.kind.value,
                    artifact.classification.value,
                    artifact.provider_id,
                    artifact.source_type.value,
                ),
            )
        )

        object.__setattr__(
            self,
            "artifacts",
            canonical,
        )

    def __len__(
        self,
    ) -> int:
        """
        Return the number of inventoried artifacts.
        """

        return len(
            self.artifacts
        )

    def __iter__(
        self,
    ):
        """
        Iterate over artifacts in canonical order.
        """

        return iter(
            self.artifacts
        )

    def artifact(
        self,
        source_name: str,
    ) -> ProviderArtifact | None:
        """
        Return an artifact by exact provider source identity.
        """

        if not isinstance(
            source_name,
            str,
        ):
            raise TypeError(
                "source_name must be a string"
            )

        if not source_name.strip():
            raise ValueError(
                "source_name must not be empty"
            )

        for artifact in self.artifacts:
            if (
                artifact.source_name
                == source_name
            ):
                return artifact

        return None

    def artifact_named(
        self,
        name: str,
    ) -> ProviderArtifact | None:
        """
        Return the unique artifact with one exact basename.

        None is returned when no artifact has the name.

        A ValueError is raised when multiple artifacts share the basename.
        Source-name lookup must be used in that case because source_name is the
        canonical provider identity.
        """

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not name.strip():
            raise ValueError(
                "name must not be empty"
            )

        matches = tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.name == name
        )

        if not matches:
            return None

        if len(
            matches
        ) > 1:
            raise ValueError(
                "multiple provider artifacts have "
                f"the name: {name}"
            )

        return matches[0]

    def artifacts_of_kind(
        self,
        kind: ProviderArtifactKind,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return all artifacts with one structural kind.
        """

        if not isinstance(
            kind,
            ProviderArtifactKind,
        ):
            raise TypeError(
                "kind must be a ProviderArtifactKind"
            )

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.kind is kind
        )

    def artifacts_of_classification(
        self,
        classification: (
            ProviderArtifactClassification
        ),
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return all artifacts with one semantic classification.
        """

        if not isinstance(
            classification,
            ProviderArtifactClassification,
        ):
            raise TypeError(
                "classification must be a "
                "ProviderArtifactClassification"
            )

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if (
                artifact.classification
                is classification
            )
        )

    def artifact_for_classification(
        self,
        classification: (
            ProviderArtifactClassification
        ),
    ) -> ProviderArtifact | None:
        """
        Return one uniquely classified artifact.

        This is intended for semantic identities that should occur once in one
        provider result, such as boot.img or vendor.img.

        The inventory itself does not globally assume that every
        classification is unique, so ambiguity is detected here rather than
        during construction.
        """

        matches = (
            self.artifacts_of_classification(
                classification
            )
        )

        if not matches:
            return None

        if len(
            matches
        ) > 1:
            raise ValueError(
                "multiple provider artifacts have "
                "classification: "
                f"{classification.value}"
            )

        return matches[0]

    def contains_source_name(
        self,
        source_name: str,
    ) -> bool:
        """
        Return whether an exact source identity is present.
        """

        return (
            self.artifact(
                source_name
            )
            is not None
        )

    def contains_name(
        self,
        name: str,
    ) -> bool:
        """
        Return whether at least one artifact has an exact basename.

        Unlike artifact_named(), this method does not require basename
        uniqueness.
        """

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not name.strip():
            raise ValueError(
                "name must not be empty"
            )

        return any(
            artifact.name == name
            for artifact
            in self.artifacts
        )

    def contains_classification(
        self,
        classification: (
            ProviderArtifactClassification
        ),
    ) -> bool:
        """
        Return whether one semantic classification is present.
        """

        return bool(
            self.artifacts_of_classification(
                classification
            )
        )

    @property
    def images(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return every discovered image artifact.
        """

        return self.artifacts_of_kind(
            ProviderArtifactKind.IMAGE
        )

    @property
    def archives(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return every discovered archive artifact.
        """

        return self.artifacts_of_kind(
            ProviderArtifactKind.ARCHIVE
        )

    @property
    def text_artifacts(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return every discovered text artifact.
        """

        return self.artifacts_of_kind(
            ProviderArtifactKind.TEXT
        )

    @property
    def scripts(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return every discovered script artifact.
        """

        return self.artifacts_of_kind(
            ProviderArtifactKind.SCRIPT
        )

    @property
    def binaries(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return every non-image artifact structurally classified as binary.
        """

        return self.artifacts_of_kind(
            ProviderArtifactKind.BINARY
        )

    @property
    def unknown_artifacts(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return artifacts whose semantic classification remains unknown.
        """

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.is_unknown
        )

    @property
    def known_artifacts(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return semantically classified artifacts.
        """

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.is_known
        )

    @property
    def artifact_count(
        self,
    ) -> int:
        """
        Return the total artifact count.
        """

        return len(
            self.artifacts
        )

    @property
    def image_count(
        self,
    ) -> int:
        """
        Return the image-artifact count.
        """

        return len(
            self.images
        )

    @property
    def known_count(
        self,
    ) -> int:
        """
        Return the semantically classified artifact count.
        """

        return len(
            self.known_artifacts
        )

    @property
    def unknown_count(
        self,
    ) -> int:
        """
        Return the semantically unknown artifact count.
        """

        return len(
            self.unknown_artifacts
        )

    @property
    def source_names(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Return exact provider source identities in canonical order.
        """

        return tuple(
            artifact.source_name
            for artifact
            in self.artifacts
        )

    @property
    def names(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Return artifact basenames in canonical inventory order.
        """

        return tuple(
            artifact.name
            for artifact
            in self.artifacts
        )