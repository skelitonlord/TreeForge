from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidReconstructionCompositionEndpointKind(
    StrEnum,
):
    """
    Kind of one canonical Reconstruction composition endpoint.

    REPRESENTATION
        One endpoint is owned by an existing canonical Reconstruction
        representation.

    PRESERVED_ARTIFACT
        One endpoint is an exact canonical artifact preserved by Planning.

    CANONICAL_REQUIREMENT
        Universe established a canonical requirement/entity, but no
        reconstructed representation owns it in the current result.

    SEMANTIC
        The endpoint is an Android semantic concept rather than a source
        representation, such as a built-in INIT lifecycle event.

    UNRESOLVED
        Universe did not establish one canonical endpoint.

    Endpoint kind is a projection result only. It must never reinterpret
    the status of the originating Universe relationship.
    """

    REPRESENTATION = "representation"
    PRESERVED_ARTIFACT = "preserved_artifact"
    CANONICAL_REQUIREMENT = "canonical_requirement"
    SEMANTIC = "semantic"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionCompositionEndpoint:
    """
    One canonical endpoint used by the Reconstruction composition graph.

    The endpoint identifies how an already-established Universe relationship
    terminates in Reconstruction. It does not choose a source-tree owner,
    destination, filename, build module, or Device Tree location.
    """

    endpoint_id: str
    kind: AndroidReconstructionCompositionEndpointKind

    representation_id: str | None = None
    preserved_artifact_id: str | None = None
    canonical_identity: str | None = None
    semantic_identity: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.endpoint_id,
                str,
            )
            or not self.endpoint_id
        ):
            raise ValueError(
                "endpoint_id must be a non-empty string"
            )

        if not isinstance(
            self.kind,
            AndroidReconstructionCompositionEndpointKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidReconstructionCompositionEndpointKind"
            )

        optional_strings = (
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "preserved_artifact_id",
                self.preserved_artifact_id,
            ),
            (
                "canonical_identity",
                self.canonical_identity,
            ),
            (
                "semantic_identity",
                self.semantic_identity,
            ),
        )

        for field_name, value in optional_strings:
            if (
                value is not None
                and (
                    not isinstance(
                        value,
                        str,
                    )
                    or not value
                )
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty "
                    "string or None"
                )

        if (
            self.kind
            is AndroidReconstructionCompositionEndpointKind
            .REPRESENTATION
        ):
            if self.representation_id is None:
                raise ValueError(
                    "REPRESENTATION endpoint requires "
                    "representation_id"
                )

            if self.preserved_artifact_id is not None:
                raise ValueError(
                    "REPRESENTATION endpoint cannot carry "
                    "preserved_artifact_id"
                )

        elif (
            self.kind
            is AndroidReconstructionCompositionEndpointKind
            .PRESERVED_ARTIFACT
        ):
            if self.preserved_artifact_id is None:
                raise ValueError(
                    "PRESERVED_ARTIFACT endpoint requires "
                    "preserved_artifact_id"
                )

            if self.representation_id is not None:
                raise ValueError(
                    "PRESERVED_ARTIFACT endpoint cannot carry "
                    "representation_id"
                )

        elif (
            self.kind
            is AndroidReconstructionCompositionEndpointKind
            .CANONICAL_REQUIREMENT
        ):
            if self.canonical_identity is None:
                raise ValueError(
                    "CANONICAL_REQUIREMENT endpoint requires "
                    "canonical_identity"
                )

            if (
                self.representation_id is not None
                or self.preserved_artifact_id is not None
            ):
                raise ValueError(
                    "CANONICAL_REQUIREMENT endpoint cannot carry "
                    "representation or preserved-artifact identity"
                )

        elif (
            self.kind
            is AndroidReconstructionCompositionEndpointKind
            .SEMANTIC
        ):
            if self.semantic_identity is None:
                raise ValueError(
                    "SEMANTIC endpoint requires semantic_identity"
                )

            if (
                self.representation_id is not None
                or self.preserved_artifact_id is not None
            ):
                raise ValueError(
                    "SEMANTIC endpoint cannot carry representation "
                    "or preserved-artifact identity"
                )

        elif (
            self.kind
            is AndroidReconstructionCompositionEndpointKind
            .UNRESOLVED
        ):
            if (
                self.representation_id is not None
                or self.preserved_artifact_id is not None
            ):
                raise ValueError(
                    "UNRESOLVED endpoint cannot claim a resolved "
                    "Reconstruction target"
                )
