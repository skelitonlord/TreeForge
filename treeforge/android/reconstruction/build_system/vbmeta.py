from __future__ import annotations

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.avb.model import (
    AndroidUniverseVbmetaRequirement,
)


class AndroidReconstructionVbmetaBuildProjector:
    """
    Project standalone canonical VBMeta partition-image participation.

    Universe VBMeta requirements may be either:

    - standalone AVB0 roots whose artifact is their container artifact; or
    - embedded/footer VBMeta regions contained by another canonical artifact.

    Partition provenance is independent from this structural distinction:
    embedded footer VBMeta may still retain the partition identity of its
    containing image.

    Only a standalone AVB0 root is a standalone physical VBMeta partition
    build artifact. Embedded/footer VBMeta remains canonical AVB evidence of
    its owning image and must not be projected as a fictitious VBMeta image.

    AVB chain, hash, hashtree, key, rollback, and trust-topology semantics
    remain canonical Universe evidence. They are not flattened into ordinary
    build dependency edges and do not imply signing-key or BoardConfig policy.
    """

    @staticmethod
    def project(
        vbmeta_requirements: tuple[
            AndroidUniverseVbmetaRequirement,
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
            vbmeta_requirements,
            tuple,
        ):
            raise TypeError(
                "vbmeta_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseVbmetaRequirement,
            )
            for requirement
            in vbmeta_requirements
        ):
            raise TypeError(
                "vbmeta_requirements must contain only "
                "AndroidUniverseVbmetaRequirement values"
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

        projected_requirement_ids: set[str] = set()

        projected: list[
            AndroidReconstructionBuildRepresentation
        ] = []

        for requirement in vbmeta_requirements:
            # Parsing preserves the decisive structural distinction:
            #
            #   standalone AVB0 root:
            #       artifact is container_artifact
            #
            #   embedded/footer VBMeta:
            #       artifact is not container_artifact
            #
            # Partition provenance is intentionally independent from that
            # distinction. An embedded footer may still belong to a known
            # partition such as boot, system, or vendor. Therefore
            # is_partition_backed must not be used as a synonym for
            # "standalone VBMeta image".
            if (
                requirement.artifact
                is not requirement.container_artifact
            ):
                continue

            if not requirement.is_partition_backed:
                raise ValueError(
                    "standalone canonical VBMeta root must retain "
                    "its partition provenance"
                )

            partition_name = (
                requirement.partition_name
            )

            if (
                not isinstance(
                    partition_name,
                    str,
                )
                or not partition_name
            ):
                raise ValueError(
                    "partition-backed VBMeta requirement must expose "
                    "a canonical partition name"
                )

            canonical_identity = (
                requirement.requirement_id
            )

            if canonical_identity in existing_requirement_ids:
                continue

            if canonical_identity in projected_requirement_ids:
                raise ValueError(
                    "canonical VBMeta partition appears more than once "
                    "during build participation projection: "
                    f"{canonical_identity}"
                )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:vbmeta:"
                        f"{canonical_identity}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .VBMETA_ARTIFACT
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=canonical_identity,
                    canonical_requirement_id=canonical_identity,
                    installed_partition=partition_name,
                    installed_android_path=None,
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Universe VBMeta evidence proves that "
                        "this exact VBMeta partition image participates in "
                        "the Android build and preserves its AVB metadata, "
                        "but Reconstruction does not invent signing-key "
                        "policy, BoardConfig directives, image-generation "
                        "syntax, source-tree ownership, or AVB trust policy."
                    ),
                )
            )

            projected_requirement_ids.add(
                canonical_identity
            )

        return tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )
