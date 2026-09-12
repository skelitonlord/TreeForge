from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.reconstruction.build_system.boot import (
    AndroidReconstructionBootImageComposition,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


class AndroidDeviceTreeBootComponentSourceEquivalence(
    StrEnum,
):
    """
    Source-equivalent realization state for one canonical boot component.

    This is intentionally independent from exact factory-payload availability.

    A factory image proves what bytes participated in the shipped image.
    It does not, by itself, prove the OEM source/build mechanism that produced
    those bytes.
    """

    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeBootComponentEvidence:
    """
    Device Tree evidence for one exact canonical boot-image component.

    The model deliberately keeps two facts independent:

    1. whether the exact factory component payload is materially available;
    2. whether TreeForge has reconstructed a source-equivalent realization.

    Exact factory bytes are evidence and may later be selected as a legitimate
    prebuilt input when Android image construction semantics require that.
    Their existence never implies source-equivalent ownership.
    """

    composition: AndroidReconstructionBootImageComposition
    artifact: ExtractedArtifact

    semantic_name: str

    exact_factory_payload_available: bool

    source_equivalence: (
        AndroidDeviceTreeBootComponentSourceEquivalence
    )

    reason: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.composition,
            AndroidReconstructionBootImageComposition,
        ):
            raise TypeError(
                "composition must be an "
                "AndroidReconstructionBootImageComposition"
            )

        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            not isinstance(
                self.semantic_name,
                str,
            )
            or not self.semantic_name
        ):
            raise ValueError(
                "semantic_name must be a non-empty string"
            )

        if (
            self.artifact.semantic_name
            != self.semantic_name
        ):
            raise ValueError(
                "boot component evidence changed canonical "
                "Extraction semantic identity"
            )

        if not any(
            candidate is self.artifact
            for candidate
            in self.composition.component_artifacts
        ):
            raise ValueError(
                "boot component evidence must preserve exact "
                "Reconstruction component artifact identity"
            )

        if (
            self.artifact.parent
            is not self.composition.image_artifact
        ):
            raise ValueError(
                "boot component evidence must preserve exact "
                "canonical parent image identity"
            )

        if not isinstance(
            self.exact_factory_payload_available,
            bool,
        ):
            raise TypeError(
                "exact_factory_payload_available must be a bool"
            )

        if not isinstance(
            self.source_equivalence,
            AndroidDeviceTreeBootComponentSourceEquivalence,
        ):
            raise TypeError(
                "source_equivalence contains an invalid state"
            )

        if (
            not isinstance(
                self.reason,
                str,
            )
            or not self.reason
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )

    @property
    def requirement_id(
        self,
    ) -> str:
        return self.composition.requirement_id

    @property
    def component_id(
        self,
    ) -> str:
        return (
            "device-tree-boot-component:"
            f"{self.requirement_id}:"
            f"{self.semantic_name}"
        )


class AndroidDeviceTreeBootComponentEvidenceProjector:
    """
    Project boot-component evidence exclusively from canonical TreeForge data.

    This projector does not inspect AOSP, another device tree, a platform
    repository, or any source checkout.

    Initial source-equivalence state is intentionally UNRESOLVED. Later
    factory-derived reconstruction passes may promote individual components
    when TreeForge can actually prove a source-equivalent realization.
    """

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
    ) -> tuple[
        AndroidDeviceTreeBootComponentEvidence,
        ...,
    ]:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        projected: list[
            AndroidDeviceTreeBootComponentEvidence
        ] = []

        seen_component_ids: set[str] = set()

        expected_component_count = sum(
            len(
                composition.component_artifacts
            )
            for composition
            in reconstruction.boot_image_compositions
        )

        for composition in (
            reconstruction.boot_image_compositions
        ):
            for artifact in (
                composition.component_artifacts
            ):
                semantic_name = (
                    artifact.semantic_name
                )

                if (
                    not isinstance(
                        semantic_name,
                        str,
                    )
                    or not semantic_name
                ):
                    raise ValueError(
                        "canonical boot component lacks "
                        "Extraction semantic identity"
                    )

                exact_available = (
                    artifact.path.is_file()
                )

                if exact_available:
                    reason = (
                        "Exact factory component bytes are available "
                        "through canonical Extraction provenance. "
                        "The factory image proves shipped image "
                        "participation but does not alone prove a "
                        "source-equivalent build realization."
                    )
                else:
                    reason = (
                        "Canonical factory component identity is known, "
                        "but its exact extracted payload is not materially "
                        "accessible and no source-equivalent build "
                        "realization has been proven."
                    )

                evidence = (
                    AndroidDeviceTreeBootComponentEvidence(
                        composition=composition,
                        artifact=artifact,
                        semantic_name=semantic_name,
                        exact_factory_payload_available=(
                            exact_available
                        ),
                        source_equivalence=(
                            AndroidDeviceTreeBootComponentSourceEquivalence
                            .UNRESOLVED
                        ),
                        reason=reason,
                    )
                )

                if (
                    evidence.component_id
                    in seen_component_ids
                ):
                    raise ValueError(
                        "duplicate canonical boot component "
                        "evidence identity: "
                        f"{evidence.component_id}"
                    )

                seen_component_ids.add(
                    evidence.component_id
                )

                projected.append(
                    evidence
                )

        if (
            len(projected)
            != expected_component_count
        ):
            raise ValueError(
                "Device Tree boot-component evidence "
                "coverage mismatch"
            )

        result = tuple(
            sorted(
                projected,
                key=lambda item: (
                    item.component_id
                ),
            )
        )

        if len(result) != len(
            {
                item.component_id
                for item
                in result
            }
        ):
            raise ValueError(
                "Device Tree boot-component evidence "
                "identities must be unique"
            )

        return result
