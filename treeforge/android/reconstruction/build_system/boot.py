from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.boot.requirement import (
    AndroidUniverseBootFamilyRequirement,
)


_BOOT_REQUIREMENT_TYPES = (
    AndroidUniverseBootFamilyRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidReconstructionBootImageComposition:
    """
    Exact syntax-neutral composition of one canonical boot-family image.

    Extraction owns physical image structure and component materialization.
    Parsing preserves exact component artifact identity. Universe owns
    boot-family semantics and exposes that canonical component population.

    Reconstruction records only the source-image composition relationship
    required by downstream Device Tree realization. It does not choose
    BoardConfig variables, source-tree placement, Make/Soong syntax, or
    image-generation policy.
    """

    requirement: AndroidUniverseBootFamilyRequirement

    image_artifact: object

    component_artifacts: tuple[
        object,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement,
            _BOOT_REQUIREMENT_TYPES,
        ):
            raise TypeError(
                "requirement must be a canonical "
                "Universe boot-family requirement"
            )

        expected_image_artifact = (
            self.requirement
            .partition
            .artifact
        )

        if (
            self.image_artifact
            is not expected_image_artifact
        ):
            raise ValueError(
                "boot image composition must preserve the exact "
                "canonical partition Extraction artifact"
            )

        if not isinstance(
            self.component_artifacts,
            tuple,
        ):
            raise TypeError(
                "component_artifacts must be a tuple"
            )

        expected_components = (
            self.requirement
            .component_artifacts
        )

        if (
            len(
                self.component_artifacts
            )
            != len(
                expected_components
            )
        ):
            raise ValueError(
                "boot image composition must preserve the complete "
                "canonical Universe component population"
            )

        if not all(
            actual is expected
            for actual, expected
            in zip(
                self.component_artifacts,
                expected_components,
                strict=True,
            )
        ):
            raise ValueError(
                "boot image composition must preserve exact "
                "canonical component artifact identity and ordering"
            )

        if not all(
            artifact.parent
            is self.image_artifact
            for artifact
            in self.component_artifacts
        ):
            raise ValueError(
                "every boot image component must preserve the exact "
                "canonical parent image artifact"
            )

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            self.requirement
            .requirement_id
        )

    @property
    def composition_id(
        self,
    ) -> str:
        return (
            "boot-image-composition:"
            f"{self.requirement_id}"
        )


class AndroidReconstructionBootBuildProjector:
    """
    Project canonical boot-family image participation.

    Universe owns boot/init_boot/vendor_boot image semantics and exact
    partition/image provenance. Reconstruction records that those canonical
    images participate in the eventual Android build without choosing
    BoardConfig, Make, Soong, source-tree placement, or image-generation
    syntax.
    """

    @staticmethod
    def project_compositions(
        boot_requirements: tuple[
            AndroidUniverseBootFamilyRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionBootImageComposition,
        ...,
    ]:
        """
        Preserve the exact component population of every canonical
        boot-family image.

        These relationships are image composition, not ordinary Android
        build dependency edges. Component artifacts therefore do not enter
        AndroidReconstructionBuildRepresentation.dependency_ids.
        """

        if not isinstance(
            boot_requirements,
            tuple,
        ):
            raise TypeError(
                "boot_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                _BOOT_REQUIREMENT_TYPES,
            )
            for requirement
            in boot_requirements
        ):
            raise TypeError(
                "boot_requirements must contain only canonical "
                "Universe boot-family requirements"
            )

        requirement_ids = tuple(
            requirement.requirement_id
            for requirement
            in boot_requirements
        )

        if len(
            requirement_ids
        ) != len(
            set(
                requirement_ids
            )
        ):
            raise ValueError(
                "canonical boot-family requirement identities "
                "must be unique"
            )

        result = tuple(
            sorted(
                (
                    AndroidReconstructionBootImageComposition(
                        requirement=requirement,
                        image_artifact=(
                            requirement
                            .partition
                            .artifact
                        ),
                        component_artifacts=(
                            requirement
                            .component_artifacts
                        ),
                    )
                    for requirement
                    in boot_requirements
                ),
                key=lambda composition: (
                    composition.composition_id
                ),
            )
        )

        return result

    @staticmethod
    def project(
        boot_requirements: tuple[
            AndroidUniverseBootFamilyRequirement,
            ...,
        ],
        *,
        existing_build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ] = (),
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        if not isinstance(
            boot_requirements,
            tuple,
        ):
            raise TypeError(
                "boot_requirements must be a tuple"
            )

        if (
            not isinstance(
                existing_build_representations,
                tuple,
            )
            or not all(
                isinstance(
                    representation,
                    AndroidReconstructionBuildRepresentation,
                )
                for representation
                in existing_build_representations
            )
        ):
            raise TypeError(
                "existing_build_representations must contain only "
                "AndroidReconstructionBuildRepresentation values"
            )

        existing_requirement_ids = {
            representation.canonical_requirement_id
            for representation
            in existing_build_representations
            if representation.canonical_requirement_id is not None
        }

        projected: list[
            AndroidReconstructionBuildRepresentation
        ] = []

        projected_requirement_ids: set[str] = set()

        for requirement in boot_requirements:
            requirement_id = requirement.requirement_id

            if requirement_id in existing_requirement_ids:
                continue

            if requirement_id in projected_requirement_ids:
                raise ValueError(
                    "canonical boot-family requirement appears more than "
                    "once during build participation projection: "
                    f"{requirement_id}"
                )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:boot:"
                        f"{requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .BOOT_ARTIFACT
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=requirement_id,
                    canonical_requirement_id=requirement_id,
                    installed_partition=(
                        requirement.partition.name
                    ),
                    installed_android_path=None,
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Universe boot-family evidence proves "
                        "that this boot image is a required Android build "
                        "artifact and preserves its exact image semantics "
                        "and partition identity, but Reconstruction does "
                        "not choose BoardConfig, Make/Soong, source-tree "
                        "placement, or image-generation syntax."
                    ),
                )
            )

            projected_requirement_ids.add(
                requirement_id
            )

        return tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )
