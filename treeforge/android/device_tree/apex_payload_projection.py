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
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeApexPayloadProjection:
    """
    One exact root-runtime canonical APEX container projected into the
    deterministic TreeForge proprietary source layout.

    APEX is deliberately separate from generic Artifact physical-payload
    projection because AndroidUniverseApexRequirement is its own canonical
    family.

    Nested-runtime APEXes remain owned by their enclosing runtime/container
    and are intentionally not independently materialized into the root
    device tree.
    """

    requirement_id: str
    representation_id: str

    destination: PurePosixPath

    installed_partition: str
    installed_android_path: str

    source_path: Path

    requirement: AndroidUniverseApexRequirement
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

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "APEX payload destination must be relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "APEX payload destination must not escape "
                "the Device Tree workspace"
            )

        if not self.installed_android_path.startswith("/"):
            raise ValueError(
                "installed_android_path must be absolute"
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
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseApexRequirement"
            )

        if not isinstance(
            self.build_representation,
            AndroidReconstructionBuildRepresentation,
        ):
            raise TypeError(
                "build_representation must be an "
                "AndroidReconstructionBuildRepresentation"
            )

        if not self.requirement.runtime_context.is_root:
            raise ValueError(
                "APEX payload projection requires a root-runtime APEX"
            )

        if (
            self.requirement.requirement_id
            != self.requirement_id
        ):
            raise ValueError(
                "APEX payload projection changed exact "
                "canonical requirement identity"
            )

        if (
            self.build_representation.canonical_requirement_id
            != self.requirement_id
        ):
            raise ValueError(
                "APEX payload projection changed Reconstruction "
                "canonical requirement identity"
            )

        if (
            self.build_representation.representation_id
            != self.representation_id
        ):
            raise ValueError(
                "APEX payload projection changed Reconstruction "
                "representation identity"
            )

        if (
            self.build_representation.installed_partition
            != self.installed_partition
        ):
            raise ValueError(
                "APEX payload projection changed canonical "
                "installed partition"
            )

        if (
            self.build_representation.installed_android_path
            != self.installed_android_path
        ):
            raise ValueError(
                "APEX payload projection changed canonical "
                "installed Android path"
            )

        if (
            self.source_path
            != self.requirement.artifact.path
        ):
            raise ValueError(
                "APEX payload projection changed exact "
                "Extraction artifact path"
            )


