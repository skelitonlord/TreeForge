from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction.selinux.model import (
    AndroidReconstructionSelinuxSourceRepresentation,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionSelinuxReconstructor:
    """
    Reconstruct canonical SELinux source representations.

    Each admitted SELinux Planning obligation already represents one exact
    canonical Universe source requirement. Reconstruction therefore preserves
    that source boundary directly.

    Universe remains the owner of source interpretation, CIL semantic-family
    classification, policy-graph reconciliation, policy conclusions, and
    applicability.

    No policy reconciliation, graph derivation, rule decomposition,
    destination choice, rendering, or materialization occurs here.
    """

    @staticmethod
    def reconstruct(
        reconstruction_input: AndroidReconstructionInput,
    ) -> tuple[
        AndroidReconstructionSelinuxSourceRepresentation,
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

        representations = []

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
                != "selinux"
            ):
                continue

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseSelinuxSourceRequirement,
            ):
                raise TypeError(
                    "SELinux Reconstruction work must preserve an "
                    "AndroidUniverseSelinuxSourceRequirement"
                )

            representations.append(
                AndroidReconstructionSelinuxSourceRepresentation(
                    source_identity=(
                        requirement.requirement_id
                    ),
                    source_path=(
                        requirement.source_path
                    ),
                    android_path=(
                        requirement.android_path
                    ),
                    work_item=item,
                    requirement=requirement,
                )
            )

            expected_obligation_ids.add(
                item.obligation_id
            )

        result = tuple(
            sorted(
                representations,
                key=lambda representation: (
                    representation
                    .requirement
                    .requirement_id,
                    representation.obligation_id,
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
                "SELinux source representation identities "
                "must be unique"
            )

        represented_obligation_ids = {
            representation.obligation_id
            for representation in result
        }

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
                "SELinux Reconstruction must account for every "
                "admitted SELinux work item exactly once: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        return result
