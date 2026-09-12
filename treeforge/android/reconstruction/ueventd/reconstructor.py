from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction.ueventd.model import (
    AndroidReconstructionUeventdSourceRepresentation,
)
from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdRequirement,
)
from treeforge.android.universe.ueventd.source_context import (
    AndroidUniverseUeventdSourceContext,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionUeventdReconstructor:
    """
    Reconstruct canonical UEVENTD source representations.

    Universe already owns import resolution, source reachability,
    semantic-subject reconciliation, and effective requirement status.
    Planning therefore admits only canonical ACTIVE UEVENTD requirements.

    Reconstruction groups those exact requirements by their preserved
    canonical UEVENTD source and keeps cross-type source-line ordering.

    No reconciliation, precedence, reachability, import, semantic,
    destination, or rendering decision is repeated here.
    """

    @staticmethod
    def reconstruct(
        reconstruction_input: AndroidReconstructionInput,
    ) -> tuple[
        AndroidReconstructionUeventdSourceRepresentation,
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
            .ueventd_source_contexts
        )

        source_context_by_identity: dict[
            tuple[
                str,
                str,
            ],
            AndroidUniverseUeventdSourceContext,
        ] = {}

        for source_context in source_contexts:
            if (
                source_context.source_identity
                in source_context_by_identity
            ):
                raise ValueError(
                    "duplicate canonical UEVENTD source context: "
                    f"{source_context.source_identity}"
                )

            source_context_by_identity[
                source_context.source_identity
            ] = source_context

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
                != "ueventd"
            ):
                continue

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseUeventdRequirement,
            ):
                raise TypeError(
                    "UEVENTD Reconstruction work must preserve "
                    "an AndroidUniverseUeventdRequirement"
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
                    "canonical UEVENTD source identity maps to "
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

            canonical_work_items = tuple(
                sorted(
                    work_items,
                    key=lambda item: (
                        item.obligation.requirement
                        .declaration.source_line,
                        item.obligation_id,
                    ),
                )
            )

            source_context = (
                source_context_by_identity.get(
                    source_identity
                )
            )

            if source_context is None:
                raise ValueError(
                    "UEVENTD Reconstruction source does not have "
                    "canonical source context: "
                    f"{source_identity}"
                )

            representation = (
                AndroidReconstructionUeventdSourceRepresentation(
                    source_identity=source_identity,
                    source_path=source_path,
                    android_path=android_path,
                    source_context=source_context,
                    requirement_work_items=(
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
                    "UEVENTD Reconstruction work appears in "
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
                "UEVENTD Reconstruction must account for every "
                "admitted ueventd work item exactly once: "
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
                "UEVENTD source representation identities "
                "must be unique"
            )

        return result
