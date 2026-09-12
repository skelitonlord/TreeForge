from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.init.model import (
    AndroidReconstructionInitSourceRepresentation,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction_planning.init.source_grouping import (
    AndroidReconstructionInitSourceDisposition,
    AndroidReconstructionInitSourceGroup,
)


_INIT_REQUIREMENT_KINDS = frozenset(
    {
        "init_import",
        "init_service",
        "init_action",
    }
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionInitReconstructor:
    """
    Build canonical semantic INIT source representations.

    Reconstruction consumes the exact source grouping already established by
    Planning. It does not regroup INIT requirements, recalculate source
    applicability, or reach backward into Parsing/filesystem materialization.

    Only admitted RECONSTRUCT work contributes source semantics here.
    Required and runtime-selectable sources may contribute admitted work.
    Alternative and wholly unresolved sources produce no source
    representation until Planning admits actual Reconstruction work for them.
    """

    @staticmethod
    def reconstruct(
        reconstruction_input: AndroidReconstructionInput,
    ) -> tuple[
        AndroidReconstructionInitSourceRepresentation,
        ...,
    ]:
        if not isinstance(
            reconstruction_input,
            AndroidReconstructionInput,
        ):
            raise TypeError(
                "reconstruction_input must be an "
                "AndroidReconstructionInput"
            )

        plan = reconstruction_input.plan

        if not isinstance(
            plan.init_source_groups,
            tuple,
        ):
            raise TypeError(
                "plan.init_source_groups must be a tuple"
            )

        if not all(
            isinstance(
                group,
                AndroidReconstructionInitSourceGroup,
            )
            for group in plan.init_source_groups
        ):
            raise TypeError(
                "plan.init_source_groups contains an invalid model"
            )

        reconstruct_work_by_id: dict[
            str,
            AndroidReconstructionWorkItem,
        ] = {
            item.obligation_id: item
            for item in reconstruction_input.work_items
            if (
                item.work_kind
                is AndroidReconstructionWorkKind.RECONSTRUCT
                and item.requirement_kind
                in _INIT_REQUIREMENT_KINDS
            )
        }

        known_unresolved_by_id = {
            outcome.obligation_id: outcome
            for outcome
            in reconstruction_input.known_unresolved_outcomes
            if (
                outcome.obligation is not None
                and outcome.obligation.requirement_kind
                in _INIT_REQUIREMENT_KINDS
            )
        }

        representations = []

        represented_work_ids: set[str] = set()

        for group in plan.init_source_groups:
            group_obligation_ids = {
                obligation.obligation_id
                for obligation in group.obligations
            }

            group_work_items = tuple(
                sorted(
                    (
                        reconstruct_work_by_id[
                            obligation_id
                        ]
                        for obligation_id
                        in group_obligation_ids
                        if obligation_id
                        in reconstruct_work_by_id
                    ),
                    key=lambda item: (
                        item.requirement_kind,
                        item.obligation_id,
                    ),
                )
            )

            group_known_unresolved = tuple(
                sorted(
                    (
                        known_unresolved_by_id[
                            obligation_id
                        ]
                        for obligation_id
                        in group_obligation_ids
                        if obligation_id
                        in known_unresolved_by_id
                    ),
                    key=lambda outcome: (
                        outcome.obligation_id
                    ),
                )
            )

            if not group_work_items:
                continue

            if group.disposition not in (
                AndroidReconstructionInitSourceDisposition.REQUIRED,
                AndroidReconstructionInitSourceDisposition.RUNTIME_SELECTABLE,
            ):
                raise ValueError(
                    "INIT source with admitted Reconstruction work "
                    "must be REQUIRED or RUNTIME_SELECTABLE by "
                    "canonical Planning: "
                    f"{group.source_identity}: "
                    f"{group.disposition.value}"
                )

            import_work_items = tuple(
                item
                for item in group_work_items
                if item.requirement_kind
                == "init_import"
            )

            service_work_items = tuple(
                item
                for item in group_work_items
                if item.requirement_kind
                == "init_service"
            )

            action_work_items = tuple(
                item
                for item in group_work_items
                if item.requirement_kind
                == "init_action"
            )

            representation = (
                AndroidReconstructionInitSourceRepresentation(
                    source_identity=(
                        group.source_identity
                    ),
                    source_disposition=(
                        group.disposition
                    ),
                    source_group=group,
                    import_work_items=(
                        import_work_items
                    ),
                    service_work_items=(
                        service_work_items
                    ),
                    action_work_items=(
                        action_work_items
                    ),
                    known_unresolved_outcomes=(
                        group_known_unresolved
                    ),
                )
            )

            duplicate_work_ids = (
                represented_work_ids.intersection(
                    representation.contributing_obligation_ids
                )
            )

            if duplicate_work_ids:
                raise ValueError(
                    "INIT Reconstruction work appears in "
                    "multiple source representations: "
                    f"{sorted(duplicate_work_ids)!r}"
                )

            represented_work_ids.update(
                representation.contributing_obligation_ids
            )

            representations.append(
                representation
            )

        expected_work_ids = set(
            reconstruct_work_by_id
        )

        if represented_work_ids != expected_work_ids:
            missing = sorted(
                expected_work_ids
                - represented_work_ids
            )
            unexpected = sorted(
                represented_work_ids
                - expected_work_ids
            )

            raise ValueError(
                "INIT source reconstruction must account for "
                "every admitted INIT RECONSTRUCT work item "
                "exactly once: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        result = tuple(
            sorted(
                representations,
                key=lambda representation: (
                    representation.source_identity,
                    representation.representation_id,
                ),
            )
        )

        representation_ids = tuple(
            representation.representation_id
            for representation in result
        )

        if len(
            representation_ids
        ) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "INIT source representation identities "
                "must be unique"
            )

        return result
