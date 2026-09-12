from __future__ import annotations

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.apex.deployment_context import (
    AndroidUniverseApexDeploymentPartition,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)


class AndroidReconstructionApexBuildProjector:
    """
    Project canonical APEX requirements into syntax-neutral build
    participation.

    Universe already establishes:
    - exact canonical APEX requirement identity;
    - exact Extraction container identity;
    - APEX package name and version;
    - canonical deployment partition and installed relative path;
    - runtime context.

    Runtime Linking may additionally classify an APEX as ACTIVE,
    EXCLUDED_SHARED_APEX, AMBIGUOUS, or UNRESOLVED for linkerconfig runtime
    participation. Those conclusions do not decide whether the canonical APEX
    itself participates in the Android build.

    Reconstruction therefore represents every canonical APEX requirement
    exactly once without choosing:
    - source-tree ownership;
    - source module identity;
    - prebuilt versus source-built mechanism;
    - Android.bp or Android.mk syntax;
    - product-package syntax;
    - filesystem materialization.
    """

    @staticmethod
    def project(
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
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
        if (
            not isinstance(
                apex_requirements,
                tuple,
            )
            or not all(
                isinstance(
                    requirement,
                    AndroidUniverseApexRequirement,
                )
                for requirement
                in apex_requirements
            )
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement values"
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

        requirement_ids = tuple(
            requirement.requirement_id
            for requirement
            in apex_requirements
        )

        if len(
            requirement_ids
        ) != len(
            set(requirement_ids)
        ):
            raise ValueError(
                "canonical APEX requirement identities must be unique"
            )

        existing_requirement_ids = {
            value
            for representation
            in existing_build_representations
            for value
            in (
                representation.canonical_requirement_id,
                representation.preserved_artifact_id,
            )
            if value is not None
        }

        projected = []

        for requirement in apex_requirements:
            if (
                requirement.requirement_id
                in existing_requirement_ids
            ):
                continue

            deployment = (
                requirement.deployment_context
            )

            installed_partition = (
                None
                if (
                    deployment.partition
                    is AndroidUniverseApexDeploymentPartition.UNKNOWN
                )
                else deployment.partition.value
            )

            relative_path = (
                deployment.relative_path.as_posix()
            )

            installed_android_path = (
                "/"
                + relative_path.lstrip("/")
            )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:apex:"
                        f"{requirement.requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .APEX
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=(
                        requirement.requirement_id
                    ),
                    canonical_requirement_id=(
                        requirement.requirement_id
                    ),
                    installed_partition=(
                        installed_partition
                    ),
                    installed_android_path=(
                        installed_android_path
                    ),
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Universe APEX evidence proves exact "
                        "installed APEX build participation, identity, "
                        "version, and deployment placement, but generic "
                        "Reconstruction does not establish the concrete "
                        "source module or build mechanism."
                    ),
                )
            )

            existing_requirement_ids.add(
                requirement.requirement_id
            )

        result = tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        if len(result) != len(
            {
                representation.canonical_requirement_id
                for representation
                in result
            }
        ):
            raise ValueError(
                "APEX build projection created duplicate canonical "
                "APEX participation"
            )

        return result
