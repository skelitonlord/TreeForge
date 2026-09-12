from __future__ import annotations

from treeforge.android.universe.fstab.source_context import (
    AndroidUniverseFstabSourceContext,
)

from dataclasses import dataclass

from treeforge.android.reconstruction.fstab.model import (
    AndroidReconstructionFstabSourceRepresentation,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.fstab.model import (
    AndroidUniverseFstabRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionFstabReconstructor:
    """
    Reconstruct canonical fstab source representations.

    Universe owns interpretation and applicability. Planning admits only
    ACTIVE fstab requirements. Reconstruction groups those exact admitted
    requirements by their already-preserved canonical fstab source.

    No applicability, device-expression, flag, mount-option, or destination
    decision is repeated here.
    """

    @staticmethod
    def reconstruct(
        reconstruction_input: AndroidReconstructionInput,
    ) -> tuple[
        AndroidReconstructionFstabSourceRepresentation,
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

        source_contexts = (
            reconstruction_input
            .plan
            .fstab_source_contexts
        )

        if not isinstance(
            source_contexts,
            tuple,
        ):
            raise TypeError(
                "plan.fstab_source_contexts must be a tuple"
            )

        if not all(
            isinstance(
                source_context,
                AndroidUniverseFstabSourceContext,
            )
            for source_context in source_contexts
        ):
            raise TypeError(
                "plan.fstab_source_contexts contains an invalid model"
            )

        source_context_by_identity = {
            source_context.source_identity: source_context
            for source_context in source_contexts
        }

        if len(
            source_context_by_identity
        ) != len(
            source_contexts
        ):
            raise ValueError(
                "plan.fstab_source_contexts contains duplicate "
                "canonical source identities"
            )

        grouped: dict[
            tuple[
                str,
                str,
            ],
            list[
                AndroidReconstructionWorkItem
            ],
        ] = {}

        source_metadata: dict[
            tuple[
                str,
                str,
            ],
            tuple[
                object,
                object,
            ],
        ] = {}

        expected_obligation_ids = set()

        for item in (
            reconstruction_input.work_items
        ):
            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.RECONSTRUCT
            ):
                continue

            if (
                item.requirement_kind
                != "fstab"
            ):
                continue

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseFstabRequirement,
            ):
                raise TypeError(
                    "fstab Reconstruction work must preserve an "
                    "AndroidUniverseFstabRequirement"
                )

            path_identity = (
                requirement.android_path.as_posix()
                if requirement.android_path is not None
                else requirement.source_path.as_posix()
            )

            source_identity = (
                requirement.source_name,
                path_identity,
            )

            metadata = (
                requirement.source_path,
                requirement.android_path,
            )

            existing_metadata = (
                source_metadata.get(
                    source_identity
                )
            )

            if (
                existing_metadata is not None
                and existing_metadata != metadata
            ):
                raise ValueError(
                    "canonical fstab source identity maps to "
                    "inconsistent source metadata: "
                    f"{source_identity}"
                )

            source_metadata[
                source_identity
            ] = metadata

            grouped.setdefault(
                source_identity,
                [],
            ).append(
                item
            )

            expected_obligation_ids.add(
                item.obligation_id
            )

        representations = []

        represented_obligation_ids = set()

        for (
            source_identity,
            work_items,
        ) in sorted(
            grouped.items(),
            key=lambda item: item[0],
        ):
            (
                source_path,
                android_path,
            ) = source_metadata[
                source_identity
            ]

            if (
                source_identity
                not in source_context_by_identity
            ):
                raise ValueError(
                    "canonical Universe fstab source context is "
                    "missing for admitted Reconstruction source: "
                    f"{source_identity}"
                )

            canonical_work_items = tuple(
                sorted(
                    work_items,
                    key=lambda item: (
                        item.obligation.requirement
                        .declaration.line_number,
                        item.obligation_id,
                    ),
                )
            )

            representation = (
                AndroidReconstructionFstabSourceRepresentation(
                    source_identity=source_identity,
                    source_path=source_path,
                    android_path=android_path,
                    source_context=(
                        source_context_by_identity[
                            source_identity
                        ]
                    ),
                    entry_work_items=(
                        canonical_work_items
                    ),
                )
            )

            duplicate_ids = (
                represented_obligation_ids.intersection(
                    representation
                    .contributing_obligation_ids
                )
            )

            if duplicate_ids:
                raise ValueError(
                    "fstab Reconstruction work appears in "
                    "multiple source representations: "
                    f"{sorted(duplicate_ids)!r}"
                )

            represented_obligation_ids.update(
                representation
                .contributing_obligation_ids
            )

            representations.append(
                representation
            )

        if (
            represented_obligation_ids
            != expected_obligation_ids
        ):
            missing = sorted(
                expected_obligation_ids
                - represented_obligation_ids
            )

            unexpected = sorted(
                represented_obligation_ids
                - expected_obligation_ids
            )

            raise ValueError(
                "fstab Reconstruction must account for every "
                "admitted fstab work item exactly once: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        result = tuple(
            representations
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
                "fstab source representation identities "
                "must be unique"
            )

        return result
