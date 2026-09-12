from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDeploymentRole,
    AndroidUniverseArtifactRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePhysicalPayloadProjection:
    """
    One exact requirement-backed canonical filesystem Artifact projected into
    deterministic TreeForge-owned proprietary source layout.

    This is distinct from preserved-artifact projection.

    ``canonical_requirement_id`` remains the Reconstruction payload identity.
    Device Tree merely proves that the referenced canonical requirement is an
    exact AndroidUniverseArtifactRequirement whose deployment role permits an
    independent source-tree payload.

    The installed partition/path remain observed runtime destination evidence;
    they are not evidence of the OEM's original repository layout.
    """

    requirement_id: str
    representation_id: str

    destination: PurePosixPath

    installed_partition: str
    installed_android_path: str

    source_path: Path

    requirement: AndroidUniverseArtifactRequirement
    build_representation: AndroidReconstructionBuildRepresentation

    def __post_init__(self) -> None:
        for field_name, value in (
            ("requirement_id", self.requirement_id),
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
                "physical payload destination must be relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "physical payload destination must not escape "
                "the Device Tree workspace"
            )

        if not self.installed_android_path.startswith("/"):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if (
            "/" in self.installed_partition
            or "\\" in self.installed_partition
            or self.installed_partition in {".", ".."}
        ):
            raise ValueError(
                "installed_partition must be one safe path component"
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

        if (
            self.requirement.requirement_id
            != self.requirement_id
        ):
            raise ValueError(
                "physical payload projection changed exact "
                "canonical requirement identity"
            )

        if (
            self.build_representation
            .canonical_requirement_id
            != self.requirement_id
        ):
            raise ValueError(
                "physical payload projection changed exact "
                "Reconstruction canonical requirement identity"
            )

        if (
            self.build_representation.representation_id
            != self.representation_id
        ):
            raise ValueError(
                "physical payload projection representation "
                "identity mismatch"
            )

        if (
            self.requirement.deployment_role
            is not AndroidUniverseArtifactDeploymentRole
            .DIRECT_PARTITION
        ):
            raise ValueError(
                "physical payload projection requires "
                "DIRECT_PARTITION deployment"
            )

        if (
            self.requirement.partition_name
            != self.installed_partition
        ):
            raise ValueError(
                "physical payload projection changed "
                "canonical partition identity"
            )

        if (
            self.requirement.android_path
            != self.installed_android_path
        ):
            raise ValueError(
                "physical payload projection changed "
                "canonical Android path"
            )

        if (
            self.build_representation.installed_partition
            != self.installed_partition
        ):
            raise ValueError(
                "physical payload projection changed "
                "Reconstruction installed partition"
            )

        if (
            self.build_representation.installed_android_path
            != self.installed_android_path
        ):
            raise ValueError(
                "physical payload projection changed "
                "Reconstruction installed Android path"
            )


class AndroidDeviceTreePhysicalPayloadProjector:
    """
    Project exact requirement-backed DIRECT_PARTITION Artifact payloads.

    Reconstruction's ``canonical_requirement_id`` is intentionally generic,
    so Device Tree must resolve it against the exact canonical requirement
    objects retained in Reconstruction Planning.

    Only IDs whose exact object is an AndroidUniverseArtifactRequirement are
    eligible here.

    DIRECT_PARTITION Artifact requirements are independently source-tree
    installable.

    BOOT_FILESYSTEM and NESTED_FILESYSTEM requirements remain owned by their
    physical containers and are intentionally excluded.

    Non-Artifact canonical requirements such as APEX, boot, DTBO, and VBMeta
    are also intentionally excluded.
    """

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
    ) -> tuple[
        AndroidDeviceTreePhysicalPayloadProjection,
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

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an AndroidDeviceTreeIdentity"
            )

        obligations = (
            reconstruction
            .reconstruction_input
            .plan
            .obligations
        )

        requirement_by_id = {}

        for obligation in obligations:
            requirement = obligation.requirement

            requirement_id = getattr(
                requirement,
                "requirement_id",
                None,
            )

            if requirement_id is None:
                continue

            existing = requirement_by_id.get(
                requirement_id
            )

            if (
                existing is not None
                and existing is not requirement
            ):
                raise ValueError(
                    "multiple canonical requirement objects claim "
                    "one requirement_id: "
                    f"{requirement_id}"
                )

            requirement_by_id[
                requirement_id
            ] = requirement

        projected = []

        seen_representation_ids = set()
        seen_requirement_ids = set()
        seen_destinations = set()

        for representation in (
            reconstruction.artifact_build_representations
        ):
            requirement_id = (
                representation.canonical_requirement_id
            )

            if requirement_id is None:
                continue

            requirement = requirement_by_id.get(
                requirement_id
            )

            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                continue

            deployment_role = (
                requirement.deployment_role
            )

            if deployment_role in {
                AndroidUniverseArtifactDeploymentRole
                .BOOT_FILESYSTEM,
                AndroidUniverseArtifactDeploymentRole
                .NESTED_FILESYSTEM,
            }:
                continue

            if (
                deployment_role
                is AndroidUniverseArtifactDeploymentRole
                .ALTERNATIVE_PARTITION
            ):
                continue

            if (
                deployment_role
                is not AndroidUniverseArtifactDeploymentRole
                .DIRECT_PARTITION
            ):
                raise ValueError(
                    "unsupported requirement-backed physical "
                    "Artifact deployment role: "
                    f"{deployment_role.value}"
                )

            from treeforge.android.device_tree.preserved_artifact_policy import (
                canonical_artifact_requires_source_materialization,
            )

            if not canonical_artifact_requires_source_materialization(
                requirement
            ):
                continue

            installed_partition = (
                representation.installed_partition
            )

            installed_android_path = (
                representation.installed_android_path
            )

            if (
                installed_partition is None
                or installed_android_path is None
            ):
                raise ValueError(
                    "requirement-backed DIRECT_PARTITION build "
                    "representation must retain installed "
                    "partition/path: "
                    f"{representation.representation_id}"
                )

            if (
                requirement.partition_name
                != installed_partition
                or requirement.android_path
                != installed_android_path
            ):
                raise ValueError(
                    "requirement-backed physical payload changed "
                    "canonical installed identity: "
                    f"{representation.representation_id}"
                )

            android_path = PurePosixPath(
                installed_android_path
            )

            if not android_path.is_absolute():
                raise ValueError(
                    "canonical installed Android path "
                    "must be absolute"
                )

            if ".." in android_path.parts:
                raise ValueError(
                    "canonical installed Android path "
                    "must not contain parent traversal"
                )

            relative_android_path = PurePosixPath(
                *android_path.parts[1:]
            )

            if not relative_android_path.parts:
                raise ValueError(
                    "physical payload cannot represent "
                    "a partition root"
                )

            destination = PurePosixPath(
                (
                    identity.proprietary_root
                    / installed_partition
                    / Path(
                        relative_android_path.as_posix()
                    )
                ).as_posix()
            )

            destination_id = (
                destination.as_posix()
            )

            if (
                representation.representation_id
                in seen_representation_ids
            ):
                raise ValueError(
                    "duplicate physical payload "
                    "representation projection"
                )

            if requirement_id in seen_requirement_ids:
                raise ValueError(
                    "multiple requirement-backed representations "
                    "claim one physical Artifact payload: "
                    f"{requirement_id}"
                )

            if destination_id in seen_destinations:
                raise ValueError(
                    "multiple requirement-backed physical "
                    "Artifacts project to one source-tree path: "
                    f"{destination_id}"
                )

            source_path = (
                requirement
                .inventory_entry
                .materialized_path(
                    requirement.metadata_entry
                )
            )

            if not isinstance(
                source_path,
                Path,
            ):
                raise TypeError(
                    "canonical Artifact materialized_path "
                    "must return a Path"
                )

            projected.append(
                AndroidDeviceTreePhysicalPayloadProjection(
                    requirement_id=requirement_id,
                    representation_id=(
                        representation.representation_id
                    ),
                    destination=destination,
                    installed_partition=(
                        installed_partition
                    ),
                    installed_android_path=(
                        installed_android_path
                    ),
                    source_path=source_path,
                    requirement=requirement,
                    build_representation=representation,
                )
            )

            seen_representation_ids.add(
                representation.representation_id
            )

            seen_requirement_ids.add(
                requirement_id
            )

            seen_destinations.add(
                destination_id
            )

        expected_direct_ids = {
            representation.representation_id
            for representation
            in reconstruction.artifact_build_representations
            if (
                representation.canonical_requirement_id
                is not None
                and isinstance(
                    requirement_by_id.get(
                        representation.canonical_requirement_id
                    ),
                    AndroidUniverseArtifactRequirement,
                )
                and (
                    requirement_by_id[
                        representation.canonical_requirement_id
                    ]
                    .deployment_role
                    is AndroidUniverseArtifactDeploymentRole
                    .DIRECT_PARTITION
                )
                and (
                    __import__(
                        "treeforge.android.device_tree."
                        "preserved_artifact_policy",
                        fromlist=[
                            "canonical_artifact_requires_"
                            "source_materialization"
                        ],
                    )
                    .canonical_artifact_requires_source_materialization(
                        requirement_by_id[
                            representation.canonical_requirement_id
                        ]
                    )
                )
            )
        }

        if (
            seen_representation_ids
            != expected_direct_ids
        ):
            missing = sorted(
                expected_direct_ids
                - seen_representation_ids
            )

            unexpected = sorted(
                seen_representation_ids
                - expected_direct_ids
            )

            raise ValueError(
                "Device Tree requirement-backed physical "
                "payload projection coverage mismatch: "
                f"missing={len(missing)}, "
                f"unexpected={len(unexpected)}"
            )

        return tuple(
            sorted(
                projected,
                key=lambda projection: (
                    projection.destination.as_posix(),
                    projection.requirement_id,
                ),
            )
        )
