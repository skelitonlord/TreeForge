from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.dtbo.requirement import (
    AndroidUniverseDtboRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidReconstructionDtboContainer:
    """
    Exact owning DTBO container preserved across Reconstruction.

    Extraction remains authoritative for the physical Android DT table and
    exact container bytes. Parsing and Universe preserve entry identity and
    semantics.

    Reconstruction records only the syntax-neutral relationship proving that
    the canonical DTBO entry population belongs to one exact Extraction
    container. It does not choose source-tree placement, build syntax, DTS
    ownership, board-selection policy, or materialization behavior.
    """

    artifact: object

    requirement_ids: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement_ids,
            tuple,
        ):
            raise TypeError(
                "requirement_ids must be a tuple"
            )

        if not self.requirement_ids:
            raise ValueError(
                "requirement_ids must not be empty"
            )

        if not all(
            isinstance(value, str) and value
            for value in self.requirement_ids
        ):
            raise ValueError(
                "requirement_ids must contain only "
                "non-empty strings"
            )

        if len(
            self.requirement_ids
        ) != len(
            set(self.requirement_ids)
        ):
            raise ValueError(
                "requirement_ids must be unique"
            )

        if self.requirement_ids != tuple(
            sorted(
                self.requirement_ids
            )
        ):
            raise ValueError(
                "requirement_ids must use canonical ordering"
            )


class AndroidReconstructionDtboBuildProjector:
    """
    Project canonical DTBO-entry build participation.

    Each Universe DTBO requirement represents one exact parsed DTBO entry.
    Reconstruction records that entry as a required syntax-neutral DTBO build
    artifact without inventing DTS source ownership, board-selection policy,
    logical source-tree placement, or Android build syntax.

    Population signatures, variants, family groups, deltas, and FDT
    references remain canonical Universe semantics rather than ordinary build
    dependency edges.
    """

    @staticmethod
    def project_container(
        dtbo_requirements: tuple[
            AndroidUniverseDtboRequirement,
            ...,
        ],
    ) -> AndroidReconstructionDtboContainer | None:
        """
        Preserve the exact common Extraction DTBO container identity.

        Every canonical DTBO requirement originates from one parsed entry.
        Each parsed entry must preserve its immediate Extraction parent. A
        complete DTBO population must resolve to exactly one shared parent
        object; Reconstruction does not infer or match parents by filename,
        digest, semantic name, or path.
        """

        if not isinstance(
            dtbo_requirements,
            tuple,
        ):
            raise TypeError(
                "dtbo_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseDtboRequirement,
            )
            for requirement
            in dtbo_requirements
        ):
            raise TypeError(
                "dtbo_requirements must contain only "
                "AndroidUniverseDtboRequirement values"
            )

        if not dtbo_requirements:
            return None

        parents = tuple(
            requirement.source.artifact.parent
            for requirement
            in dtbo_requirements
        )

        if any(
            parent is None
            for parent in parents
        ):
            raise ValueError(
                "canonical DTBO entry is missing its "
                "Extraction container parent"
            )

        parent = parents[0]

        if not all(
            candidate is parent
            for candidate in parents
        ):
            raise ValueError(
                "canonical DTBO population does not preserve "
                "one exact shared Extraction container identity"
            )

        requirement_ids = tuple(
            sorted(
                requirement.requirement_id
                for requirement
                in dtbo_requirements
            )
        )

        if len(
            requirement_ids
        ) != len(
            set(requirement_ids)
        ):
            raise ValueError(
                "canonical DTBO requirement IDs must be unique"
            )

        return AndroidReconstructionDtboContainer(
            artifact=parent,
            requirement_ids=requirement_ids,
        )

    @staticmethod
    def project(
        dtbo_requirements: tuple[
            AndroidUniverseDtboRequirement,
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
            dtbo_requirements,
            tuple,
        ):
            raise TypeError(
                "dtbo_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseDtboRequirement,
            )
            for requirement
            in dtbo_requirements
        ):
            raise TypeError(
                "dtbo_requirements must contain only "
                "AndroidUniverseDtboRequirement values"
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

        for requirement in dtbo_requirements:
            requirement_id = requirement.requirement_id

            if requirement_id in existing_requirement_ids:
                continue

            if requirement_id in projected_requirement_ids:
                raise ValueError(
                    "canonical DTBO requirement appears more than once "
                    "during build participation projection: "
                    f"{requirement_id}"
                )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:dtbo:"
                        f"{requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .DTBO_ARTIFACT
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=requirement_id,
                    canonical_requirement_id=requirement_id,
                    installed_partition=None,
                    installed_android_path=None,
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Universe DTBO evidence proves that this "
                        "exact DTBO entry participates in the device's DTBO "
                        "population. Reconstruction separately preserves the "
                        "population's exact shared Extraction container "
                        "identity, but does not invent DTS source ownership, "
                        "board-selection policy, source-tree placement, or "
                        "Make/Soong/BoardConfig representation."
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