class AndroidDeviceTreeApexPayloadProjector:
    """
    Project exact root-runtime canonical APEX containers.

    Requirement identity is joined only through Reconstruction's retained
    canonical requirement graph. No filename scan, package-name lookup, or
    filesystem rediscovery is performed here.
    """

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
    ) -> tuple[
        AndroidDeviceTreeApexPayloadProjection,
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

        obligations = (
            reconstruction
            .reconstruction_input
            .plan
            .obligations
        )

        requirement_by_id = {}

        for obligation in obligations:
            requirement = obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            ):
                continue

            requirement_id = (
                requirement.requirement_id
            )

            existing = requirement_by_id.get(
                requirement_id
            )

            if (
                existing is not None
                and existing is not requirement
            ):
                raise ValueError(
                    "multiple canonical APEX requirement objects "
                    "claim one requirement_id: "
                    f"{requirement_id}"
                )

            requirement_by_id[
                requirement_id
            ] = requirement

        apex_representations = tuple(
            representation
            for representation
            in reconstruction.artifact_build_representations
            if (
                representation.kind
                is AndroidReconstructionBuildRepresentationKind
                .APEX
            )
        )

        projected = []

        seen_representation_ids = set()
        seen_requirement_ids = set()
        seen_destinations = set()

        nested_representation_ids = set()

        for representation in apex_representations:
            requirement_id = (
                representation.canonical_requirement_id
            )

            if requirement_id is None:
                raise ValueError(
                    "APEX representation requires canonical "
                    "requirement identity: "
                    f"{representation.representation_id}"
                )

            requirement = requirement_by_id.get(
                requirement_id
            )

            if not isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            ):
                raise ValueError(
                    "APEX representation does not resolve to an "
                    "exact canonical APEX requirement: "
                    f"{representation.representation_id}"
                )

            if not requirement.runtime_context.is_root:
                nested_representation_ids.add(
                    representation.representation_id
                )
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
                    "root-runtime APEX representation must retain "
                    "installed partition/path: "
                    f"{representation.representation_id}"
                )

            android_path = PurePosixPath(
                installed_android_path
            )

            if not android_path.is_absolute():
                raise ValueError(
                    "canonical APEX installed Android path "
                    "must be absolute"
                )

            if ".." in android_path.parts:
                raise ValueError(
                    "canonical APEX installed Android path "
                    "must not contain parent traversal"
                )

            relative_android_path = PurePosixPath(
                *android_path.parts[1:]
            )

            if not relative_android_path.parts:
                raise ValueError(
                    "APEX payload cannot represent a partition root"
                )

            installed_suffix = (
                android_path.suffix.lower()
            )

            source_artifact = (
                requirement.artifact
            )

            if installed_suffix == ".apex":
                build_relative_android_path = (
                    relative_android_path
                )

            elif installed_suffix == ".capex":
                #
                # Parsing follows canonical recursive Extraction lineage.
                #
                # For a compressed APEX, the parsed/Universe APEX artifact
                # is therefore the exact extracted `original_apex`, while
                # deployment_context independently retains the enclosing
                # factory .capex installed path.
                #
                # Device Tree may use that exact uncompressed APEX as its
                # prebuilt_apex build payload. It must not rename the outer
                # CAPEX bytes or independently decompress/reparse anything.
                #
                if (
                    source_artifact.semantic_name
                    != "original_apex"
                ):
                    raise ValueError(
                        "root-runtime CAPEX must resolve to the "
                        "canonical Extraction original_apex artifact: "
                        f"{representation.representation_id}"
                    )

                archive_member = (
                    source_artifact.fact(
                        "archive_member"
                    )
                )

                if (
                    archive_member is None
                    or archive_member.value
                    != "original_apex"
                ):
                    raise ValueError(
                        "root-runtime CAPEX original_apex artifact "
                        "must retain exact Extraction archive-member "
                        "evidence: "
                        f"{representation.representation_id}"
                    )

                build_relative_android_path = (
                    relative_android_path.with_suffix(
                        ".apex"
                    )
                )

            else:
                raise ValueError(
                    "root-runtime APEX has unsupported canonical "
                    "installed container suffix: "
                    f"{installed_android_path!r}"
                )

            destination = PurePosixPath(
                (
                    identity.proprietary_root
                    / installed_partition
                    / Path(
                        build_relative_android_path.as_posix()
                    )
                ).as_posix()
            )

            destination_id = (
                destination.as_posix()
            )

            source_path = (
                source_artifact.path
            )

            if not isinstance(
                source_path,
                Path,
            ):
                raise TypeError(
                    "canonical APEX Extraction artifact path "
                    "must be a Path"
                )

            if (
                representation.representation_id
                in seen_representation_ids
            ):
                raise ValueError(
                    "duplicate APEX payload representation projection"
                )

            if requirement_id in seen_requirement_ids:
                raise ValueError(
                    "multiple APEX representations claim one "
                    "canonical payload: "
                    f"{requirement_id}"
                )

            if destination_id in seen_destinations:
                raise ValueError(
                    "multiple root-runtime APEX requirements project "
                    "to one Device Tree source path: "
                    f"{destination_id}"
                )

            projected.append(
                AndroidDeviceTreeApexPayloadProjection(
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

        expected_root_ids = {
            representation.representation_id
            for representation
            in apex_representations
            if (
                isinstance(
                    requirement_by_id.get(
                        representation.canonical_requirement_id
                    ),
                    AndroidUniverseApexRequirement,
                )
                and requirement_by_id[
                    representation.canonical_requirement_id
                ].runtime_context.is_root
            )
        }

        expected_nested_ids = {
            representation.representation_id
            for representation
            in apex_representations
            if (
                isinstance(
                    requirement_by_id.get(
                        representation.canonical_requirement_id
                    ),
                    AndroidUniverseApexRequirement,
                )
                and not requirement_by_id[
                    representation.canonical_requirement_id
                ].runtime_context.is_root
            )
        }

        if seen_representation_ids != expected_root_ids:
            raise ValueError(
                "Device Tree root-runtime APEX payload "
                "projection coverage mismatch"
            )

        if nested_representation_ids != expected_nested_ids:
            raise ValueError(
                "Device Tree nested-runtime APEX exclusion "
                "coverage mismatch"
            )

        if (
            len(expected_root_ids)
            + len(expected_nested_ids)
            != len(apex_representations)
        ):
            raise ValueError(
                "Device Tree APEX runtime classification "
                "coverage mismatch"
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
