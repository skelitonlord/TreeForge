from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDeploymentRole,
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVendorKernelRamdiskModuleProjection:
    """
    One exact vendor_kernel_boot .ko exposed as an Android vendor-kernel-
    ramdisk source input.

    This is deliberately distinct from generic preserved Artifact projection:
    the canonical Artifact remains BOOT_FILESYSTEM/container-owned, while the
    kernel family has a proven Android build mechanism that requires the exact
    module as an independent source input.
    """

    artifact_id: str
    representation_id: str

    destination: PurePosixPath

    installed_partition: str
    installed_android_path: str

    source_path: Path

    requirement: AndroidUniverseArtifactRequirement
    build_representation: AndroidReconstructionBuildRepresentation

    def __post_init__(self) -> None:
        for field_name, value in (
            ("artifact_id", self.artifact_id),
            ("representation_id", self.representation_id),
            ("installed_partition", self.installed_partition),
            ("installed_android_path", self.installed_android_path),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(self.destination, PurePosixPath):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "destination must be Device Tree relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape Device Tree workspace"
            )

        if self.destination.suffix != ".ko":
            raise ValueError(
                "vendor kernel ramdisk projection must target .ko"
            )

        if self.installed_partition != "vendor_kernel_boot":
            raise ValueError(
                "vendor kernel ramdisk module must preserve "
                "vendor_kernel_boot canonical partition identity"
            )

        if not self.installed_android_path.startswith("/"):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if not self.installed_android_path.lower().endswith(".ko"):
            raise ValueError(
                "vendor kernel ramdisk installed path must be .ko"
            )

        if not isinstance(self.source_path, Path):
            raise TypeError(
                "source_path must be a Path"
            )

        if not isinstance(
            self.requirement,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseArtifactRequirement"
            )

        if not isinstance(
            self.build_representation,
            AndroidReconstructionBuildRepresentation,
        ):
            raise TypeError(
                "build_representation must be an "
                "AndroidReconstructionBuildRepresentation"
            )

        if self.requirement.requirement_id != self.artifact_id:
            raise ValueError(
                "vendor kernel ramdisk projection changed "
                "canonical Artifact identity"
            )

        if (
            self.build_representation.preserved_artifact_id
            != self.artifact_id
        ):
            raise ValueError(
                "vendor kernel ramdisk projection changed "
                "Reconstruction preserved Artifact identity"
            )

        if (
            self.build_representation.representation_id
            != self.representation_id
        ):
            raise ValueError(
                "vendor kernel ramdisk projection changed "
                "Reconstruction representation identity"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVendorKernelRamdiskPlan:
    """
    Concrete Device Tree plan for the Android vendor kernel ramdisk.

    load_module_names preserves canonical modules.load ordering as installed
    module basenames. Android build/make will regenerate modules.dep, alias,
    and softdep from the supplied exact .ko population.
    """

    module_projections: tuple[
        AndroidDeviceTreeVendorKernelRamdiskModuleProjection,
        ...,
    ]

    load_module_names: tuple[str, ...]

    load_relationship_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.module_projections, tuple):
            raise TypeError(
                "module_projections must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeVendorKernelRamdiskModuleProjection,
            )
            for item in self.module_projections
        ):
            raise TypeError(
                "module_projections contains an invalid model"
            )

        representation_ids = tuple(
            item.representation_id
            for item in self.module_projections
        )

        if len(representation_ids) != len(set(representation_ids)):
            raise ValueError(
                "vendor kernel ramdisk module representation "
                "identities must be unique"
            )

        destinations = tuple(
            item.destination.as_posix()
            for item in self.module_projections
        )

        if len(destinations) != len(set(destinations)):
            raise ValueError(
                "vendor kernel ramdisk source destinations "
                "must be unique"
            )

        if not isinstance(self.load_module_names, tuple):
            raise TypeError(
                "load_module_names must be a tuple"
            )

        if not all(
            isinstance(value, str) and value
            for value in self.load_module_names
        ):
            raise ValueError(
                "load_module_names must contain non-empty strings"
            )

        if not isinstance(
            self.load_relationship_id,
            str,
        ) or not self.load_relationship_id:
            raise ValueError(
                "load_relationship_id must be a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMaterializedVendorKernelRamdiskModule:
    """One exact vendor-kernel-ramdisk module copied by Device Tree."""

    relative_path: Path
    artifact_id: str
    representation_id: str
    source_path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.relative_path, Path):
            raise TypeError(
                "relative_path must be a Path"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in self.relative_path.parts:
            raise ValueError(
                "relative_path must not escape Device Tree workspace"
            )

        if self.relative_path.suffix != ".ko":
            raise ValueError(
                "materialized vendor kernel ramdisk module must be .ko"
            )

        for field_name, value in (
            ("artifact_id", self.artifact_id),
            ("representation_id", self.representation_id),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(self.source_path, Path):
            raise TypeError(
                "source_path must be a Path"
            )


class AndroidDeviceTreeVendorKernelRamdiskProjector:
    """
    Project exact canonical vendor_kernel_boot modules into Android's
    BOARD_VENDOR_KERNEL_RAMDISK_KERNEL_MODULES source surface.
    """

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
    ) -> AndroidDeviceTreeVendorKernelRamdiskPlan:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an AndroidReconstructionResult"
            )

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an AndroidDeviceTreeIdentity"
            )

        ownership = (
            reconstruction
            .reconstruction_input
            .plan
            .ownership
        )

        if ownership is None:
            raise ValueError(
                "vendor kernel ramdisk projection requires "
                "first-class Reconstruction Ownership"
            )

        module_representations = tuple(
            representation
            for representation
            in reconstruction.artifact_build_representations
            if (
                representation.kind
                is AndroidReconstructionBuildRepresentationKind
                .KERNEL_MODULE
                and representation.installed_partition
                == "vendor_kernel_boot"
            )
        )

        projected = []
        seen_artifact_ids = set()
        seen_destinations = set()

        for representation in module_representations:
            artifact_id = representation.preserved_artifact_id

            if artifact_id is None:
                raise ValueError(
                    "vendor_kernel_boot KERNEL_MODULE must be "
                    "preserved Artifact-backed: "
                    f"{representation.representation_id}"
                )

            ownership_decision = ownership.decision_for(
                requirement_kind="artifact",
                source_identity=artifact_id,
            )

            if ownership_decision is None:
                raise ValueError(
                    "vendor_kernel_boot module has no Artifact "
                    "Ownership decision: "
                    f"{artifact_id}"
                )

            requirement = ownership_decision.requirement

            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise TypeError(
                    "vendor_kernel_boot module Ownership must retain "
                    "AndroidUniverseArtifactRequirement"
                )

            if requirement.requirement_id != artifact_id:
                raise ValueError(
                    "vendor kernel ramdisk projection changed "
                    "canonical Artifact identity"
                )

            if (
                requirement.disposition
                is not AndroidUniverseArtifactDisposition.PRESERVE
            ):
                raise ValueError(
                    "vendor_kernel_boot module must retain "
                    "PRESERVE disposition"
                )

            if (
                requirement.deployment_role
                is not AndroidUniverseArtifactDeploymentRole
                .BOOT_FILESYSTEM
            ):
                raise ValueError(
                    "vendor_kernel_boot module must retain "
                    "BOOT_FILESYSTEM deployment role"
                )

            if requirement.partition_name != "vendor_kernel_boot":
                raise ValueError(
                    "vendor kernel ramdisk module changed "
                    "canonical partition identity"
                )

            installed_android_path = (
                representation.installed_android_path
            )

            if installed_android_path is None:
                raise ValueError(
                    "vendor_kernel_boot module requires installed path"
                )

            installed = PurePosixPath(installed_android_path)

            if (
                not installed.is_absolute()
                or installed.suffix != ".ko"
            ):
                raise ValueError(
                    "vendor_kernel_boot module must retain an "
                    "absolute installed .ko path"
                )

            relative_installed = PurePosixPath(
                *installed.parts[1:]
            )

            destination = PurePosixPath(
                (
                    identity.proprietary_root
                    / "vendor_kernel_ramdisk"
                    / Path(relative_installed.as_posix())
                ).as_posix()
            )

            source_path = (
                requirement
                .inventory_entry
                .materialized_path(
                    requirement.metadata_entry
                )
            )

            if not isinstance(source_path, Path):
                raise TypeError(
                    "canonical Artifact materialized_path "
                    "must return a Path"
                )

            if artifact_id in seen_artifact_ids:
                raise ValueError(
                    "duplicate vendor kernel ramdisk Artifact identity"
                )

            destination_id = destination.as_posix()

            if destination_id in seen_destinations:
                raise ValueError(
                    "multiple vendor kernel ramdisk modules project "
                    "to one source destination"
                )

            projected.append(
                AndroidDeviceTreeVendorKernelRamdiskModuleProjection(
                    artifact_id=artifact_id,
                    representation_id=(
                        representation.representation_id
                    ),
                    destination=destination,
                    installed_partition=(
                        representation.installed_partition
                    ),
                    installed_android_path=(
                        installed_android_path
                    ),
                    source_path=source_path,
                    requirement=requirement,
                    build_representation=representation,
                )
            )

            seen_artifact_ids.add(artifact_id)
            seen_destinations.add(destination_id)

        #
        # First-stage load order is already canonical Universe semantics.
        #
        # Planning preserves the exact cross-family relationship objects for
        # Reconstruction. Device Tree consumes that established semantic
        # result directly rather than reopening/reinterpreting modules.load.
        #
        from treeforge.android.universe.relationships.model import (
            AndroidUniverseFirstStageKernelModuleLoadingRelationship,
        )

        first_stage_relationships = tuple(
            relationship
            for relationship
            in reconstruction.reconstruction_input.plan
            .cross_family_relationships
            if isinstance(
                relationship,
                AndroidUniverseFirstStageKernelModuleLoadingRelationship,
            )
        )

        if not first_stage_relationships:
            raise ValueError(
                "vendor kernel ramdisk realization requires a canonical "
                "first-stage kernel-module-loading relationship"
            )

        unresolved_first_stage_relationships = tuple(
            relationship
            for relationship
            in first_stage_relationships
            if relationship.status.value != "resolved"
        )

        if unresolved_first_stage_relationships:
            raise ValueError(
                "vendor kernel ramdisk realization requires only "
                "resolved first-stage kernel-module-loading relationships"
            )

        #
        # More than one Boot policy may point at the same canonical
        # vendor_kernel_boot modules.load population. That is legitimate.
        # Every relationship must preserve the exact same ordered load-entry
        # identities; otherwise Device Tree would face an unresolved build
        # ambiguity and must not choose between them.
        #
        canonical_relationship = first_stage_relationships[0]

        canonical_load_entry_ids = tuple(
            id(entry)
            for entry
            in canonical_relationship.load_entries
        )

        for relationship in first_stage_relationships[1:]:
            relationship_load_entry_ids = tuple(
                id(entry)
                for entry
                in relationship.load_entries
            )

            if (
                relationship_load_entry_ids
                != canonical_load_entry_ids
            ):
                raise ValueError(
                    "first-stage kernel-module-loading relationships "
                    "disagree on canonical vendor_kernel_boot load order"
                )

        if not canonical_relationship.load_entries:
            raise ValueError(
                "canonical first-stage kernel-module-loading relationship "
                "has no vendor_kernel_boot load entries"
            )

        sequence_indexes = tuple(
            entry.sequence_index
            for entry
            in canonical_relationship.load_entries
        )

        if sequence_indexes != tuple(
            sorted(sequence_indexes)
        ):
            raise ValueError(
                "canonical first-stage kernel-module-loading relationship "
                "lost modules.load source ordering"
            )

        load_module_names = []

        for entry in canonical_relationship.load_entries:
            module_source = (
                entry.module.source.elf.source
            )

            filesystem_source = (
                module_source.filesystem_source
            )

            if filesystem_source is None:
                raise ValueError(
                    "first-stage kernel module lost canonical "
                    "filesystem source identity"
                )

            if (
                filesystem_source.source_name
                != "vendor_kernel_boot"
            ):
                raise ValueError(
                    "first-stage kernel-module-loading relationship "
                    "contains a non-vendor_kernel_boot module"
                )

            android_path = module_source.android_path

            module_name = PurePosixPath(
                android_path.as_posix()
            ).name

            if not module_name.endswith(".ko"):
                raise ValueError(
                    "first-stage kernel-module-loading relationship "
                    "contains a non-.ko module"
                )

            load_module_names.append(module_name)

        load_module_names = tuple(load_module_names)

        projected_module_names = {
            PurePosixPath(
                item.installed_android_path
            ).name
            for item in projected
        }

        missing_load_modules = tuple(
            module_name
            for module_name
            in load_module_names
            if module_name not in projected_module_names
        )

        if missing_load_modules:
            raise ValueError(
                "canonical first-stage load relationship references "
                "modules outside the projected vendor_kernel_boot "
                "population: "
                f"{missing_load_modules[:16]!r}"
            )

        if len(load_module_names) != len(
            canonical_relationship.load_entries
        ):
            raise ValueError(
                "vendor kernel ramdisk load projection changed "
                "canonical first-stage entry count"
            )

        return AndroidDeviceTreeVendorKernelRamdiskPlan(
            module_projections=tuple(
                sorted(
                    projected,
                    key=lambda item: (
                        item.destination.as_posix(),
                        item.artifact_id,
                    ),
                )
            ),
            load_module_names=load_module_names,
            load_relationship_id=(
                canonical_relationship.relationship_id
            ),
        )
