from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction_planning.init.source_grouping import (
    AndroidReconstructionInitSourceDisposition,
    AndroidReconstructionInitSourceGroup,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningOutcome,
)


_INIT_REQUIREMENT_KINDS = frozenset(
    {
        "init_import",
        "init_service",
        "init_action",
    }
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionInitSourceRepresentation:
    """
    Canonical semantic Reconstruction representation of one INIT source.

    The source boundary and source identity come directly from the accepted
    Reconstruction Planning source group.

    Each work item still carries its exact Planning obligation, which in turn
    retains the exact canonical Universe requirement and Universe context.
    Reconstruction therefore preserves imports, services, actions, parsed
    declarations, semantic interpretations, and provenance without copying
    or reinterpreting them here.

    This representation deliberately does not choose a source-tree
    destination, ownership domain, filename, rendered text, or physical
    materialization strategy.
    """

    source_identity: str
    source_disposition: AndroidReconstructionInitSourceDisposition

    source_group: AndroidReconstructionInitSourceGroup

    import_work_items: tuple[
        AndroidReconstructionWorkItem,
        ...,
    ]

    service_work_items: tuple[
        AndroidReconstructionWorkItem,
        ...,
    ]

    action_work_items: tuple[
        AndroidReconstructionWorkItem,
        ...,
    ]

    known_unresolved_outcomes: tuple[
        AndroidReconstructionPlanningOutcome,
        ...,
    ] = ()

    @property
    def representation_id(self) -> str:
        return f"init-source:{self.source_identity}"

    @property
    def work_items(
        self,
    ) -> tuple[
        AndroidReconstructionWorkItem,
        ...,
    ]:
        return (
            self.import_work_items
            + self.service_work_items
            + self.action_work_items
        )

    @property
    def contributing_obligation_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            item.obligation_id
            for item in self.work_items
        )

    @property
    def source_group_obligation_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            obligation.obligation_id
            for obligation in self.source_group.obligations
        )

    @property
    def import_requirements(
        self,
    ) -> tuple[object, ...]:
        return tuple(
            item.obligation.requirement
            for item in self.import_work_items
        )

    @property
    def service_requirements(
        self,
    ) -> tuple[object, ...]:
        return tuple(
            item.obligation.requirement
            for item in self.service_work_items
        )

    @property
    def action_requirements(
        self,
    ) -> tuple[object, ...]:
        return tuple(
            item.obligation.requirement
            for item in self.action_work_items
        )

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_identity,
            str,
        ):
            raise TypeError(
                "source_identity must be a string"
            )

        if not self.source_identity:
            raise ValueError(
                "source_identity must not be empty"
            )

        if not isinstance(
            self.source_disposition,
            AndroidReconstructionInitSourceDisposition,
        ):
            raise TypeError(
                "source_disposition must be an "
                "AndroidReconstructionInitSourceDisposition"
            )

        if not isinstance(
            self.source_group,
            AndroidReconstructionInitSourceGroup,
        ):
            raise TypeError(
                "source_group must be an "
                "AndroidReconstructionInitSourceGroup"
            )

        if (
            self.source_group.source_identity
            != self.source_identity
        ):
            raise ValueError(
                "source_identity must match source_group"
            )

        if (
            self.source_group.disposition
            is not self.source_disposition
        ):
            raise ValueError(
                "source_disposition must match source_group"
            )

        for (
            field_name,
            values,
            expected_kind,
        ) in (
            (
                "import_work_items",
                self.import_work_items,
                "init_import",
            ),
            (
                "service_work_items",
                self.service_work_items,
                "init_service",
            ),
            (
                "action_work_items",
                self.action_work_items,
                "init_action",
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            for item in values:
                if not isinstance(
                    item,
                    AndroidReconstructionWorkItem,
                ):
                    raise TypeError(
                        f"{field_name} must contain only "
                        "AndroidReconstructionWorkItem instances"
                    )

                if (
                    item.work_kind
                    is not AndroidReconstructionWorkKind.RECONSTRUCT
                ):
                    raise ValueError(
                        f"{field_name} may contain only "
                        "RECONSTRUCT work"
                    )

                if (
                    item.requirement_kind
                    != expected_kind
                ):
                    raise ValueError(
                        f"{field_name} contains a work item "
                        "from the wrong INIT family"
                    )

        if not self.work_items:
            raise ValueError(
                "INIT source representation requires at least "
                "one Reconstruction work item"
            )

        work_ids = self.contributing_obligation_ids

        if len(
            work_ids
        ) != len(
            set(work_ids)
        ):
            raise ValueError(
                "INIT source representation contains duplicate "
                "Reconstruction work items"
            )

        source_group_ids = set(
            self.source_group_obligation_ids
        )

        if not set(work_ids).issubset(
            source_group_ids
        ):
            raise ValueError(
                "INIT source representation work must belong to "
                "its canonical Planning source group"
            )

        if not isinstance(
            self.known_unresolved_outcomes,
            tuple,
        ):
            raise TypeError(
                "known_unresolved_outcomes must be a tuple"
            )

        for outcome in self.known_unresolved_outcomes:
            if not isinstance(
                outcome,
                AndroidReconstructionPlanningOutcome,
            ):
                raise TypeError(
                    "known_unresolved_outcomes must contain only "
                    "AndroidReconstructionPlanningOutcome instances"
                )

            if not outcome.known_unresolved:
                raise ValueError(
                    "INIT source representation may carry only "
                    "known unresolved Planning outcomes"
                )

            if (
                outcome.obligation is None
                or outcome.obligation.requirement_kind
                not in _INIT_REQUIREMENT_KINDS
            ):
                raise ValueError(
                    "known unresolved outcome does not belong "
                    "to an INIT requirement"
                )

            if (
                outcome.obligation_id
                not in source_group_ids
            ):
                raise ValueError(
                    "known unresolved INIT outcome must belong "
                    "to the same canonical source group"
                )

        unresolved_ids = tuple(
            outcome.obligation_id
            for outcome in self.known_unresolved_outcomes
        )

        if len(
            unresolved_ids
        ) != len(
            set(unresolved_ids)
        ):
            raise ValueError(
                "known unresolved INIT outcome identities "
                "must be unique"
            )
