from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)


class AndroidUniverseElfArtifactAssociationKind(
    StrEnum,
):
    FILESYSTEM_ARTIFACT = "filesystem_artifact"
    EXTRACTION_ARTIFACT = "extraction_artifact"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfArtifactAssociation:
    """
    Exact physical backing relationship for one canonical Universe ELF.

    Filesystem-backed ELFs reference their exact canonical Artifact
    requirement.

    Extraction-backed embedded ELFs remain linked directly to their exact
    EMBEDDED_ELF_EXTRACTION artifact because the generic Artifact inventory
    intentionally represents filesystem regular files only.
    """

    elf_requirement: AndroidUniverseElfRequirement
    kind: AndroidUniverseElfArtifactAssociationKind

    artifact_requirement: (
        AndroidUniverseArtifactRequirement
        | None
    ) = None

    extraction_artifact: (
        ExtractedArtifact
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.elf_requirement,
            AndroidUniverseElfRequirement,
        ):
            raise TypeError(
                "elf_requirement must be an "
                "AndroidUniverseElfRequirement"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseElfArtifactAssociationKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseElfArtifactAssociationKind"
            )

        source = (
            self.elf_requirement
            .source
            .source
        )

        if (
            self.kind
            is AndroidUniverseElfArtifactAssociationKind
            .FILESYSTEM_ARTIFACT
        ):
            if not source.is_filesystem_backed:
                raise ValueError(
                    "filesystem ELF association requires a "
                    "filesystem-backed Parsing source"
                )

            if not isinstance(
                self.artifact_requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise ValueError(
                    "filesystem ELF association requires its "
                    "canonical Artifact requirement"
                )

            if self.extraction_artifact is not None:
                raise ValueError(
                    "filesystem ELF association must not carry "
                    "an extraction_artifact"
                )

            filesystem_source = (
                source.filesystem_source
            )

            assert filesystem_source is not None

            if (
                self.artifact_requirement
                .inventory_entry
                .artifact
                is not filesystem_source.artifact
            ):
                raise ValueError(
                    "filesystem ELF association must preserve "
                    "exact filesystem Extraction identity"
                )

            if (
                source.metadata_entry is not None
                and self.artifact_requirement.metadata_entry
                is not source.metadata_entry
            ):
                raise ValueError(
                    "filesystem ELF association must preserve "
                    "exact Filesystem Metadata identity"
                )

        else:
            if not source.is_extraction_backed:
                raise ValueError(
                    "extraction ELF association requires an "
                    "extraction-backed Parsing source"
                )

            if self.artifact_requirement is not None:
                raise ValueError(
                    "extraction-backed ELF must not invent a "
                    "filesystem Artifact requirement"
                )

            if (
                self.extraction_artifact
                is not source.extraction_artifact
            ):
                raise ValueError(
                    "extraction ELF association must preserve "
                    "exact Parsing Extraction artifact identity"
                )

            assert self.extraction_artifact is not None

            if (
                self.extraction_artifact.operation
                is not ExtractionOperation
                .EMBEDDED_ELF_EXTRACTION
            ):
                raise ValueError(
                    "extraction-backed ELF association must reference "
                    "EMBEDDED_ELF_EXTRACTION"
                )


class AndroidUniverseElfArtifactAssociationBuilder:
    @staticmethod
    def build(
        *,
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> tuple[
        AndroidUniverseElfArtifactAssociation,
        ...,
    ]:
        if not isinstance(
            elf_requirements,
            tuple,
        ):
            raise TypeError(
                "elf_requirements must be a tuple"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        artifacts_by_key = {
            (
                id(
                    requirement
                    .inventory_entry
                    .artifact
                ),
                requirement.metadata_entry.path,
            ): requirement
            for requirement
            in artifact_requirements.requirements
        }

        associations = []

        for elf_requirement in elf_requirements:
            source = (
                elf_requirement
                .source
                .source
            )

            if source.is_extraction_backed:
                associations.append(
                    AndroidUniverseElfArtifactAssociation(
                        elf_requirement=elf_requirement,
                        kind=(
                            AndroidUniverseElfArtifactAssociationKind
                            .EXTRACTION_ARTIFACT
                        ),
                        extraction_artifact=(
                            source.extraction_artifact
                        ),
                    )
                )
                continue

            filesystem_source = (
                source.filesystem_source
            )

            assert filesystem_source is not None

            try:
                inventory_entry = (
                    artifact_requirements
                    .source_inventory
                    .entry_for_artifact(
                        filesystem_source.artifact
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "filesystem-backed ELF does not map to "
                    "canonical Filesystem Metadata inventory"
                ) from error

            metadata_path = (
                inventory_entry
                .filesystem_path_for_materialized_path(
                    source.host_path
                )
            )

            artifact_requirement = (
                artifacts_by_key.get(
                    (
                        id(
                            inventory_entry.artifact
                        ),
                        metadata_path,
                    )
                )
            )

            if artifact_requirement is None:
                raise ValueError(
                    "filesystem-backed ELF does not map to an exact "
                    "canonical Universe Artifact requirement: "
                    f"{source.identity_key!r}"
                )

            associations.append(
                AndroidUniverseElfArtifactAssociation(
                    elf_requirement=elf_requirement,
                    kind=(
                        AndroidUniverseElfArtifactAssociationKind
                        .FILESYSTEM_ARTIFACT
                    ),
                    artifact_requirement=(
                        artifact_requirement
                    ),
                )
            )

        return tuple(
            associations
        )
