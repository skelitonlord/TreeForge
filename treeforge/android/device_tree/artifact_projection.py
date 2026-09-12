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
from treeforge.android.reconstruction_ownership.model import (
    AndroidReconstructionOwnershipDomain,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDeploymentRole,
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeArtifactProjection:
    """
    One exact preserved Artifact -> generated proprietary source-tree path.

    The generated proprietary path is TreeForge-owned source layout.
    ``installed_partition`` and ``installed_android_path`` remain canonical
    observed runtime destination evidence and are not treated as evidence of
    the OEM's original repository layout.
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
            (
                "artifact_id",
                self.artifact_id,
            ),
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "installed_partition",
                self.installed_partition,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "artifact destination must be relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "artifact destination must not escape "
                "the Device Tree workspace"
            )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if (
            "/"
            in self.installed_partition
            or "\\"
            in self.installed_partition
            or self.installed_partition
            in {
                ".",
                "..",
            }
        ):
            raise ValueError(
                "installed_partition must be one "
                "safe path component"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
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
            != self.artifact_id
        ):
            raise ValueError(
                "artifact projection must preserve exact "
                "Universe artifact identity"
            )

        if (
            self.build_representation
            .preserved_artifact_id
            != self.artifact_id
        ):
            raise ValueError(
                "artifact projection must preserve exact "
                "Build-System artifact identity"
            )

        if (
            self.build_representation
            .representation_id
            != self.representation_id
        ):
            raise ValueError(
                "artifact projection representation identity mismatch"
            )

        if (
            self.build_representation
            .installed_partition
            != self.installed_partition
        ):
            raise ValueError(
                "artifact projection changed installed partition"
            )

        if (
            self.build_representation
            .installed_android_path
            != self.installed_android_path
        ):
            raise ValueError(
                "artifact projection changed installed Android path"
            )


class AndroidDeviceTreeArtifactProjector:
    """
    Project canonical preserved artifacts into deterministic TreeForge
    proprietary source layout.

    Ownership is consumed from the exact first-class Planning Ownership result.
    Payload location is resolved only through the exact canonical filesystem
    metadata inventory entry.
    """

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
    ) -> tuple[
        AndroidDeviceTreeArtifactProjection,
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
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        ownership = (
            reconstruction
            .reconstruction_input
            .plan
            .ownership
        )

        if ownership is None:
            raise ValueError(
                "preserved Artifact Device Tree projection "
                "requires first-class Reconstruction Ownership"
            )

        build_by_artifact_id = {}

        for representation in (
            reconstruction
            .artifact_build_representations
        ):
            artifact_id = (
                representation
                .preserved_artifact_id
            )

            #
            # Device Tree artifact projection owns only exact preserved
            # canonical Artifact payloads. Reconstruction now also exposes
            # requirement-backed and source-content-backed physical build
            # representations through the same global build population.
            # Those representations belong to their own Device Tree
            # projectors and must not be mistaken for preserved Artifacts.
            #
            if artifact_id is None:
                continue

            if artifact_id in build_by_artifact_id:
                raise ValueError(
                    "multiple Build-System representations "
                    "claim one preserved Artifact identity"
                )

            build_by_artifact_id[
                artifact_id
            ] = representation

        #
        # Finalized Reconstruction build participation is authoritative for
        # the physical preserved-Artifact population.
        #
        # Reconstruction work_items describe execution work and are no
        # longer guaranteed to contain the complete preserved payload
        # population after Build-System Reconstruction has projected the
        # canonical physical roles.
        #
        # preserved_artifact_id is the exact payload identity contract.
        #
        artifact_backed_representations = tuple(
            sorted(
                build_by_artifact_id.values(),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        projected = []

        seen_artifact_ids = set()
        seen_destinations = set()

        for build_representation in (
            artifact_backed_representations
        ):
            artifact_id = (
                build_representation
                .preserved_artifact_id
            )

            if artifact_id is None:
                raise ValueError(
                    "preserved-backed Device Tree projection "
                    "lost exact Artifact identity"
                )

            if artifact_id in seen_artifact_ids:
                raise ValueError(
                    "duplicate preserved Artifact projection identity"
                )

            ownership_decision = (
                ownership.decision_for(
                    requirement_kind="artifact",
                    source_identity=artifact_id,
                )
            )

            if ownership_decision is None:
                raise ValueError(
                    "preserved Artifact has no Ownership decision: "
                    f"{artifact_id}"
                )

            requirement = (
                ownership_decision.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise TypeError(
                    "preserved Artifact Ownership must retain an "
                    "AndroidUniverseArtifactRequirement"
                )

            if (
                requirement.requirement_id
                != artifact_id
            ):
                raise ValueError(
                    "Artifact Ownership changed exact canonical "
                    "Artifact identity"
                )

            if (
                requirement.disposition
                is not AndroidUniverseArtifactDisposition
                .PRESERVE
            ):
                raise ValueError(
                    "preserved-backed Build-System representation "
                    "must retain Universe PRESERVE disposition"
                )

            if (
                ownership_decision.domain
                is not AndroidReconstructionOwnershipDomain
                .PROPRIETARY
            ):
                raise ValueError(
                    "preserved Artifact Device Tree projection "
                    "requires PROPRIETARY ownership"
                )

            if (
                requirement.deployment_role
                is not AndroidUniverseArtifactDeploymentRole
                .DIRECT_PARTITION
            ):
                continue

            from treeforge.android.device_tree.preserved_artifact_policy import (
                preserved_artifact_requires_source_materialization,
            )

            if not preserved_artifact_requires_source_materialization(
                requirement
            ):
                continue

            installed_partition = (
                build_representation
                .installed_partition
            )

            installed_android_path = (
                build_representation
                .installed_android_path
            )

            if (
                installed_partition is None
                or installed_android_path is None
            ):
                raise ValueError(
                    "preserved Artifact Build-System representation "
                    "must retain installed partition/path: "
                    f"{artifact_id}"
                )

            if (
                installed_partition
                != requirement.partition_name
                or installed_android_path
                != requirement.android_path
            ):
                raise ValueError(
                    "Artifact Build-System representation changed "
                    "canonical runtime destination evidence"
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

            relative_android_path = (
                PurePosixPath(
                    *android_path.parts[1:]
                )
            )

            if not relative_android_path.parts:
                raise ValueError(
                    "preserved Artifact cannot represent "
                    "a partition root"
                )

            destination = PurePosixPath(
                (
                    identity.proprietary_root
                    / installed_partition
                    / Path(
                        relative_android_path
                        .as_posix()
                    )
                ).as_posix()
            )

            destination_id = (
                destination.as_posix()
            )

            if destination_id in seen_destinations:
                raise ValueError(
                    "multiple preserved Artifacts project to "
                    "one proprietary source-tree path: "
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
                AndroidDeviceTreeArtifactProjection(
                    artifact_id=artifact_id,
                    representation_id=(
                        build_representation
                        .representation_id
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
                    build_representation=(
                        build_representation
                    ),
                )
            )

            seen_artifact_ids.add(
                artifact_id
            )

            seen_destinations.add(
                destination_id
            )

        expected_artifact_ids = set()

        for build_representation in (
            artifact_backed_representations
        ):
            artifact_id = (
                build_representation
                .preserved_artifact_id
            )

            if artifact_id is None:
                raise ValueError(
                    "preserved-backed Device Tree coverage "
                    "lost exact Artifact identity"
                )

            ownership_decision = (
                ownership.decision_for(
                    requirement_kind="artifact",
                    source_identity=artifact_id,
                )
            )

            if ownership_decision is None:
                raise ValueError(
                    "preserved Artifact has no Ownership decision "
                    "during coverage validation: "
                    f"{artifact_id}"
                )

            requirement = (
                ownership_decision.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise TypeError(
                    "Artifact Ownership coverage must retain an "
                    "AndroidUniverseArtifactRequirement"
                )

            if (
                requirement.requirement_id
                != artifact_id
            ):
                raise ValueError(
                    "Artifact Ownership coverage changed exact "
                    "canonical Artifact identity"
                )

            if (
                requirement.deployment_role
                is AndroidUniverseArtifactDeploymentRole
                .DIRECT_PARTITION
            ):
                from treeforge.android.device_tree.preserved_artifact_policy import (
                    preserved_artifact_requires_source_materialization,
                )

                if preserved_artifact_requires_source_materialization(
                    requirement
                ):
                    expected_artifact_ids.add(
                        artifact_id
                    )

        if seen_artifact_ids != expected_artifact_ids:
            missing = sorted(
                expected_artifact_ids
                - seen_artifact_ids
            )

            unexpected = sorted(
                seen_artifact_ids
                - expected_artifact_ids
            )

            raise ValueError(
                "Device Tree Artifact projection coverage mismatch: "
                f"missing={len(missing)}, "
                f"unexpected={len(unexpected)}"
            )

        return tuple(
            sorted(
                projected,
                key=lambda projection: (
                    projection
                    .destination
                    .as_posix(),
                    projection.artifact_id,
                ),
            )
        )
