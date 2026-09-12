from __future__ import annotations

from dataclasses import replace

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleRequirement,
)


class AndroidReconstructionKernelModuleBuildProjector:
    """
    Project canonical physical kernel modules into syntax-neutral Android
    build participation.

    Physical identity is inherited from the exact canonical filesystem
    Artifact requirement corresponding to the module's ParsedAndroidElf
    source. Kernel-module logical names are never used for physical matching.

    Canonical modules.dep hard dependencies already resolve exact physical
    owner/dependency module instances in Android Device Universe. This class
    consumes those conclusions mechanically; it does not repeat module-name
    resolution.
    """

    @staticmethod
    def _module_artifact_identity(
        module,
    ):
        source = (
            module.source
            .elf
            .source
        )

        filesystem_source = (
            source.filesystem_source
        )

        if filesystem_source is None:
            raise ValueError(
                "kernel module must preserve an exact filesystem source"
            )

        if source.metadata_entry is None:
            raise ValueError(
                "kernel module must preserve exact filesystem metadata"
            )

        return (
            id(filesystem_source.artifact),
            id(source.metadata_entry),
        )

    @staticmethod
    def project(
        kernel_module_requirement: AndroidUniverseKernelModuleRequirement,
        artifact_requirements,
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
            kernel_module_requirement,
            AndroidUniverseKernelModuleRequirement,
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement"
            )

        requirements = getattr(
            artifact_requirements,
            "requirements",
            None,
        )

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "artifact_requirements must expose tuple requirements"
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

        artifact_by_identity = {
            requirement.identity_key: requirement
            for requirement
            in requirements
        }

        if len(
            artifact_by_identity
        ) != len(
            requirements
        ):
            raise ValueError(
                "canonical Artifact identities must be unique"
            )

        artifact_requirement_by_id = {
            requirement.requirement_id: requirement
            for requirement
            in requirements
        }

        if len(
            artifact_requirement_by_id
        ) != len(
            requirements
        ):
            raise ValueError(
                "canonical Artifact requirement IDs must be unique"
            )

        represented_artifact_ids = {
            value
            for representation
            in existing_build_representations
            for value in (
                representation.preserved_artifact_id,
                representation.canonical_requirement_id,
            )
            if value in artifact_requirement_by_id
        }

        projected = []

        for module in (
            kernel_module_requirement.module_requirements
        ):
            identity_key = (
                AndroidReconstructionKernelModuleBuildProjector
                ._module_artifact_identity(
                    module
                )
            )

            artifact_requirement = (
                artifact_by_identity.get(
                    identity_key
                )
            )

            if artifact_requirement is None:
                raise ValueError(
                    "canonical kernel module has no exact canonical "
                    "Artifact requirement"
                )

            if (
                artifact_requirement.requirement_id
                in represented_artifact_ids
            ):
                continue

            source = (
                module.source
                .elf
                .source
            )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:kernel-module:"
                        f"{artifact_requirement.requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .KERNEL_MODULE
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=(
                        f"kernel-module:"
                        f"{source.source_name}:"
                        f"{source.android_path.as_posix()}"
                    ),
                    canonical_requirement_id=(
                        artifact_requirement.requirement_id
                    ),
                    installed_partition=(
                        artifact_requirement.partition_name
                    ),
                    installed_android_path=(
                        artifact_requirement.android_path
                    ),
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical kernel-module and Artifact evidence "
                        "proves exact physical module build participation "
                        "and installed identity, but generic Reconstruction "
                        "does not establish the concrete source module or "
                        "build mechanism."
                    ),
                )
            )

            represented_artifact_ids.add(
                artifact_requirement.requirement_id
            )

        return tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

    @staticmethod
    def project_configurations(
        kernel_module_requirement: AndroidUniverseKernelModuleRequirement,
        artifact_requirements,
        *,
        existing_build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ] = (),
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        """
        Project exact canonical modules.* configuration files into
        syntax-neutral SOURCE_CONFIG build participation.

        AndroidModelSource does not carry the filesystem metadata object
        directly. Exact physical identity is therefore established by the
        conjunction of:
        - exact owning parser filesystem Extraction artifact identity; and
        - exact canonical Android-visible source path.

        Artifact Universe already guarantees exactly one canonical Artifact
        requirement for every regular file.
        """

        if not isinstance(
            kernel_module_requirement,
            AndroidUniverseKernelModuleRequirement,
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement"
            )

        requirements = getattr(
            artifact_requirements,
            "requirements",
            None,
        )

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "artifact_requirements must expose tuple requirements"
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

        artifact_requirement_by_id = {
            requirement.requirement_id: requirement
            for requirement
            in requirements
        }

        if len(
            artifact_requirement_by_id
        ) != len(
            requirements
        ):
            raise ValueError(
                "canonical Artifact requirement IDs must be unique"
            )

        represented_artifact_ids = {
            value
            for representation
            in existing_build_representations
            for value in (
                representation.preserved_artifact_id,
                representation.canonical_requirement_id,
            )
            if value in artifact_requirement_by_id
        }

        projected = []

        for configuration in (
            kernel_module_requirement.configuration_requirements
        ):
            model_source = (
                configuration.source.source
            )

            artifact_requirement = (
                configuration.artifact_requirement
            )

            canonical = (
                artifact_requirement_by_id.get(
                    artifact_requirement.requirement_id
                )
            )

            if canonical is None:
                raise ValueError(
                    "kernel-module configuration lost its canonical "
                    "Artifact requirement before Reconstruction: "
                    f"source={model_source.identity_key!r}"
                )

            if canonical is not artifact_requirement:
                raise ValueError(
                    "kernel-module configuration Artifact requirement "
                    "identity changed before Reconstruction"
                )

            if (
                artifact_requirement.requirement_id
                in represented_artifact_ids
            ):
                continue

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:kernel-module-config:"
                        f"{artifact_requirement.requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .SOURCE_CONFIG
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=(
                        "kernel-module-config:"
                        f"{model_source.source_name}:"
                        f"{model_source.android_path.as_posix()}"
                    ),
                    canonical_requirement_id=(
                        artifact_requirement.requirement_id
                    ),
                    installed_partition=(
                        artifact_requirement.partition_name
                    ),
                    installed_android_path=(
                        artifact_requirement.android_path
                    ),
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Kernel Module configuration and Artifact "
                        "evidence proves exact modules.* configuration build "
                        "participation and installed identity, but generic "
                        "Reconstruction does not choose source-tree placement "
                        "or Make/Soong materialization syntax."
                    ),
                )
            )

            represented_artifact_ids.add(
                artifact_requirement.requirement_id
            )

        result = tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        canonical_ids = tuple(
            representation.canonical_requirement_id
            for representation
            in result
        )

        if len(
            canonical_ids
        ) != len(
            set(canonical_ids)
        ):
            raise ValueError(
                "kernel-module configuration projection created duplicate "
                "canonical Artifact participation"
            )

        return result

    @staticmethod
    def apply_hard_dependencies(
        kernel_module_requirement: AndroidUniverseKernelModuleRequirement,
        artifact_requirements,
        *,
        build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        if not isinstance(
            kernel_module_requirement,
            AndroidUniverseKernelModuleRequirement,
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement"
            )

        requirements = getattr(
            artifact_requirements,
            "requirements",
            None,
        )

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "artifact_requirements must expose tuple requirements"
            )

        artifact_by_identity = {
            requirement.identity_key: requirement
            for requirement
            in requirements
        }

        artifact_requirement_by_id = {
            requirement.requirement_id: requirement
            for requirement
            in requirements
        }

        representation_by_id = {
            representation.representation_id: representation
            for representation
            in build_representations
        }

        if len(
            representation_by_id
        ) != len(
            build_representations
        ):
            raise ValueError(
                "Build-System representation identities must be unique"
            )

        representation_id_by_artifact_requirement_id = {}

        for representation in build_representations:
            artifact_requirement_id = (
                representation.preserved_artifact_id
                or representation.canonical_requirement_id
            )

            if (
                artifact_requirement_id
                not in artifact_requirement_by_id
            ):
                continue

            existing = (
                representation_id_by_artifact_requirement_id.get(
                    artifact_requirement_id
                )
            )

            if (
                existing is not None
                and existing != representation.representation_id
            ):
                raise ValueError(
                    "one canonical Artifact is represented by multiple "
                    "physical Build-System representations"
                )

            representation_id_by_artifact_requirement_id[
                artifact_requirement_id
            ] = representation.representation_id

        representation_id_by_module_object_id = {}

        for module in (
            kernel_module_requirement.module_requirements
        ):
            identity_key = (
                AndroidReconstructionKernelModuleBuildProjector
                ._module_artifact_identity(
                    module
                )
            )

            artifact_requirement = (
                artifact_by_identity.get(
                    identity_key
                )
            )

            if artifact_requirement is None:
                raise ValueError(
                    "canonical kernel module has no exact Artifact "
                    "requirement during dependency projection"
                )

            representation_id = (
                representation_id_by_artifact_requirement_id.get(
                    artifact_requirement.requirement_id
                )
            )

            if representation_id is None:
                raise ValueError(
                    "canonical kernel module has no physical "
                    "Build-System representation"
                )

            representation_id_by_module_object_id[
                id(module)
            ] = representation_id

        additions_by_owner_id: dict[
            str,
            set[str],
        ] = {}

        for dependency in (
            kernel_module_requirement.hard_dependencies
        ):
            owner_id = (
                representation_id_by_module_object_id.get(
                    id(dependency.owner)
                )
            )

            dependency_id = (
                representation_id_by_module_object_id.get(
                    id(dependency.dependency)
                )
            )

            if (
                owner_id is None
                or dependency_id is None
            ):
                raise ValueError(
                    "modules.dep edge lost exact physical "
                    "Build-System representation identity"
                )

            if owner_id == dependency_id:
                continue

            additions_by_owner_id.setdefault(
                owner_id,
                set(),
            ).add(
                dependency_id
            )

        projected = []

        for representation in build_representations:
            additions = (
                additions_by_owner_id.get(
                    representation.representation_id,
                    set(),
                )
            )

            if not additions:
                projected.append(
                    representation
                )
                continue

            projected.append(
                replace(
                    representation,
                    dependency_ids=tuple(
                        sorted(
                            {
                                *representation.dependency_ids,
                                *additions,
                            }
                        )
                    ),
                )
            )

        result = tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        result_ids = {
            representation.representation_id
            for representation
            in result
        }

        for representation in result:
            missing = (
                set(representation.dependency_ids)
                - result_ids
            )

            if missing:
                raise ValueError(
                    "kernel-module build dependency references missing "
                    "Build-System representation identities"
                )

        return result
