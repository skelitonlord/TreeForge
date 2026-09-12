from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlan,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
)
from treeforge.android.runtime_linking.model import (
    AndroidRuntimeLinking,
)
from treeforge.android.partition.layout import (
    PartitionLayout,
)

if TYPE_CHECKING:
    from treeforge.android.reconstruction.init.model import (
        AndroidReconstructionInitSourceRepresentation,
    )
    from treeforge.android.reconstruction.runtime_property.model import (
        AndroidReconstructionRuntimePropertyRepresentation,
    )
    from treeforge.android.reconstruction.fstab.model import (
        AndroidReconstructionFstabSourceRepresentation,
    )
    from treeforge.android.reconstruction.ueventd.model import (
        AndroidReconstructionUeventdSourceRepresentation,
    )
    from treeforge.android.reconstruction.vintf.model import (
        AndroidReconstructionVintfDocumentRepresentation,
    )
    from treeforge.android.reconstruction.selinux.model import (
        AndroidReconstructionSelinuxSourceRepresentation,
    )


class AndroidReconstructionWorkKind(StrEnum):
    """
    Kind of downstream Reconstruction work admitted from Planning.

    RECONSTRUCT means Planning established that a semantic/source
    representation must be reconstructed.

    PRESERVE means Planning established that one exact canonical artifact
    identity must survive into Reconstruction.

    This enum deliberately says nothing about source-tree ownership,
    destinations, filenames, build-system placement, or materialization.
    """

    RECONSTRUCT = "reconstruct"
    PRESERVE = "preserve"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionWorkItem:
    """
    One exact Planning obligation admitted for Reconstruction work.

    The work item preserves the canonical Planning obligation and outcome
    verbatim. Reconstruction may later derive source representations from
    this work, but this intake model does not choose any representation,
    destination, ownership domain, or physical output.
    """

    obligation_id: str
    requirement_kind: str
    source_identity: str
    work_kind: AndroidReconstructionWorkKind

    obligation: AndroidReconstructionPlanningObligation
    planning_outcome: AndroidReconstructionPlanningOutcome

    preserved_artifact_id: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("obligation_id", self.obligation_id),
            ("requirement_kind", self.requirement_kind),
            ("source_identity", self.source_identity),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.work_kind,
            AndroidReconstructionWorkKind,
        ):
            raise TypeError(
                "work_kind must be an AndroidReconstructionWorkKind"
            )

        if not isinstance(
            self.obligation,
            AndroidReconstructionPlanningObligation,
        ):
            raise TypeError(
                "obligation must be an "
                "AndroidReconstructionPlanningObligation"
            )

        if not isinstance(
            self.planning_outcome,
            AndroidReconstructionPlanningOutcome,
        ):
            raise TypeError(
                "planning_outcome must be an "
                "AndroidReconstructionPlanningOutcome"
            )

        if self.obligation.obligation_id != self.obligation_id:
            raise ValueError(
                "work item obligation_id must match obligation"
            )

        if (
            self.planning_outcome.obligation_id
            != self.obligation_id
        ):
            raise ValueError(
                "work item obligation_id must match planning outcome"
            )

        if (
            self.obligation.requirement_kind
            != self.requirement_kind
        ):
            raise ValueError(
                "work item requirement_kind must match obligation"
            )

        if (
            self.obligation.source_identity
            != self.source_identity
        ):
            raise ValueError(
                "work item source_identity must match obligation"
            )

        if self.work_kind is AndroidReconstructionWorkKind.PRESERVE:
            if (
                not isinstance(
                    self.preserved_artifact_id,
                    str,
                )
                or not self.preserved_artifact_id
            ):
                raise ValueError(
                    "PRESERVE work requires preserved_artifact_id"
                )
        elif self.preserved_artifact_id is not None:
            raise ValueError(
                "only PRESERVE work may carry preserved_artifact_id"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionCoverage:
    """
    Admission accounting at the Planning -> Reconstruction boundary.

    This is intentionally not final Reconstruction completeness. It records
    whether every Planning obligation has been deterministically accounted
    for before family reconstruction begins.
    """

    required: int
    reconstruction_work: int
    preservation_work: int
    not_applicable: int
    known_unresolved: int

    @property
    def accounted(self) -> int:
        return (
            self.reconstruction_work
            + self.preservation_work
            + self.not_applicable
            + self.known_unresolved
        )

    @property
    def ready(self) -> bool:
        return self.required == self.accounted

    def __post_init__(self) -> None:
        values = (
            self.required,
            self.reconstruction_work,
            self.preservation_work,
            self.not_applicable,
            self.known_unresolved,
        )

        if not all(
            isinstance(value, int)
            and value >= 0
            for value in values
        ):
            raise ValueError(
                "Reconstruction coverage counts must be "
                "non-negative integers"
            )

        if self.accounted > self.required:
            raise ValueError(
                "Reconstruction coverage exceeds required count"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionInput:
    """
    Canonical accepted input to semantic Reconstruction.

    ``plan`` remains the authoritative Planning result. This object adds only
    the deterministic Reconstruction admission view:

    - PLANNED obligations become RECONSTRUCT work;
    - PRESERVED obligations become PRESERVE work;
    - NOT_APPLICABLE obligations remain explicitly acknowledged;
    - known UNRESOLVED obligations remain explicit canonical unknowns.

    Conflicts and unexpected/unclassified unresolved outcomes are rejected by
    AndroidReconstructionStage before this model can be created.
    """

    plan: AndroidReconstructionPlan

    runtime_linking: AndroidRuntimeLinking

    work_items: tuple[
        AndroidReconstructionWorkItem,
        ...,
    ]

    not_applicable_outcomes: tuple[
        AndroidReconstructionPlanningOutcome,
        ...,
    ]

    known_unresolved_outcomes: tuple[
        AndroidReconstructionPlanningOutcome,
        ...,
    ]

    coverage: AndroidReconstructionCoverage

    #
    # Exact canonical upstream Partition Layout.
    #
    # Optional because snapshot-backed/application callers may not have
    # retained Layout evidence. None means downstream consumers must omit
    # Layout-dependent realization rather than guess.
    #
    partition_layout: PartitionLayout | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.plan,
            AndroidReconstructionPlan,
        ):
            raise TypeError(
                "plan must be an AndroidReconstructionPlan"
            )

        if not isinstance(
            self.runtime_linking,
            AndroidRuntimeLinking,
        ):
            raise TypeError(
                "runtime_linking must be an AndroidRuntimeLinking"
            )

        if (
            self.partition_layout is not None
            and not isinstance(
                self.partition_layout,
                PartitionLayout,
            )
        ):
            raise TypeError(
                "partition_layout must be a PartitionLayout or None"
            )

        for field_name, value, expected_type in (
            (
                "work_items",
                self.work_items,
                AndroidReconstructionWorkItem,
            ),
            (
                "not_applicable_outcomes",
                self.not_applicable_outcomes,
                AndroidReconstructionPlanningOutcome,
            ),
            (
                "known_unresolved_outcomes",
                self.known_unresolved_outcomes,
                AndroidReconstructionPlanningOutcome,
            ),
        ):
            if not isinstance(value, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(item, expected_type)
                for item in value
            ):
                raise TypeError(
                    f"{field_name} contains an invalid model"
                )

        if not isinstance(
            self.coverage,
            AndroidReconstructionCoverage,
        ):
            raise TypeError(
                "coverage must be an AndroidReconstructionCoverage"
            )

        work_ids = tuple(
            item.obligation_id
            for item in self.work_items
        )

        if len(work_ids) != len(set(work_ids)):
            raise ValueError(
                "Reconstruction work item identities must be unique"
            )

        accounted_ids = (
            work_ids
            + tuple(
                outcome.obligation_id
                for outcome in self.not_applicable_outcomes
            )
            + tuple(
                outcome.obligation_id
                for outcome in self.known_unresolved_outcomes
            )
        )

        if len(accounted_ids) != len(set(accounted_ids)):
            raise ValueError(
                "Planning obligations must be accounted for exactly once "
                "at the Reconstruction boundary"
            )

        plan_ids = {
            obligation.obligation_id
            for obligation in self.plan.obligations
        }

        if set(accounted_ids) != plan_ids:
            raise ValueError(
                "Reconstruction input must account for every Planning "
                "obligation exactly once"
            )

        if not self.coverage.ready:
            raise ValueError(
                "Reconstruction input coverage must be ready"
            )


class AndroidReconstructionOutcomeStatus(StrEnum):
    """
    Status of one eventual semantic Reconstruction outcome.

    These statuses are defined now so family reconstructors can share one
    canonical result vocabulary later. The intake stage does not fabricate
    these outcomes before reconstruction has actually occurred.
    """

    RECONSTRUCTED = "reconstructed"
    PRESERVED = "preserved"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionOutcome:
    """
    One eventual semantic Reconstruction result.

    ``representation_ids`` will identify canonical reconstructed source
    representations once family Reconstruction is implemented. Multiple
    obligations may refer to the same representation.
    """

    obligation_id: str
    status: AndroidReconstructionOutcomeStatus
    representation_ids: tuple[str, ...] = ()
    preserved_artifact_id: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.obligation_id, str):
            raise TypeError(
                "obligation_id must be a string"
            )

        if not self.obligation_id:
            raise ValueError(
                "obligation_id must not be empty"
            )

        if not isinstance(
            self.status,
            AndroidReconstructionOutcomeStatus,
        ):
            raise TypeError(
                "status must be an AndroidReconstructionOutcomeStatus"
            )

        if not isinstance(
            self.representation_ids,
            tuple,
        ):
            raise TypeError(
                "representation_ids must be a tuple"
            )

        if not all(
            isinstance(value, str) and value
            for value in self.representation_ids
        ):
            raise ValueError(
                "representation_ids must contain only "
                "non-empty strings"
            )

        if len(
            self.representation_ids
        ) != len(
            set(self.representation_ids)
        ):
            raise ValueError(
                "representation_ids must be unique"
            )

        if (
            self.status
            is AndroidReconstructionOutcomeStatus.PRESERVED
        ):
            if (
                not isinstance(
                    self.preserved_artifact_id,
                    str,
                )
                or not self.preserved_artifact_id
            ):
                raise ValueError(
                    "PRESERVED Reconstruction outcome requires "
                    "preserved_artifact_id"
                )
        elif self.preserved_artifact_id is not None:
            raise ValueError(
                "only PRESERVED Reconstruction outcomes may carry "
                "preserved_artifact_id"
            )

        if (
            self.status
            is AndroidReconstructionOutcomeStatus.UNRESOLVED
            and not self.reason
        ):
            raise ValueError(
                "UNRESOLVED Reconstruction outcome requires a reason"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionResult:
    """
    Canonical semantic Reconstruction result.

    This model is intentionally empty-capable while the family reconstructors
    are introduced incrementally. It never represents physical Device Tree
    materialization.
    """

    reconstruction_input: AndroidReconstructionInput

    init_source_representations: tuple[
        "AndroidReconstructionInitSourceRepresentation",
        ...,
    ] = ()

    init_source_contents: tuple[
        "AndroidReconstructionSourceContent",
        ...,
    ] = ()

    fstab_source_contents: tuple[
        "AndroidReconstructionSourceContent",
        ...,
    ] = ()

    runtime_property_representations: tuple[
        "AndroidReconstructionRuntimePropertyRepresentation",
        ...,
    ] = ()

    runtime_property_source_contents: tuple[
        "AndroidReconstructionSourceContent",
        ...,
    ] = ()

    fstab_source_representations: tuple[
        "AndroidReconstructionFstabSourceRepresentation",
        ...,
    ] = ()

    ueventd_source_representations: tuple[
        "AndroidReconstructionUeventdSourceRepresentation",
        ...,
    ] = ()

    ueventd_source_contents: tuple[
        "AndroidReconstructionSourceContent",
        ...,
    ] = ()

    vintf_document_representations: tuple[
        "AndroidReconstructionVintfDocumentRepresentation",
        ...,
    ] = ()

    vintf_source_contents: tuple[
        "AndroidReconstructionSourceContent",
        ...,
    ] = ()

    selinux_source_representations: tuple[
        "AndroidReconstructionSelinuxSourceRepresentation",
        ...,
    ] = ()

    selinux_source_contents: tuple[
        "AndroidReconstructionSourceContent",
        ...,
    ] = ()

    boot_image_compositions: tuple[
        "AndroidReconstructionBootImageComposition",
        ...,
    ] = ()

    dtbo_container: (
        "AndroidReconstructionDtboContainer"
        | None
    ) = None

    artifact_build_representations: tuple[
        "AndroidReconstructionBuildRepresentation",
        ...,
    ] = ()

    elf_build_semantics: tuple[
        "AndroidReconstructionElfBuildSemantics",
        ...,
    ] = ()

    composition_relationships: tuple[
        "AndroidReconstructionCompositionRelationship",
        ...,
    ] = ()

    outcomes: tuple[
        AndroidReconstructionOutcome,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        from treeforge.android.reconstruction.build_system.model import (
            AndroidReconstructionBuildRepresentation,
        )
        from treeforge.android.reconstruction.build_system.boot import (
            AndroidReconstructionBootImageComposition,
        )
        from treeforge.android.reconstruction.build_system.dtbo import (
            AndroidReconstructionDtboContainer,
        )
        from treeforge.android.reconstruction.build_system.elf import (
            AndroidReconstructionElfBuildSemantics,
        )
        from treeforge.android.reconstruction.composition.relationship import (
            AndroidReconstructionCompositionRelationship,
        )
        from treeforge.android.reconstruction.source_content.model import (
            AndroidReconstructionSourceContent,
            AndroidReconstructionSourceContentMediaKind,
            AndroidReconstructionSourceContentStatus,
        )

        if not isinstance(
            self.boot_image_compositions,
            tuple,
        ):
            raise TypeError(
                "boot_image_compositions must be a tuple"
            )

        if not all(
            isinstance(
                composition,
                AndroidReconstructionBootImageComposition,
            )
            for composition
            in self.boot_image_compositions
        ):
            raise TypeError(
                "boot_image_compositions contains an invalid model"
            )

        canonical_boot_compositions = tuple(
            sorted(
                self.boot_image_compositions,
                key=lambda composition: (
                    composition.composition_id
                ),
            )
        )

        if (
            self.boot_image_compositions
            != canonical_boot_compositions
        ):
            raise ValueError(
                "boot_image_compositions must use "
                "canonical composition ordering"
            )

        universe_boot_requirements = (
            self.reconstruction_input
            .runtime_linking
            .universe
            .boot_requirements
        )

        universe_boot_by_id = {
            requirement.requirement_id:
            requirement
            for requirement
            in universe_boot_requirements
        }

        if len(
            universe_boot_by_id
        ) != len(
            universe_boot_requirements
        ):
            raise ValueError(
                "canonical Universe boot-family requirement "
                "identities must be unique"
            )

        composition_requirement_ids = tuple(
            composition.requirement_id
            for composition
            in self.boot_image_compositions
        )

        expected_requirement_ids = tuple(
            sorted(
                universe_boot_by_id
            )
        )

        if (
            tuple(
                sorted(
                    composition_requirement_ids
                )
            )
            != expected_requirement_ids
        ):
            raise ValueError(
                "boot_image_compositions must preserve the complete "
                "canonical Universe boot-family requirement population"
            )

        if len(
            composition_requirement_ids
        ) != len(
            set(
                composition_requirement_ids
            )
        ):
            raise ValueError(
                "boot_image_compositions must not contain duplicate "
                "canonical requirement identities"
            )

        for composition in (
            self.boot_image_compositions
        ):
            expected_requirement = (
                universe_boot_by_id.get(
                    composition.requirement_id
                )
            )

            if (
                expected_requirement
                is None
                or composition.requirement
                is not expected_requirement
            ):
                raise ValueError(
                    "boot_image_compositions must preserve exact "
                    "canonical Universe requirement object identity"
                )

        if (
            self.dtbo_container is not None
            and not isinstance(
                self.dtbo_container,
                AndroidReconstructionDtboContainer,
            )
        ):
            raise TypeError(
                "dtbo_container contains an invalid model"
            )

        if self.dtbo_container is not None:
            universe_dtbo_requirements = (
                self.reconstruction_input
                .runtime_linking
                .universe
                .dtbo_requirements
            )

            expected_requirement_ids = tuple(
                sorted(
                    requirement.requirement_id
                    for requirement
                    in universe_dtbo_requirements
                )
            )

            if (
                self.dtbo_container.requirement_ids
                != expected_requirement_ids
            ):
                raise ValueError(
                    "dtbo_container must preserve the complete "
                    "canonical Universe DTBO requirement population"
                )

            if not universe_dtbo_requirements:
                raise ValueError(
                    "dtbo_container cannot exist without "
                    "canonical DTBO requirements"
                )

            if not all(
                requirement.source.artifact.parent
                is self.dtbo_container.artifact
                for requirement
                in universe_dtbo_requirements
            ):
                raise ValueError(
                    "dtbo_container must preserve the exact "
                    "Extraction parent identity shared by every "
                    "canonical DTBO requirement"
                )

        if not isinstance(
            self.artifact_build_representations,
            tuple,
        ):
            raise TypeError(
                "artifact_build_representations must be a tuple"
            )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionBuildRepresentation,
            )
            for representation
            in self.artifact_build_representations
        ):
            raise TypeError(
                "artifact_build_representations contains "
                "an invalid model"
            )

        artifact_build_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.artifact_build_representations
        )

        if len(
            artifact_build_representation_ids
        ) != len(
            set(
                artifact_build_representation_ids
            )
        ):
            raise ValueError(
                "artifact build representation identities "
                "must be unique"
            )

        canonical_artifact_build_representations = tuple(
            sorted(
                self.artifact_build_representations,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        if (
            self.artifact_build_representations
            != canonical_artifact_build_representations
        ):
            raise ValueError(
                "artifact_build_representations must use "
                "canonical representation ordering"
            )

        preserved_artifact_work_items = tuple(
            item
            for item
            in self.reconstruction_input.work_items
            if (
                item.work_kind
                is AndroidReconstructionWorkKind.PRESERVE
                and item.requirement_kind == "artifact"
            )
        )

        expected_preserved_artifact_ids = {
            item.preserved_artifact_id
            for item
            in preserved_artifact_work_items
        }

        preserved_artifact_build_representations = tuple(
            representation
            for representation
            in self.artifact_build_representations
            if representation.preserved_artifact_id is not None
        )

        actual_preserved_artifact_ids = {
            representation.preserved_artifact_id
            for representation
            in preserved_artifact_build_representations
        }

        if (
            actual_preserved_artifact_ids
            != expected_preserved_artifact_ids
        ):
            missing = sorted(
                expected_preserved_artifact_ids
                - actual_preserved_artifact_ids
            )
            unexpected = sorted(
                actual_preserved_artifact_ids
                - expected_preserved_artifact_ids
            )

            raise ValueError(
                "preserved-artifact-backed build representations "
                "must correspond exactly to preserved artifact work: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if (
            len(preserved_artifact_build_representations)
            != len(preserved_artifact_work_items)
        ):
            raise ValueError(
                "preserved-artifact-backed build representations "
                "must contain exactly one representation per "
                "preserved artifact work item"
            )

        all_source_contents = (
            *self.init_source_contents,
            *self.runtime_property_source_contents,
            *self.fstab_source_contents,
            *self.ueventd_source_contents,
            *self.vintf_source_contents,
            *self.selinux_source_contents,
        )

        source_content_by_id = {
            content.content_id: content
            for content in all_source_contents
        }

        if len(source_content_by_id) != len(all_source_contents):
            raise ValueError(
                "Reconstruction source-content identities must be "
                "globally unique before build projection"
            )

        source_backed_build_representations = tuple(
            representation
            for representation
            in self.artifact_build_representations
            if representation.source_content_id is not None
        )

        source_backed_ids = tuple(
            representation.source_content_id
            for representation
            in source_backed_build_representations
        )

        if len(source_backed_ids) != len(set(source_backed_ids)):
            raise ValueError(
                "one source-content unit may have at most one "
                "build representation"
            )

        unknown_source_content_ids = sorted(
            source_content_id
            for source_content_id in source_backed_ids
            if source_content_id not in source_content_by_id
        )

        if unknown_source_content_ids:
            raise ValueError(
                "source-backed build representations reference "
                "unknown Reconstruction source content: "
                f"{unknown_source_content_ids!r}"
            )

        non_source_declarable_ids = {
            content.content_id
            for content in all_source_contents
            if (
                content.status
                is AndroidReconstructionSourceContentStatus
                .NOT_SOURCE_DECLARABLE
            )
        }

        invalid_source_backed_ids = sorted(
            source_content_id
            for source_content_id in source_backed_ids
            if source_content_id in non_source_declarable_ids
        )

        if invalid_source_backed_ids:
            raise ValueError(
                "NOT_SOURCE_DECLARABLE Reconstruction content "
                "must not have source-backed build representations: "
                f"{invalid_source_backed_ids!r}"
            )

        if not isinstance(
            self.elf_build_semantics,
            tuple,
        ):
            raise TypeError(
                "elf_build_semantics must be a tuple"
            )

        if not all(
            isinstance(
                semantics,
                AndroidReconstructionElfBuildSemantics,
            )
            for semantics
            in self.elf_build_semantics
        ):
            raise TypeError(
                "elf_build_semantics contains an invalid model"
            )

        elf_semantics_ids = tuple(
            semantics.semantics_id
            for semantics
            in self.elf_build_semantics
        )

        if len(
            elf_semantics_ids
        ) != len(
            set(elf_semantics_ids)
        ):
            raise ValueError(
                "ELF build semantics identities must be unique"
            )

        if self.elf_build_semantics != tuple(
            sorted(
                self.elf_build_semantics,
                key=lambda semantics: (
                    semantics.semantics_id
                ),
            )
        ):
            raise ValueError(
                "elf_build_semantics must use canonical ordering"
            )

        preserved_elf_work_items = tuple(
            item
            for item
            in self.reconstruction_input.work_items
            if (
                item.work_kind
                is AndroidReconstructionWorkKind.PRESERVE
                and item.requirement_kind == "elf"
            )
        )

        expected_elf_requirement_ids = {
            item.obligation.requirement.requirement_id
            for item
            in preserved_elf_work_items
        }

        actual_elf_requirement_ids = {
            semantics.requirement.requirement_id
            for semantics
            in self.elf_build_semantics
        }

        if (
            actual_elf_requirement_ids
            != expected_elf_requirement_ids
        ):
            missing = sorted(
                expected_elf_requirement_ids
                - actual_elf_requirement_ids
            )
            unexpected = sorted(
                actual_elf_requirement_ids
                - expected_elf_requirement_ids
            )

            raise ValueError(
                "ELF build semantics must correspond exactly "
                "to preserved ELF work: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if (
            len(self.elf_build_semantics)
            != len(preserved_elf_work_items)
        ):
            raise ValueError(
                "ELF build semantics must contain exactly one "
                "projection per preserved ELF work item"
            )

        artifact_build_ids = {
            representation.representation_id
            for representation
            in self.artifact_build_representations
        }

        invalid_elf_targets = sorted(
            semantics.target_build_representation_id
            for semantics
            in self.elf_build_semantics
            if (
                semantics.target_build_representation_id
                is not None
                and semantics.target_build_representation_id
                not in artifact_build_ids
            )
        )

        if invalid_elf_targets:
            raise ValueError(
                "ELF build semantics reference unknown Artifact "
                "build representations: "
                f"{invalid_elf_targets!r}"
            )

        if not isinstance(
            self.composition_relationships,
            tuple,
        ):
            raise TypeError(
                "composition_relationships must be a tuple"
            )

        if not all(
            isinstance(
                relationship,
                AndroidReconstructionCompositionRelationship,
            )
            for relationship
            in self.composition_relationships
        ):
            raise TypeError(
                "composition_relationships contains an invalid model"
            )

        composition_relationship_ids = tuple(
            relationship.relationship_id
            for relationship
            in self.composition_relationships
        )

        if len(
            composition_relationship_ids
        ) != len(
            set(
                composition_relationship_ids
            )
        ):
            raise ValueError(
                "composition_relationships must contain unique "
                "relationship identities"
            )

        canonical_composition_relationships = tuple(
            sorted(
                self.composition_relationships,
                key=lambda relationship: (
                    relationship.relationship_id
                ),
            )
        )

        if (
            self.composition_relationships
            != canonical_composition_relationships
        ):
            raise ValueError(
                "composition_relationships must be in canonical order"
            )

        if not isinstance(
            self.reconstruction_input,
            AndroidReconstructionInput,
        ):
            raise TypeError(
                "reconstruction_input must be an AndroidReconstructionInput"
            )

        if not isinstance(
            self.init_source_representations,
            tuple,
        ):
            raise TypeError(
                "init_source_representations must be a tuple"
            )

        from treeforge.android.reconstruction.init.model import (
            AndroidReconstructionInitSourceRepresentation,
        )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionInitSourceRepresentation,
            )
            for representation
            in self.init_source_representations
        ):
            raise TypeError(
                "init_source_representations contains "
                "an invalid model"
            )

        representation_ids = tuple(
            representation.representation_id
            for representation
            in self.init_source_representations
        )

        if len(
            representation_ids
        ) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "Reconstruction representation identities "
                "must be unique"
            )

        if not isinstance(
            self.init_source_contents,
            tuple,
        ):
            raise TypeError(
                "init_source_contents must be a tuple"
            )

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content in self.init_source_contents
        ):
            raise TypeError(
                "init_source_contents contains an invalid model"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.INIT_RC
            for content in self.init_source_contents
        ):
            raise ValueError(
                "init_source_contents may contain only INIT_RC content"
            )

        content_ids = tuple(
            content.content_id
            for content in self.init_source_contents
        )

        if len(content_ids) != len(set(content_ids)):
            raise ValueError(
                "INIT source content identities must be unique"
            )

        content_representation_ids = tuple(
            content.representation_id
            for content in self.init_source_contents
        )

        if len(
            content_representation_ids
        ) != len(
            set(content_representation_ids)
        ):
            raise ValueError(
                "INIT source representations may map to only "
                "one source-content result"
            )

        if set(content_representation_ids) != set(
            representation_ids
        ):
            missing = sorted(
                set(representation_ids)
                - set(content_representation_ids)
            )
            unexpected = sorted(
                set(content_representation_ids)
                - set(representation_ids)
            )

            raise ValueError(
                "INIT source content must correspond exactly to "
                "INIT source representations: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if not isinstance(
            self.runtime_property_representations,
            tuple,
        ):
            raise TypeError(
                "runtime_property_representations must be a tuple"
            )

        from treeforge.android.reconstruction.runtime_property.model import (
            AndroidReconstructionRuntimePropertyRepresentation,
        )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionRuntimePropertyRepresentation,
            )
            for representation
            in self.runtime_property_representations
        ):
            raise TypeError(
                "runtime_property_representations contains "
                "an invalid model"
            )

        runtime_property_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.runtime_property_representations
        )

        if len(
            runtime_property_representation_ids
        ) != len(
            set(runtime_property_representation_ids)
        ):
            raise ValueError(
                "runtime-property Reconstruction representation "
                "identities must be unique"
            )

        if not isinstance(
            self.runtime_property_source_contents,
            tuple,
        ):
            raise TypeError(
                "runtime_property_source_contents must be a tuple"
            )

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content
            in self.runtime_property_source_contents
        ):
            raise TypeError(
                "runtime_property_source_contents contains "
                "an invalid model"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.PROPERTY
            for content
            in self.runtime_property_source_contents
        ):
            raise ValueError(
                "runtime_property_source_contents may contain "
                "only PROPERTY content"
            )

        if not all(
            content.status
            is (
                AndroidReconstructionSourceContentStatus
                .NOT_SOURCE_DECLARABLE
            )
            for content
            in self.runtime_property_source_contents
        ):
            raise ValueError(
                "runtime-property Source Content must be "
                "NOT_SOURCE_DECLARABLE"
            )

        if not all(
            content.text is None
            and content.raw_bytes is None
            for content
            in self.runtime_property_source_contents
        ):
            raise ValueError(
                "runtime-property NOT_SOURCE_DECLARABLE content "
                "must not contain rendered text or bytes"
            )

        runtime_property_content_ids = tuple(
            content.content_id
            for content
            in self.runtime_property_source_contents
        )

        if len(
            runtime_property_content_ids
        ) != len(
            set(runtime_property_content_ids)
        ):
            raise ValueError(
                "runtime-property Source Content identities "
                "must be unique"
            )

        runtime_property_content_representation_ids = tuple(
            content.representation_id
            for content
            in self.runtime_property_source_contents
        )

        if len(
            runtime_property_content_representation_ids
        ) != len(
            set(
                runtime_property_content_representation_ids
            )
        ):
            raise ValueError(
                "runtime-property Source Content must contain "
                "exactly one unit per representation"
            )

        runtime_property_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.runtime_property_representations
        )

        if set(
            runtime_property_content_representation_ids
        ) != set(
            runtime_property_representation_ids
        ):
            missing = sorted(
                set(runtime_property_representation_ids)
                - set(
                    runtime_property_content_representation_ids
                )
            )

            unexpected = sorted(
                set(
                    runtime_property_content_representation_ids
                )
                - set(runtime_property_representation_ids)
            )

            raise ValueError(
                "runtime-property Source Content must correspond "
                "exactly to runtime-property representations: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if not isinstance(
            self.fstab_source_representations,
            tuple,
        ):
            raise TypeError(
                "fstab_source_representations must be a tuple"
            )

        from treeforge.android.reconstruction.fstab.model import (
            AndroidReconstructionFstabSourceRepresentation,
        )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionFstabSourceRepresentation,
            )
            for representation
            in self.fstab_source_representations
        ):
            raise TypeError(
                "fstab_source_representations contains "
                "an invalid model"
            )

        fstab_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.fstab_source_representations
        )

        if len(
            fstab_representation_ids
        ) != len(
            set(fstab_representation_ids)
        ):
            raise ValueError(
                "fstab Reconstruction representation identities "
                "must be unique"
            )

        if not isinstance(
            self.fstab_source_contents,
            tuple,
        ):
            raise TypeError(
                "fstab_source_contents must be a tuple"
            )

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content in self.fstab_source_contents
        ):
            raise TypeError(
                "fstab_source_contents contains an invalid model"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.FSTAB
            for content in self.fstab_source_contents
        ):
            raise ValueError(
                "fstab_source_contents may contain only FSTAB content"
            )

        fstab_content_ids = tuple(
            content.content_id
            for content in self.fstab_source_contents
        )

        if len(
            fstab_content_ids
        ) != len(
            set(fstab_content_ids)
        ):
            raise ValueError(
                "fstab source content identities must be unique"
            )

        fstab_content_representation_ids = tuple(
            content.representation_id
            for content in self.fstab_source_contents
        )

        if len(
            fstab_content_representation_ids
        ) != len(
            set(fstab_content_representation_ids)
        ):
            raise ValueError(
                "fstab source representations may map to only "
                "one source-content result"
            )

        if set(
            fstab_content_representation_ids
        ) != set(
            fstab_representation_ids
        ):
            missing = sorted(
                set(fstab_representation_ids)
                - set(fstab_content_representation_ids)
            )
            unexpected = sorted(
                set(fstab_content_representation_ids)
                - set(fstab_representation_ids)
            )

            raise ValueError(
                "fstab source content must correspond exactly to "
                "fstab source representations: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if not isinstance(
            self.ueventd_source_representations,
            tuple,
        ):
            raise TypeError(
                "ueventd_source_representations must be a tuple"
            )

        from treeforge.android.reconstruction.ueventd.model import (
            AndroidReconstructionUeventdSourceRepresentation,
        )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionUeventdSourceRepresentation,
            )
            for representation
            in self.ueventd_source_representations
        ):
            raise TypeError(
                "ueventd_source_representations contains "
                "an invalid model"
            )

        ueventd_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.ueventd_source_representations
        )

        if len(
            ueventd_representation_ids
        ) != len(
            set(ueventd_representation_ids)
        ):
            raise ValueError(
                "UEVENTD Reconstruction representation identities "
                "must be unique"
            )

        if not isinstance(
            self.ueventd_source_contents,
            tuple,
        ):
            raise TypeError(
                "ueventd_source_contents must be a tuple"
            )

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content
            in self.ueventd_source_contents
        ):
            raise TypeError(
                "ueventd_source_contents contains an invalid model"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.UEVENTD
            for content
            in self.ueventd_source_contents
        ):
            raise ValueError(
                "ueventd_source_contents may contain only "
                "UEVENTD content"
            )

        ueventd_content_ids = tuple(
            content.content_id
            for content
            in self.ueventd_source_contents
        )

        if len(
            ueventd_content_ids
        ) != len(
            set(ueventd_content_ids)
        ):
            raise ValueError(
                "UEVENTD source content identities must be unique"
            )

        ueventd_content_representation_ids = tuple(
            content.representation_id
            for content
            in self.ueventd_source_contents
        )

        if len(
            ueventd_content_representation_ids
        ) != len(
            set(
                ueventd_content_representation_ids
            )
        ):
            raise ValueError(
                "UEVENTD source representations may map to "
                "only one source-content result"
            )

        if set(
            ueventd_content_representation_ids
        ) != set(
            ueventd_representation_ids
        ):
            missing = sorted(
                set(
                    ueventd_representation_ids
                )
                - set(
                    ueventd_content_representation_ids
                )
            )

            unexpected = sorted(
                set(
                    ueventd_content_representation_ids
                )
                - set(
                    ueventd_representation_ids
                )
            )

            raise ValueError(
                "UEVENTD source content must correspond "
                "exactly to UEVENTD source representations: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if not isinstance(
            self.vintf_document_representations,
            tuple,
        ):
            raise TypeError(
                "vintf_document_representations must be a tuple"
            )

        from treeforge.android.reconstruction.vintf.model import (
            AndroidReconstructionVintfDocumentRepresentation,
        )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionVintfDocumentRepresentation,
            )
            for representation
            in self.vintf_document_representations
        ):
            raise TypeError(
                "vintf_document_representations contains "
                "an invalid model"
            )

        vintf_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.vintf_document_representations
        )

        if len(
            vintf_representation_ids
        ) != len(
            set(vintf_representation_ids)
        ):
            raise ValueError(
                "VINTF Reconstruction representation identities "
                "must be unique"
            )

        if not isinstance(
            self.vintf_source_contents,
            tuple,
        ):
            raise TypeError(
                "vintf_source_contents must be a tuple"
            )

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content
            in self.vintf_source_contents
        ):
            raise TypeError(
                "vintf_source_contents contains an invalid model"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.VINTF_XML
            for content
            in self.vintf_source_contents
        ):
            raise ValueError(
                "vintf_source_contents may contain only "
                "VINTF XML content"
            )

        if not all(
            content.status
            is AndroidReconstructionSourceContentStatus.PRESERVED_EXACT
            for content
            in self.vintf_source_contents
        ):
            raise ValueError(
                "VINTF source content must preserve exact "
                "canonical XML"
            )

        vintf_content_ids = tuple(
            content.content_id
            for content
            in self.vintf_source_contents
        )

        if len(
            vintf_content_ids
        ) != len(
            set(vintf_content_ids)
        ):
            raise ValueError(
                "VINTF source content identities must be unique"
            )

        vintf_content_representation_ids = tuple(
            content.representation_id
            for content
            in self.vintf_source_contents
        )

        if len(
            vintf_content_representation_ids
        ) != len(
            set(
                vintf_content_representation_ids
            )
        ):
            raise ValueError(
                "VINTF document representations may map to "
                "only one source-content result"
            )

        if set(
            vintf_content_representation_ids
        ) != set(
            vintf_representation_ids
        ):
            missing = sorted(
                set(
                    vintf_representation_ids
                )
                - set(
                    vintf_content_representation_ids
                )
            )

            unexpected = sorted(
                set(
                    vintf_content_representation_ids
                )
                - set(
                    vintf_representation_ids
                )
            )

            raise ValueError(
                "VINTF source content must correspond exactly "
                "to VINTF document representations: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if not isinstance(
            self.selinux_source_representations,
            tuple,
        ):
            raise TypeError(
                "selinux_source_representations must be a tuple"
            )

        from treeforge.android.reconstruction.selinux.model import (
            AndroidReconstructionSelinuxSourceRepresentation,
        )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionSelinuxSourceRepresentation,
            )
            for representation
            in self.selinux_source_representations
        ):
            raise TypeError(
                "selinux_source_representations contains "
                "an invalid model"
            )

        selinux_representation_ids = tuple(
            representation.representation_id
            for representation
            in self.selinux_source_representations
        )

        if len(
            selinux_representation_ids
        ) != len(
            set(selinux_representation_ids)
        ):
            raise ValueError(
                "SELinux Reconstruction representation identities "
                "must be unique"
            )

        if not isinstance(
            self.selinux_source_contents,
            tuple,
        ):
            raise TypeError(
                "selinux_source_contents must be a tuple"
            )

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content
            in self.selinux_source_contents
        ):
            raise TypeError(
                "selinux_source_contents contains an invalid model"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.SELINUX
            for content
            in self.selinux_source_contents
        ):
            raise ValueError(
                "selinux_source_contents may contain only "
                "SELinux content"
            )

        allowed_selinux_statuses = {
            AndroidReconstructionSourceContentStatus.PRESERVED_EXACT,
            AndroidReconstructionSourceContentStatus.OPAQUE,
        }

        if not all(
            content.status
            in allowed_selinux_statuses
            for content
            in self.selinux_source_contents
        ):
            raise ValueError(
                "SELinux source content must be PRESERVED_EXACT "
                "or OPAQUE"
            )

        selinux_content_ids = tuple(
            content.content_id
            for content
            in self.selinux_source_contents
        )

        if len(
            selinux_content_ids
        ) != len(
            set(selinux_content_ids)
        ):
            raise ValueError(
                "SELinux source content identities must be unique"
            )

        selinux_content_representation_ids = tuple(
            content.representation_id
            for content
            in self.selinux_source_contents
        )

        if len(
            selinux_content_representation_ids
        ) != len(
            set(selinux_content_representation_ids)
        ):
            raise ValueError(
                "SELinux source representations may map to "
                "only one source-content result"
            )

        if set(
            selinux_content_representation_ids
        ) != set(
            selinux_representation_ids
        ):
            missing = sorted(
                set(selinux_representation_ids)
                - set(
                    selinux_content_representation_ids
                )
            )

            unexpected = sorted(
                set(
                    selinux_content_representation_ids
                )
                - set(selinux_representation_ids)
            )

            raise ValueError(
                "SELinux source content must correspond exactly "
                "to SELinux source representations: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if not isinstance(self.outcomes, tuple):
            raise TypeError(
                "outcomes must be a tuple"
            )

        if not all(
            isinstance(
                outcome,
                AndroidReconstructionOutcome,
            )
            for outcome in self.outcomes
        ):
            raise TypeError(
                "outcomes contains an invalid model"
            )

        outcome_ids = tuple(
            outcome.obligation_id
            for outcome in self.outcomes
        )

        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError(
                "Reconstruction outcome obligation identities "
                "must be unique"
            )
