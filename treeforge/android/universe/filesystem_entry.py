from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
    FilesystemMetadataInventoryEntry,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
)
from treeforge.android.universe.artifact.builder import (
    AndroidUniverseArtifactRequirementBuilder,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDeploymentRole,
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


class AndroidUniverseFilesystemEntryDisposition(
    StrEnum,
):
    """
    Device-level disposition of one exact canonical filesystem entry.

    This is deliberately independent from regular-file Artifact disposition.

    ARTIFACT_BACKED
        The canonical entry is a regular file represented by exactly one
        AndroidUniverseArtifactRequirement.

    STRUCTURAL
        The entry establishes filesystem structure, currently a directory.

    ALIAS_SEMANTIC_SOURCE
        The entry is a canonical filesystem symlink. Specialized Universe
        families may derive alias relationships from this exact witness.

    RUNTIME_SPECIAL_NODE
        The entry is a character device, block device, FIFO, or socket whose
        intrinsic filesystem identity must remain available even when it does
        not independently create a regular-file artifact obligation.

    UNRESOLVED
        Filesystem Metadata exposed an entry type whose device-level meaning
        is not yet established.
    """

    ARTIFACT_BACKED = "artifact_backed"
    STRUCTURAL = "structural"
    ALIAS_SEMANTIC_SOURCE = "alias_semantic_source"
    RUNTIME_SPECIAL_NODE = "runtime_special_node"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFilesystemEntryRequirement:
    """
    Canonical Universe identity for one exact Filesystem Metadata entry.

    Literal filesystem facts remain owned by the exact upstream
    FilesystemMetadataEntry. Universe adds only device-level placement and
    disposition semantics.

    No metadata field is copied or normalized here.
    """

    inventory_entry: FilesystemMetadataInventoryEntry
    metadata_entry: FilesystemMetadataEntry
    deployment_role: AndroidUniverseArtifactDeploymentRole
    disposition: AndroidUniverseFilesystemEntryDisposition

    artifact_requirement: (
        AndroidUniverseArtifactRequirement
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.inventory_entry,
            FilesystemMetadataInventoryEntry,
        ):
            raise TypeError(
                "inventory_entry must be a "
                "FilesystemMetadataInventoryEntry"
            )

        if not isinstance(
            self.metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "metadata_entry must be a FilesystemMetadataEntry"
            )

        if not isinstance(
            self.deployment_role,
            AndroidUniverseArtifactDeploymentRole,
        ):
            raise TypeError(
                "deployment_role must be an "
                "AndroidUniverseArtifactDeploymentRole"
            )

        if not isinstance(
            self.disposition,
            AndroidUniverseFilesystemEntryDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidUniverseFilesystemEntryDisposition"
            )

        canonical_entry = (
            self.inventory_entry
            .result
            .metadata
            .entries
            .get(
                self.metadata_entry.path
            )
        )

        if canonical_entry is not self.metadata_entry:
            raise ValueError(
                "metadata_entry must preserve exact canonical "
                "Filesystem Metadata identity"
            )

        if (
            self.metadata_entry.entry_type
            is FilesystemEntryType.FILE
        ):
            if (
                self.disposition
                is not AndroidUniverseFilesystemEntryDisposition
                .ARTIFACT_BACKED
            ):
                raise ValueError(
                    "regular filesystem files must be "
                    "ARTIFACT_BACKED"
                )

            if self.artifact_requirement is None:
                raise ValueError(
                    "regular filesystem files must retain their "
                    "exact Artifact requirement"
                )

            if (
                self.artifact_requirement.inventory_entry
                is not self.inventory_entry
                or self.artifact_requirement.metadata_entry
                is not self.metadata_entry
            ):
                raise ValueError(
                    "artifact_requirement must preserve the exact "
                    "filesystem inventory and metadata-entry identities"
                )

        elif self.artifact_requirement is not None:
            raise ValueError(
                "non-regular filesystem entries must not gain "
                "regular-file Artifact requirements"
            )

        expected_disposition = (
            self._disposition_for_entry_type(
                self.metadata_entry.entry_type
            )
        )

        if self.disposition is not expected_disposition:
            raise ValueError(
                "filesystem-entry disposition does not match canonical "
                "entry type: "
                f"{self.metadata_entry.entry_type.value}"
            )

    @staticmethod
    def _disposition_for_entry_type(
        entry_type: FilesystemEntryType,
    ) -> AndroidUniverseFilesystemEntryDisposition:
        if entry_type is FilesystemEntryType.FILE:
            return (
                AndroidUniverseFilesystemEntryDisposition
                .ARTIFACT_BACKED
            )

        if entry_type is FilesystemEntryType.DIRECTORY:
            return (
                AndroidUniverseFilesystemEntryDisposition
                .STRUCTURAL
            )

        if entry_type is FilesystemEntryType.SYMLINK:
            return (
                AndroidUniverseFilesystemEntryDisposition
                .ALIAS_SEMANTIC_SOURCE
            )

        if entry_type in {
            FilesystemEntryType.CHARACTER_DEVICE,
            FilesystemEntryType.BLOCK_DEVICE,
            FilesystemEntryType.FIFO,
            FilesystemEntryType.SOCKET,
        }:
            return (
                AndroidUniverseFilesystemEntryDisposition
                .RUNTIME_SPECIAL_NODE
            )

        return (
            AndroidUniverseFilesystemEntryDisposition
            .UNRESOLVED
        )

    @property
    def identity_key(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        return (
            id(
                self.inventory_entry.artifact
            ),
            id(
                self.metadata_entry
            ),
        )

    @property
    def key(
        self,
    ) -> tuple[
        str,
        str,
    ]:
        return (
            self.inventory_entry
            .artifact
            .path
            .as_posix(),
            self.metadata_entry.path,
        )

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "filesystem-entry:"
            f"{self.inventory_entry.artifact.path.as_posix()}:"
            f"{self.metadata_entry.path}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFilesystemEntryRequirementInventory:
    """
    Complete Universe ledger for canonical Filesystem Metadata.

    Every FilesystemMetadataEntry from every exact filesystem inventory root
    must appear exactly once, regardless of entry type.

    Regular files additionally point to their exact canonical Artifact
    requirement. Non-regular entries remain first-class canonical Universe
    evidence instead of disappearing outside family-specific consumers.
    """

    source_inventory: FilesystemMetadataInventory

    requirements: tuple[
        AndroidUniverseFilesystemEntryRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "source_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if not isinstance(
            self.requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseFilesystemEntryRequirement,
            )
            for requirement in self.requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseFilesystemEntryRequirement objects"
            )

        source_entries = {
            id(entry): entry
            for entry
            in self.source_inventory.entries
        }

        seen = set()
        previous_key = None

        for requirement in self.requirements:
            if (
                id(
                    requirement.inventory_entry
                )
                not in source_entries
            ):
                raise ValueError(
                    "filesystem-entry requirement must preserve an "
                    "exact source inventory entry"
                )

            identity = (
                requirement.identity_key
            )

            if identity in seen:
                raise ValueError(
                    "duplicate filesystem-entry requirement: "
                    f"{requirement.key}"
                )

            if (
                previous_key is not None
                and requirement.key < previous_key
            ):
                raise ValueError(
                    "filesystem-entry requirements must use "
                    "deterministic ordering"
                )

            seen.add(
                identity
            )

            previous_key = (
                requirement.key
            )

        expected = {
            (
                id(
                    inventory_entry.artifact
                ),
                id(
                    metadata_entry
                ),
            )
            for inventory_entry
            in self.source_inventory.entries
            for metadata_entry
            in (
                inventory_entry
                .result
                .metadata
                .entries
                .values()
            )
        }

        if seen != expected:
            missing = expected - seen
            extra = seen - expected

            raise ValueError(
                "filesystem-entry requirement inventory must cover "
                "every canonical metadata entry exactly once; "
                f"missing={len(missing)}, extra={len(extra)}"
            )

    def __len__(
        self,
    ) -> int:
        return len(
            self.requirements
        )

    @property
    def unresolved(
        self,
    ) -> tuple[
        AndroidUniverseFilesystemEntryRequirement,
        ...,
    ]:
        return tuple(
            requirement
            for requirement
            in self.requirements
            if (
                requirement.disposition
                is AndroidUniverseFilesystemEntryDisposition
                .UNRESOLVED
            )
        )


class AndroidUniverseFilesystemEntryRequirementBuilder:
    """
    Promote the complete canonical Filesystem Metadata population into
    Universe ownership.

    The existing Artifact deployment-role classifier remains the sole source
    of direct/alternative/nested/boot filesystem placement semantics.

    Regular-file Artifact requirements are joined strictly by exact upstream
    object identity.
    """

    def build(
        self,
        source_inventory: FilesystemMetadataInventory,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseFilesystemEntryRequirementInventory:
        if not isinstance(
            source_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "source_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        if (
            artifact_requirements.source_inventory
            is not source_inventory
        ):
            raise ValueError(
                "Artifact and filesystem-entry builders must share "
                "the exact canonical Filesystem Metadata inventory"
            )

        #
        # Intentionally reuse the exact existing canonical decision.
        # Do not independently infer deployment placement here.
        #
        deployment_roles = (
            AndroidUniverseArtifactRequirementBuilder
            ._build_deployment_roles(
                source_inventory
            )
        )

        artifacts_by_identity = {
            requirement.identity_key: requirement
            for requirement
            in artifact_requirements.requirements
        }

        requirements = []

        for inventory_entry in source_inventory.entries:
            deployment_role = (
                deployment_roles[
                    id(
                        inventory_entry
                    )
                ]
            )

            for metadata_entry in (
                inventory_entry
                .result
                .metadata
                .entries
                .values()
            ):
                artifact_requirement = None

                if (
                    metadata_entry.entry_type
                    is FilesystemEntryType.FILE
                ):
                    artifact_requirement = (
                        artifacts_by_identity.get(
                            (
                                id(
                                    inventory_entry.artifact
                                ),
                                id(
                                    metadata_entry
                                ),
                            )
                        )
                    )

                    if artifact_requirement is None:
                        raise ValueError(
                            "canonical regular filesystem entry has no "
                            "exact Artifact requirement: "
                            f"{inventory_entry.artifact.path}:"
                            f"{metadata_entry.path}"
                        )

                requirements.append(
                    AndroidUniverseFilesystemEntryRequirement(
                        inventory_entry=inventory_entry,
                        metadata_entry=metadata_entry,
                        deployment_role=deployment_role,
                        disposition=(
                            AndroidUniverseFilesystemEntryRequirement
                            ._disposition_for_entry_type(
                                metadata_entry.entry_type
                            )
                        ),
                        artifact_requirement=(
                            artifact_requirement
                        ),
                    )
                )

        requirements.sort(
            key=lambda requirement: (
                requirement.key
            )
        )

        return (
            AndroidUniverseFilesystemEntryRequirementInventory(
                source_inventory=source_inventory,
                requirements=tuple(
                    requirements
                ),
            )
        )
